"""
GitHub Integration API
Handles GitHub repository synchronization with workspace
Thin wrapper - business logic is in shared.services.git_integration_service
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

import azure.functions as func
from azure.storage.queue import QueueClient, TextBase64EncodePolicy

from shared.services.git_integration_service import GitIntegrationService
from shared.keyvault import KeyVaultClient
from shared.models import (
    GitHubConfigEntity,
    GitHubConfigRequest,
    GitHubConfigResponse,
    GitHubReposResponse,
    GitHubBranchesResponse,
    FetchFromGitHubResponse,
    CommitAndPushRequest,
    CommitAndPushResponse,
    PushToGitHubRequest,
    PushToGitHubResponse,
    PullFromGitHubRequest,
    PullFromGitHubResponse,
    GitHubSyncRequest,
    GitHubSyncResponse,
    ResolveConflictRequest,
    ResolveConflictResponse,
    WorkspaceAnalysisResponse,
    CreateRepoRequest,
    CreateRepoResponse,
    CommitHistoryResponse,
    GitRefreshStatusResponse,
    DiscardUnpushedCommitsResponse,
)
from shared.openapi_decorators import openapi_endpoint
from shared.repositories.config import ConfigRepository
from shared.secret_naming import generate_secret_name
from shared.middleware import with_org_context
from shared.custom_types import get_org_context

logger = logging.getLogger(__name__)

# Create blueprint for GitHub integration endpoints
bp = func.Blueprint()


# Key names for Azure Key Vault (legacy - kept for reference)
GITHUB_TOKEN_KEY = "github-token"
GITHUB_REPO_URL_KEY = "github-repo-url"
GITHUB_BRANCH_KEY = "github-branch"


async def _get_github_token(req: func.HttpRequest) -> str | None:
    """
    Helper function to get GitHub token from Config table and Key Vault.

    Returns:
        Token string if found and active, None otherwise
    """
    context = get_org_context(req)
    config_repo = ConfigRepository(context)
    github_config = await config_repo.get_github_config()

    if not github_config or not github_config.secret_ref:
        return None

    if github_config.status == "disconnected":
        return None

    # Get token from Key Vault using secret reference
    async with KeyVaultClient() as kv_client:
        try:
            token = await kv_client.get_secret(github_config.secret_ref)
            return token
        except Exception:
            return None


@bp.route(route="github/configure", methods=["POST"])
@bp.function_name("github_configure")
@openapi_endpoint(
    path="/github/configure",
    method="POST",
    summary="Configure GitHub integration",
    description="Save GitHub repository configuration and initialize sync",
    tags=["GitHub"],
    request_model=GitHubConfigRequest,
    response_model=GitHubConfigResponse,
)
@with_org_context
async def github_configure(req: func.HttpRequest) -> func.HttpResponse:
    """
    Configure GitHub integration.

    Saves configuration to Config table and initializes Git repository.
    If initialization fails, configuration is rolled back.
    """
    try:
        # Parse request
        request_data = json.loads(req.get_body())
        config_request = GitHubConfigRequest(**request_data)

        logger.info(f"Configuring GitHub integration for repo: {config_request.repo_url}")

        # Get existing config to retrieve secret reference
        context = get_org_context(req)
        config_repo = ConfigRepository(context)
        existing_config = await config_repo.get_github_config()

        if not existing_config or not existing_config.secret_ref:
            return func.HttpResponse(
                body=json.dumps({
                    "error": "NotConfigured",
                    "message": "GitHub token not found. Please validate your token first."
                }),
                status_code=400,
                mimetype="application/json",
            )

        # Get token from Key Vault using secret reference
        async with KeyVaultClient() as kv_client:
            token = await kv_client.get_secret(existing_config.secret_ref)

        # First, try to initialize the Git repository
        # This validates everything works before we save configuration
        # Always uses replace_with_remote strategy - backup created if needed
        git_service = GitIntegrationService()
        backup_info = None
        try:
            backup_info = await git_service.initialize_repo(
                token=token,
                repo_url=config_request.repo_url,
                branch=config_request.branch
            )
        except Exception as git_error:
            logger.error(f"Git initialization failed: {git_error}")
            # Don't save anything if Git init fails
            raise

        # Only save configuration to Config table if Git initialization succeeded
        github_config = GitHubConfigEntity(
            status="configured",
            secret_ref=existing_config.secret_ref,
            repo_url=config_request.repo_url,
            production_branch=config_request.branch,
            updated_at=datetime.now(timezone.utc),
            updated_by=context.email or "system",
        )
        await config_repo.save_github_config(github_config, updated_by=context.email or "system")

        logger.info("GitHub integration configured successfully")

        response = GitHubConfigResponse(
            configured=True,
            backup_path=backup_info.get("backup_path") if backup_info else None,
            token_saved=True,
            repo_url=config_request.repo_url,
            branch=config_request.branch
        )

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to configure GitHub: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "ConfigurationError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/config", methods=["GET"])
@bp.function_name("github_get_config")
@openapi_endpoint(
    path="/github/config",
    method="GET",
    summary="Get GitHub configuration",
    description="Retrieve current GitHub integration configuration",
    tags=["GitHub"],
    response_model=GitHubConfigResponse,
)
@with_org_context
async def github_get_config(req: func.HttpRequest) -> func.HttpResponse:
    """Get current GitHub configuration"""
    try:
        # Retrieve configuration from Config table
        context = get_org_context(req)
        config_repo = ConfigRepository(context)
        github_config = await config_repo.get_github_config()

        if not github_config:
            # No configuration exists yet
            response = GitHubConfigResponse(
                configured=False,
                token_saved=False,
                repo_url=None,
                branch=None,
                backup_path=None
            )
        else:
            # Return configuration from Config table
            response = GitHubConfigResponse(
                configured=(github_config.status == "configured"),
                token_saved=(github_config.status != "disconnected"),
                repo_url=github_config.repo_url,
                branch=github_config.production_branch,
                backup_path=None
            )

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to get GitHub config: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "ConfigError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/validate", methods=["POST"])
@bp.function_name("github_validate_token")
@openapi_endpoint(
    path="/github/validate",
    method="POST",
    summary="Validate GitHub token",
    description="Validate GitHub token and save to Key Vault, returns accessible repositories",
    tags=["GitHub"],
    response_model=GitHubReposResponse,
)
@with_org_context
async def github_validate_token(req: func.HttpRequest) -> func.HttpResponse:
    """Validate GitHub token, save to Key Vault and Config table, and list repositories"""
    try:
        # Parse request
        request_data = json.loads(req.get_body())
        token = request_data.get("token")

        if not token:
            return func.HttpResponse(
                body=json.dumps({"error": "MissingToken", "message": "GitHub token required"}),
                status_code=400,
                mimetype="application/json",
            )

        logger.info("Validating GitHub token")

        # Test the token by listing repositories
        git_service = GitIntegrationService()
        repositories = git_service.list_repositories(token)

        # Token is valid, get or create Config entry
        context = get_org_context(req)
        config_repo = ConfigRepository(context)

        existing_config = await config_repo.get_github_config()

        if existing_config and existing_config.secret_ref:
            # Reuse existing secret reference (Azure KV will auto-version)
            secret_ref = existing_config.secret_ref
            logger.info(f"Reusing existing secret reference: {secret_ref}")
        else:
            # Generate new GUID-based secret name
            secret_ref = generate_secret_name("global", "github-token")
            logger.info(f"Generated new secret reference: {secret_ref}")

        # Save token to Key Vault (will version if exists)
        async with KeyVaultClient() as kv_client:
            await kv_client.set_secret(secret_ref, token)

        # Save or update Config table entry
        github_config = GitHubConfigEntity(
            status="token_saved",
            secret_ref=secret_ref,
            repo_url=existing_config.repo_url if existing_config else None,
            production_branch=existing_config.production_branch if existing_config else None,
            updated_at=datetime.now(timezone.utc),
            updated_by=context.email or "system",
        )
        await config_repo.save_github_config(github_config, updated_by=context.email or "system")

        logger.info("GitHub token validated and saved successfully")

        response = GitHubReposResponse(repositories=repositories)

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to validate GitHub token: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "ValidationError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/repositories", methods=["GET"])
@bp.function_name("github_list_repos")
@openapi_endpoint(
    path="/github/repositories",
    method="GET",
    summary="List GitHub repositories",
    description="List accessible repositories using the saved GitHub token",
    tags=["GitHub"],
    response_model=GitHubReposResponse,
)
@with_org_context
async def github_list_repos(req: func.HttpRequest) -> func.HttpResponse:
    """List user's GitHub repositories using token from Config table"""
    try:
        # Get token from Config table
        token = await _get_github_token(req)

        if not token:
            return func.HttpResponse(
                body=json.dumps({"error": "NotConfigured", "message": "GitHub token not found. Please validate your token first."}),
                status_code=400,
                mimetype="application/json",
            )

        git_service = GitIntegrationService()
        repositories = git_service.list_repositories(token)

        response = GitHubReposResponse(repositories=repositories)

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to list repositories: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "GitHubError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/branches", methods=["GET"])
@bp.function_name("github_list_branches")
@openapi_endpoint(
    path="/github/branches",
    method="GET",
    summary="List repository branches",
    description="List branches in a GitHub repository using saved token",
    tags=["GitHub"],
    response_model=GitHubBranchesResponse,
    query_params={
        "repo": {
            "description": "Repository full name (owner/repo)",
            "schema": {"type": "string"},
            "required": True,
        }
    },
)
@with_org_context
async def github_list_branches(req: func.HttpRequest) -> func.HttpResponse:
    """List branches in a repository using token from Key Vault"""
    try:
        repo_full_name = req.params.get("repo")

        if not repo_full_name:
            return func.HttpResponse(
                body=json.dumps({"error": "MissingParameters", "message": "Repository name required"}),
                status_code=400,
                mimetype="application/json",
            )

        # Get token from Config table
        token = await _get_github_token(req)

        if not token:
            return func.HttpResponse(
                body=json.dumps({"error": "NotConfigured", "message": "GitHub token not found. Please validate your token first."}),
                status_code=400,
                mimetype="application/json",
            )

        git_service = GitIntegrationService()
        branches = git_service.list_branches(token, repo_full_name)

        response = GitHubBranchesResponse(branches=branches)

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to list branches: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "GitHubError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/commits", methods=["GET"])
@bp.function_name("github_commits")
@openapi_endpoint(
    path="/github/commits",
    method="GET",
    summary="Get commit history",
    description="Get commit history for the current branch with push status",
    tags=["GitHub"],
    response_model=CommitHistoryResponse,
)
@with_org_context
async def github_commits(req: func.HttpRequest) -> func.HttpResponse:
    """Get commit history with pagination"""
    try:
        _context = get_org_context(req)  # noqa: F841 - Required for auth

        # Get limit and offset from query params
        limit_str = req.params.get('limit', '20')
        offset_str = req.params.get('offset', '0')

        try:
            limit = int(limit_str)
            limit = max(1, min(limit, 100))  # Clamp between 1 and 100
        except ValueError:
            limit = 20

        try:
            offset = int(offset_str)
            offset = max(0, offset)  # Ensure non-negative
        except ValueError:
            offset = 0

        git_service = GitIntegrationService()
        result = await git_service.get_commit_history(limit=limit, offset=offset)

        response = CommitHistoryResponse(
            commits=result["commits"],
            total_commits=result["total"],
            has_more=result["has_more"]
        )

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to get commit history: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "GitError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/fetch", methods=["POST"])
@bp.function_name("github_fetch")
@openapi_endpoint(
    path="/github/fetch",
    method="POST",
    summary="Fetch from GitHub",
    description="Fetch latest refs from GitHub without merging (lightweight check for updates)",
    tags=["GitHub"],
    response_model=FetchFromGitHubResponse,
)
@with_org_context
async def github_fetch(req: func.HttpRequest) -> func.HttpResponse:
    """Fetch latest refs from GitHub (no merge)"""
    try:
        context = get_org_context(req)
        git_service = GitIntegrationService()

        # Check if Git repo is initialized
        if not git_service.is_git_repo():
            return func.HttpResponse(
                body=json.dumps({"error": "NotInitialized", "message": "Git repository not initialized"}),
                status_code=400,
                mimetype="application/json",
            )

        # Fetch from remote with authentication
        await git_service.fetch_from_remote(context)

        # Get ahead/behind counts
        ahead, behind = await git_service.get_commits_ahead_behind()

        response = FetchFromGitHubResponse(
            success=True,
            commits_ahead=ahead,
            commits_behind=behind,
            error=None
        )

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to fetch from GitHub: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "FetchError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/refresh", methods=["POST"])
@bp.function_name("github_refresh")
@openapi_endpoint(
    path="/github/refresh",
    method="POST",
    summary="Refresh Git status",
    description="Get complete Git status using GitHub API (fast) including local changes, ahead/behind counts, and commit history",
    tags=["GitHub"],
    response_model=GitRefreshStatusResponse,
)
@with_org_context
async def github_refresh(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get complete Git status.
    By default, only returns local status (fast).
    Pass ?fetch=true to also fetch from remote (slow on SMB).
    """
    try:
        context = get_org_context(req)
        git_service = GitIntegrationService()

        # Check if fetch parameter is provided
        fetch = req.params.get('fetch', 'false').lower() == 'true'

        # Get complete refresh status
        # fetch=False (default): Fast, local status only
        # fetch=True: Slow, fetches from remote first
        result = await git_service.refresh_status(context, fetch=fetch)

        response = GitRefreshStatusResponse(**result)

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to get sync status: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "SyncStatusError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/discard", methods=["POST"])
@bp.function_name("github_discard")
@openapi_endpoint(
    path="/github/discard",
    method="POST",
    summary="Discard unpushed commits",
    description="Reset local branch to match remote, discarding any unpushed local commits",
    tags=["GitHub"],
    response_model=DiscardUnpushedCommitsResponse,
)
@with_org_context
async def github_discard(req: func.HttpRequest) -> func.HttpResponse:
    """Discard all unpushed local commits"""
    try:
        context = get_org_context(req)
        git_service = GitIntegrationService()

        # Check if Git repo is initialized
        if not git_service.is_git_repo():
            return func.HttpResponse(
                body=json.dumps({"error": "NotInitialized", "message": "Git repository not initialized"}),
                status_code=400,
                mimetype="application/json",
            )

        # Discard unpushed commits (fetch from remote first)
        result = await git_service.discard_unpushed_commits(context)

        response = DiscardUnpushedCommitsResponse(**result)

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to discard unpushed commits: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "DiscardError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/discard/{commit_sha}", methods=["POST"])
@bp.function_name("github_discard_commit")
@openapi_endpoint(
    path="/github/discard/{commit_sha}",
    method="POST",
    summary="Discard a specific commit",
    description="Discard a specific unpushed commit and all commits newer than it by resetting to its parent",
    tags=["GitHub"],
    response_model=DiscardUnpushedCommitsResponse,
)
@with_org_context
async def github_discard_commit(req: func.HttpRequest) -> func.HttpResponse:
    """Discard a specific commit and all newer commits"""
    try:
        # Get commit SHA from path parameter
        commit_sha = req.route_params.get('commit_sha')
        if not commit_sha:
            return func.HttpResponse(
                body=json.dumps({"error": "MissingParameter", "message": "commit_sha path parameter is required"}),
                status_code=400,
                mimetype="application/json",
            )

        context = get_org_context(req)
        git_service = GitIntegrationService()

        # Check if Git repo is initialized
        if not git_service.is_git_repo():
            return func.HttpResponse(
                body=json.dumps({"error": "NotInitialized", "message": "Git repository not initialized"}),
                status_code=400,
                mimetype="application/json",
            )

        # Discard the commit (fetch from remote first)
        result = await git_service.discard_commit(commit_sha, context)

        response = DiscardUnpushedCommitsResponse(**result)

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to discard commit: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "DiscardError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/pull", methods=["POST"])
@bp.function_name("github_pull")
@openapi_endpoint(
    path="/github/pull",
    method="POST",
    summary="Pull from GitHub",
    description="Fetch and merge changes from GitHub repository",
    tags=["GitHub"],
    request_model=PullFromGitHubRequest,
    response_model=PullFromGitHubResponse,
)
@with_org_context
async def github_pull(req: func.HttpRequest) -> func.HttpResponse:
    """Pull changes from GitHub"""
    try:
        logger.info("=== GitHub Pull Endpoint Called ===")

        # Parse request body
        request_data = json.loads(req.get_body().decode('utf-8')) if req.get_body() else {}
        pull_request = PullFromGitHubRequest(**request_data)

        # Get configuration from Config table
        token = await _get_github_token(req)
        context = get_org_context(req)
        config_repo = ConfigRepository(context)
        github_config = await config_repo.get_github_config()

        if not token or not github_config or not github_config.repo_url:
            logger.warning("GitHub not configured for pull operation")
            return func.HttpResponse(
                body=json.dumps({"error": "NotConfigured", "message": "GitHub integration not configured"}),
                status_code=400,
                mimetype="application/json",
            )

        logger.info(f"Pulling from repository: {github_config.repo_url}")
        git_service = GitIntegrationService()
        result = await git_service.pull(context, connection_id=pull_request.connection_id)
        logger.info(f"Pull result: success={result['success']}, updated_files={len(result['updated_files'])}, conflicts={len(result['conflicts'])}, error={result.get('error')}")

        response = PullFromGitHubResponse(
            success=result["success"],
            updated_files=result["updated_files"],
            conflicts=result["conflicts"],
            error=result["error"]
        )

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to pull from GitHub: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "PullError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/sync", methods=["POST"])
@bp.function_name("github_sync")
@openapi_endpoint(
    path="/github/sync",
    method="POST",
    summary="Sync with GitHub",
    description="Atomic pull + push operation. Queues a job that pulls changes, checks for conflicts, and pushes if clean.",
    tags=["GitHub"],
    request_model=GitHubSyncRequest,
    response_model=GitHubSyncResponse,
)
@with_org_context
async def github_sync(req: func.HttpRequest) -> func.HttpResponse:
    """Sync with GitHub (pull + push)"""
    try:
        # Parse request body
        request_data = json.loads(req.get_body().decode('utf-8')) if req.get_body() else {}
        sync_request = GitHubSyncRequest(**request_data)

        # Get organization context
        context = get_org_context(req)
        git_service = GitIntegrationService()

        # Check if Git repo is initialized
        if not git_service.is_git_repo():
            return func.HttpResponse(
                body=json.dumps({"error": "NotInitialized", "message": "Git repository not initialized"}),
                status_code=400,
                mimetype="application/json",
            )

        # Generate job ID
        job_id = str(uuid.uuid4())

        # Queue sync job
        connection_string = os.environ.get("AzureWebJobsStorage", "UseDevelopmentStorage=true")
        queue_client = QueueClient.from_connection_string(
            connection_string,
            queue_name="git-sync-jobs",
            message_encode_policy=TextBase64EncodePolicy()
        )

        try:
            ctx = getattr(req, "ctx", None)
            message = {
                "type": "git_sync",
                "job_id": job_id,
                "org_id": context.scope,  # Use scope (GLOBAL or org ID) instead of org_id (can be None)
                "connection_id": sync_request.connection_id,
                "user_id": ctx.user_id if ctx else "",
                "user_email": ctx.email if ctx else ""
            }

            logger.info(f"Queuing git sync job {job_id} with connection_id: {sync_request.connection_id}")
            queue_client.send_message(json.dumps(message))
            logger.info(f"Queued git sync job {job_id}")
        finally:
            queue_client.close()

        return func.HttpResponse(
            body=json.dumps({
                "job_id": job_id,
                "status": "queued"
            }),
            mimetype="application/json",
            status_code=202
        )

    except Exception as e:
        logger.error(f"Failed to queue git sync: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "SyncError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/commit", methods=["POST"])
@bp.function_name("github_commit")
@openapi_endpoint(
    path="/github/commit",
    method="POST",
    summary="Commit changes",
    description="Commit all changes locally",
    tags=["GitHub"],
    request_model=CommitAndPushRequest,
    response_model=CommitAndPushResponse,
)
@with_org_context
async def github_commit(req: func.HttpRequest) -> func.HttpResponse:
    """Commit changes locally"""
    try:
        # Parse request
        request_data = json.loads(req.get_body())
        commit_request = CommitAndPushRequest(**request_data)

        git_service = GitIntegrationService()
        result = await git_service.commit(commit_request.message)

        response = CommitAndPushResponse(
            success=result["success"],
            commit_sha=result["commit_sha"],
            files_committed=result["files_committed"],
            error=result["error"]
        )

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to commit: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "CommitError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/push", methods=["POST"])
@bp.function_name("github_push")
@openapi_endpoint(
    path="/github/push",
    method="POST",
    summary="Push to GitHub",
    description="Push local commits to GitHub without committing",
    tags=["GitHub"],
    request_model=PushToGitHubRequest,
    response_model=PushToGitHubResponse,
)
@with_org_context
async def github_push(req: func.HttpRequest) -> func.HttpResponse:
    """Push to GitHub"""
    logger.info("=== GitHub Push Endpoint Called ===")
    try:
        # Parse request body
        request_data = json.loads(req.get_body().decode('utf-8')) if req.get_body() else {}
        push_request = PushToGitHubRequest(**request_data)

        # Get configuration from Config table
        token = await _get_github_token(req)
        context = get_org_context(req)
        config_repo = ConfigRepository(context)
        github_config = await config_repo.get_github_config()

        if not token or not github_config or not github_config.repo_url:
            logger.warning("GitHub not configured")
            return func.HttpResponse(
                body=json.dumps({"error": "NotConfigured", "message": "GitHub integration not configured"}),
                status_code=400,
                mimetype="application/json",
            )

        logger.info(f"Pushing to repository: {github_config.repo_url}")
        git_service = GitIntegrationService()
        result = await git_service.push(context, connection_id=push_request.connection_id)

        logger.info(f"Push result: success={result['success']}, error={result.get('error')}")

        response = PushToGitHubResponse(
            success=result["success"],
            error=result["error"]
        )

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to push: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "PushError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )

@bp.route(route="github/conflicts/resolve", methods=["POST"])
@bp.function_name("github_resolve_conflict")
@openapi_endpoint(
    path="/github/conflicts/resolve",
    method="POST",
    summary="Resolve merge conflict",
    description="Resolve a merge conflict in a file",
    tags=["GitHub"],
    request_model=ResolveConflictRequest,
    response_model=ResolveConflictResponse,
)
@with_org_context
async def github_resolve_conflict(req: func.HttpRequest) -> func.HttpResponse:
    """Resolve a merge conflict"""
    try:
        # Parse request
        request_data = json.loads(req.get_body())
        resolve_request = ResolveConflictRequest(**request_data)

        git_service = GitIntegrationService()
        remaining_conflicts = await git_service.resolve_conflict(
            resolve_request.file_path,
            resolve_request.resolution,
            resolve_request.manual_content
        )

        response = ResolveConflictResponse(
            success=True,
            file_path=resolve_request.file_path,
            remaining_conflicts=remaining_conflicts
        )

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to resolve conflict: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "ResolveError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/analyze-workspace", methods=["POST"])
@bp.function_name("github_analyze_workspace")
@openapi_endpoint(
    path="/github/analyze-workspace",
    method="POST",
    summary="Analyze workspace for conflicts",
    description="Analyze workspace and remote repository to determine conflict resolution needs",
    tags=["GitHub"],
    request_model=GitHubConfigRequest,
    response_model=WorkspaceAnalysisResponse,
)
@with_org_context
async def github_analyze_workspace(req: func.HttpRequest) -> func.HttpResponse:
    """Analyze workspace for potential conflicts before configuration"""
    try:
        # Parse request
        request_data = json.loads(req.get_body())
        config_request = GitHubConfigRequest(**request_data)

        logger.info(f"Analyzing workspace for repo: {config_request.repo_url}")

        # Get saved token
        token = await _get_github_token(req)
        if not token:
            return func.HttpResponse(
                body=json.dumps({
                    "error": "NotConfigured",
                    "message": "GitHub token not found. Please validate your token first."
                }),
                status_code=400,
                mimetype="application/json",
            )

        git_service = GitIntegrationService()
        analysis = await git_service.analyze_workspace(
            token=token,
            repo_url=config_request.repo_url,
            branch=config_request.branch
        )

        return func.HttpResponse(
            body=json.dumps(analysis),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to analyze workspace: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "AnalysisError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/create-repo", methods=["POST"])
@bp.function_name("github_create_repo")
@openapi_endpoint(
    path="/github/create-repo",
    method="POST",
    summary="Create new GitHub repository",
    description="Create a new GitHub repository using saved token",
    tags=["GitHub"],
    request_model=CreateRepoRequest,
    response_model=CreateRepoResponse,
)
@with_org_context
async def github_create_repo(req: func.HttpRequest) -> func.HttpResponse:
    """Create a new GitHub repository using token from Key Vault"""
    try:
        # Get token from Config table
        token = await _get_github_token(req)

        if not token:
            return func.HttpResponse(
                body=json.dumps({"error": "NotConfigured", "message": "GitHub token not found. Please validate your token first."}),
                status_code=400,
                mimetype="application/json",
            )

        # Parse request
        request_data = json.loads(req.get_body())
        create_request = CreateRepoRequest(**request_data)

        logger.info(f"Creating repository: {create_request.name}")

        git_service = GitIntegrationService()
        repo_info = git_service.create_repository(
            token=token,
            name=create_request.name,
            description=create_request.description,
            private=create_request.private,
            organization=create_request.organization
        )

        return func.HttpResponse(
            body=json.dumps(repo_info),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to create repository: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "CreateRepoError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="github/disconnect", methods=["POST"])
@bp.function_name("github_disconnect")
@openapi_endpoint(
    path="/github/disconnect",
    method="POST",
    summary="Disconnect GitHub integration",
    description="Mark GitHub integration as disconnected (does not delete secrets)",
    tags=["GitHub"],
)
@with_org_context
async def github_disconnect(req: func.HttpRequest) -> func.HttpResponse:
    """Disconnect GitHub integration by updating status to disconnected"""
    try:
        logger.info("Disconnecting GitHub integration")

        # Update Config table to mark as disconnected (don't delete secrets)
        context = get_org_context(req)
        config_repo = ConfigRepository(context)

        updated_config = await config_repo.update_github_status(
            status="disconnected",
            updated_by=context.email or "system"
        )

        if not updated_config:
            return func.HttpResponse(
                body=json.dumps({
                    "error": "NotConfigured",
                    "message": "No GitHub configuration found"
                }),
                status_code=404,
                mimetype="application/json",
            )

        logger.info("GitHub integration marked as disconnected")

        return func.HttpResponse(
            body=json.dumps({"success": True, "message": "GitHub integration disconnected"}),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to disconnect GitHub: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "DisconnectError", "message": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
