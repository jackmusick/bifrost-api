"""
GitHub Integration Router

Git/GitHub integration for workspace sync.
Provides endpoints for connecting to repos, pulling, pushing, and syncing.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from shared.models import (
    GitHubConfigRequest,
    PullFromGitHubRequest,
    PullFromGitHubResponse,
    PushToGitHubRequest,
    PushToGitHubResponse,
    GitRefreshStatusResponse,
    CommitHistoryResponse,
    DiscardUnpushedCommitsResponse,
    DiscardCommitRequest,
)
from shared.services.git_integration_service import GitIntegrationService
from src.core.auth import Context, CurrentSuperuser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/github", tags=["GitHub"])


# =============================================================================
# Helper Functions
# =============================================================================


def get_git_service() -> GitIntegrationService:
    """Get or create git integration service."""
    return GitIntegrationService()


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.get(
    "/status",
    response_model=GitRefreshStatusResponse,
    summary="Get GitHub sync status",
    description="Get current GitHub repository connection and sync status",
)
async def get_github_status(
    ctx: Context,
    user: CurrentSuperuser,
) -> GitRefreshStatusResponse:
    """
    Get GitHub sync status.

    Returns:
        Current sync status and repository information
    """
    try:
        git_service = get_git_service()

        # Use get_repo_info to get repository status
        status_dict = await git_service.get_repo_info(ctx, fetch=False)

        logger.info(f"GitHub status retrieved")

        return GitRefreshStatusResponse(**status_dict)

    except Exception as e:
        logger.error(f"Error getting GitHub status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get GitHub status",
        )


@router.post(
    "/pull",
    response_model=PullFromGitHubResponse,
    summary="Pull from GitHub",
    description="Pull latest changes from the connected GitHub repository",
)
async def pull_from_github(
    ctx: Context,
    user: CurrentSuperuser,
    request: PullFromGitHubRequest | None = None,
) -> PullFromGitHubResponse:
    """
    Pull latest changes from GitHub.

    Returns:
        Pull response with pull status and any conflicts
    """
    try:
        git_service = get_git_service()

        # Pull from repository - pull() returns a dict with result info
        connection_id = request.connection_id if request else None
        result = await git_service.pull(ctx, connection_id)

        logger.info(f"Pulled from GitHub")

        return PullFromGitHubResponse(**result)

    except Exception as e:
        logger.error(f"Error pulling from GitHub: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pull from GitHub",
        )


@router.post(
    "/push",
    response_model=PushToGitHubResponse,
    summary="Push to GitHub",
    description="Push local changes to the connected GitHub repository",
)
async def push_to_github(
    ctx: Context,
    user: CurrentSuperuser,
    request: PushToGitHubRequest,
) -> PushToGitHubResponse:
    """
    Push local changes to GitHub.

    Args:
        request: Commit message and author information

    Returns:
        Push response with confirmation
    """
    try:
        git_service = get_git_service()

        # Commit and push in one operation
        result = await git_service.commit_and_push(
            ctx,
            message=request.message or "Updated from Bifrost",
            connection_id=None
        )

        return PushToGitHubResponse(
            success=result.get("success", True),
            error=result.get("error")
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error pushing to GitHub: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to push to GitHub",
        )


@router.get(
    "/changes",
    response_model=GitRefreshStatusResponse,
    summary="Get local changes",
    description="List local changes not yet pushed to GitHub",
)
async def get_changes(
    ctx: Context,
    user: CurrentSuperuser,
) -> GitRefreshStatusResponse:
    """
    Get list of local changes.

    Returns:
        Local file changes not yet pushed
    """
    try:
        git_service = get_git_service()

        # Use get_repo_info to get complete status including changes
        status_dict = await git_service.get_repo_info(ctx, fetch=False)

        logger.info(f"Retrieved local changes")

        return GitRefreshStatusResponse(**status_dict)

    except Exception as e:
        logger.error(f"Error getting changes: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get changes",
        )


@router.post(
    "/init",
    response_model=GitRefreshStatusResponse,
    summary="Initialize Git repository",
    description="Initialize workspace as a Git repository with remote (stub)",
)
async def init_repo(
    request: GitHubConfigRequest,
    ctx: Context,
    user: CurrentSuperuser,
) -> GitRefreshStatusResponse:
    """
    Initialize the workspace as a Git repository.

    This is a stub endpoint for API compatibility.
    """
    try:
        git_service = get_git_service()

        # Get token from request (should be provided)
        if not request.auth_token:
            raise ValueError("auth_token is required to initialize repository")

        # Initialize repository with the provided config
        result = await git_service.initialize_repo(
            token=request.auth_token,
            repo_url=request.repo_url,
            branch=request.branch or "main",
        )

        logger.info(f"Initialized git repository: {request.repo_url}")

        # Get current status after initialization
        status_dict = await git_service.get_repo_info(ctx, fetch=False)
        return GitRefreshStatusResponse(**status_dict)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error initializing repo: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize repository",
        )


@router.post(
    "/commit",
    summary="Commit local changes",
    description="Commit staged changes with a message (stub)",
)
async def commit_changes(
    request: PushToGitHubRequest,
    ctx: Context,
    user: CurrentSuperuser,
) -> dict:
    """
    Commit local changes.

    This is a stub endpoint for API compatibility.
    The push endpoint handles commit + push together.
    """
    try:
        git_service = get_git_service()

        # Get changes
        changes = await git_service.get_changes()

        if not changes:
            return {
                "message": "No changes to commit",
                "commit_hash": None,
            }

        # Commit the changes
        result = await git_service.commit(message=request.message or "Update from Bifrost")

        logger.info(f"Committed {len(changes)} changes")

        return result

    except Exception as e:
        logger.error(f"Error committing changes: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to commit changes",
        )


@router.get(
    "/commits",
    response_model=CommitHistoryResponse,
    summary="Get commit history",
    description="Get commit history with pagination",
)
async def get_commits(
    ctx: Context,
    user: CurrentSuperuser,
    limit: int = Query(20, description="Number of commits to return"),
    offset: int = Query(0, description="Offset for pagination"),
) -> CommitHistoryResponse:
    """
    Get commit history with pagination support.

    Returns commit history with pushed/unpushed status and pagination info.
    """
    try:
        git_service = get_git_service()

        result = await git_service.get_commit_history(
            limit=limit,
            offset=offset
        )

        return CommitHistoryResponse(**result)

    except Exception as e:
        logger.error(f"Error getting commits: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get commit history",
        )


@router.get(
    "/conflicts",
    summary="Get merge conflicts",
    description="List files with merge conflicts (stub)",
)
async def get_conflicts(
    ctx: Context,
    user: CurrentSuperuser,
) -> dict:
    """
    Get files with merge conflicts.

    This is a stub endpoint for API compatibility.
    """
    try:
        git_service = get_git_service()

        conflicts = await git_service.get_conflicts()

        return {
            "conflicts": conflicts,
            "count": len(conflicts),
        }

    except Exception as e:
        logger.error(f"Error getting conflicts: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get conflicts",
        )


@router.post(
    "/abort-merge",
    summary="Abort merge",
    description="Abort current merge operation (stub)",
)
async def abort_merge(
    ctx: Context,
    user: CurrentSuperuser,
) -> dict:
    """
    Abort a merge operation.

    This is a stub endpoint for API compatibility.
    """
    try:
        git_service = get_git_service()

        await git_service.abort_merge()

        logger.info("Aborted merge operation")

        return {
            "message": "Merge aborted successfully",
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Error aborting merge: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to abort merge",
        )


@router.post(
    "/discard-unpushed",
    response_model=DiscardUnpushedCommitsResponse,
    summary="Discard unpushed commits",
    description="Discard all unpushed commits and reset to remote",
)
async def discard_unpushed_commits(
    ctx: Context,
    user: CurrentSuperuser,
) -> DiscardUnpushedCommitsResponse:
    """
    Discard all unpushed commits.

    Resets the local branch to match the remote tracking branch,
    discarding any local commits that haven't been pushed.

    Returns:
        Response with list of discarded commits
    """
    try:
        git_service = get_git_service()

        result = await git_service.discard_unpushed_commits(ctx)

        logger.info(f"Discarded {len(result.get('discarded_commits', []))} unpushed commits")

        return DiscardUnpushedCommitsResponse(**result)

    except Exception as e:
        logger.error(f"Error discarding unpushed commits: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to discard unpushed commits",
        )


@router.post(
    "/discard-commit",
    response_model=DiscardUnpushedCommitsResponse,
    summary="Discard specific commit",
    description="Discard a specific commit and all newer commits",
)
async def discard_commit(
    ctx: Context,
    user: CurrentSuperuser,
    request: DiscardCommitRequest,
) -> DiscardUnpushedCommitsResponse:
    """
    Discard a specific commit and all newer commits.

    Resets the branch to the parent of the specified commit,
    effectively removing the commit and all commits after it.

    Returns:
        Response with list of discarded commits
    """
    try:
        git_service = get_git_service()

        result = await git_service.discard_commit(request.commit_sha, ctx)

        logger.info(f"Discarded commit {request.commit_sha} and {len(result.get('discarded_commits', []))} commits")

        return DiscardUnpushedCommitsResponse(**result)

    except Exception as e:
        logger.error(f"Error discarding commit: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to discard commit",
        )
