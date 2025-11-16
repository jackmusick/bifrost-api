"""
Git Integration Service

Handles GitHub repository synchronization with workspace.
Provides Git operations: clone, pull, push, conflict resolution.
Uses Dulwich (pure Python Git implementation) - works without git binary.
"""

import logging
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from dulwich import porcelain
from dulwich.repo import Repo as DulwichRepo
from dulwich.errors import NotGitRepository
from dulwich.porcelain import DivergedBranches
from github import Github, GithubException

from typing import Any

from shared.models import (
    FileChange,
    GitFileStatus,
    ConflictInfo,
    GitHubRepoInfo,
    GitHubBranchInfo,
    CommitInfo,
)
from shared.repositories.config import ConfigRepository
from shared.keyvault import KeyVaultClient

logger = logging.getLogger(__name__)


class GitIntegrationService:
    """
    Service for Git/GitHub integration.

    Manages workspace synchronization with GitHub repository.
    Handles cloning, pulling, pushing, and conflict resolution.
    Uses Dulwich (pure Python) instead of GitPython.
    """

    def __init__(self, workspace_path: str | None = None):
        """
        Initialize Git integration service.

        Args:
            workspace_path: Path to workspace directory (default: BIFROST_WORKSPACE_LOCATION env var)
        """
        self.workspace_path = Path(
            workspace_path or os.environ.get('BIFROST_WORKSPACE_LOCATION', '/mounts/workspace')
        )

        if not self.workspace_path.exists():
            raise RuntimeError(
                f"Workspace directory does not exist: {self.workspace_path}"
            )

        logger.info(f"Initialized Git integration service at: {self.workspace_path}")

    def is_git_repo(self) -> bool:
        """Check if workspace is a Git repository"""
        try:
            DulwichRepo(str(self.workspace_path))
            return True
        except NotGitRepository:
            return False

    def get_repo(self) -> DulwichRepo:
        """Get Dulwich repository instance"""
        if not self.is_git_repo():
            raise ValueError("Workspace is not a Git repository. Call initialize_repo() first.")
        return DulwichRepo(str(self.workspace_path))

    async def initialize_repo(
        self,
        token: str,
        repo_url: str,
        branch: str = "main"
    ) -> dict | None:
        """
        Initialize Git repository from GitHub.

        If workspace is empty: clone repository
        If workspace has files: backup and replace with repository

        Args:
            token: GitHub personal access token
            repo_url: GitHub repository URL or owner/repo format
            branch: Branch to clone (default: main)

        Returns:
            dict with backup_path if workspace was backed up, None otherwise

        Raises:
            ValueError: If repo_url is invalid
            Exception: If Git operations fail
        """
        logger.info(f"Initializing Git repo from {repo_url} (branch: {branch})")

        # Normalize repo URL - accept both full URLs and owner/repo format
        if not repo_url.startswith(('https://github.com/', 'git@github.com:')):
            # Assume it's in owner/repo format, convert to HTTPS URL
            repo_url = f"https://github.com/{repo_url}"
            logger.info(f"Normalized repo URL to: {repo_url}")

        # Validate normalized URL
        if not repo_url.startswith(('https://github.com/', 'git@github.com:')):
            raise ValueError("Invalid GitHub repository URL")

        # Convert HTTPS URL to use token authentication
        auth_url = self._insert_token_in_url(repo_url, token)

        # Check workspace state
        workspace_empty = not any(self.workspace_path.iterdir())
        is_git_repo = self.is_git_repo()

        result = None

        # Scenario 1: Already a Git repo - just update remote
        if is_git_repo:
            logger.info("Workspace is already a Git repository, updating configuration...")
            self._update_existing_repo(auth_url, branch)

        # Scenario 2: Empty workspace - just clone
        elif workspace_empty:
            logger.info("Workspace is empty, cloning repository...")
            self._clone_repo(auth_url, branch)

        # Scenario 3: Has files but no Git - backup and replace
        else:
            logger.info("Workspace has files, backing up and replacing with repository...")
            backup_path = await self._clear_and_clone(auth_url, branch)
            result = {"backup_path": backup_path}

        logger.info("Repository initialized successfully")
        return result

    def _insert_token_in_url(self, repo_url: str, token: str) -> str:
        """Insert GitHub token into HTTPS URL for authentication"""
        if repo_url.startswith('git@github.com:'):
            # Convert SSH to HTTPS with token
            repo_path = repo_url.replace('git@github.com:', '')
            return f'https://{token}@github.com/{repo_path}'

        # Insert token into URL
        return repo_url.replace('https://github.com/', f'https://{token}@github.com/')

    async def _get_authenticated_remote_url(self, context: Any) -> str | None:
        """
        Get authenticated remote URL with token from Key Vault.

        Args:
            context: Organization context

        Returns:
            Authenticated URL with token, or None if not configured
        """
        config_repo = ConfigRepository(context)
        github_config = await config_repo.get_github_config()

        if not github_config or not github_config.secret_ref:
            return None

        if github_config.status == "disconnected":
            return None

        # Get token from Key Vault
        async with KeyVaultClient() as kv_client:
            try:
                token = await kv_client.get_secret(github_config.secret_ref)
            except Exception as e:
                logger.warning(f"Failed to retrieve token from Key Vault: {e}")
                return None

        # Normalize repo URL - accept both full URLs and owner/repo format
        repo_url = github_config.repo_url
        if not repo_url.startswith(('https://github.com/', 'git@github.com:')):
            # Convert owner/repo format to HTTPS URL
            repo_url = f"https://github.com/{repo_url}"
            logger.debug(f"Normalized repo URL to: {repo_url}")

        # Build authenticated URL
        return self._insert_token_in_url(repo_url, token)

    def _clone_repo(self, auth_url: str, branch: str) -> None:
        """Clone repository using Dulwich"""
        logger.info(f"Cloning repository (branch: {branch})")

        # Clone the repository
        porcelain.clone(
            auth_url,
            str(self.workspace_path),
            checkout=True,
            branch=branch.encode('utf-8')
        )

        logger.info("Repository cloned successfully")

    def _update_existing_repo(self, auth_url: str, branch: str) -> None:
        """Update an existing Git repository with new remote"""
        repo = self.get_repo()

        # Update or create origin remote
        config = repo.get_config()
        config.set((b'remote', b'origin'), b'url', auth_url.encode('utf-8'))
        config.set((b'remote', b'origin'), b'fetch', b'+refs/heads/*:refs/remotes/origin/*')
        config.write_to_path()

        # Fetch from remote
        porcelain.fetch(repo, remote_location=auth_url)

        # Checkout branch
        branch_ref = f'refs/heads/{branch}'.encode('utf-8')
        remote_ref = f'refs/remotes/origin/{branch}'.encode('utf-8')

        # Create local branch tracking remote
        repo.refs[branch_ref] = repo.refs[remote_ref]

        # Checkout the branch
        porcelain.reset(repo, "hard", branch_ref.decode('utf-8'))  # type: ignore[call-arg]

    async def _clear_and_clone(self, auth_url: str, branch: str) -> str:
        """
        Clear workspace, clone from remote, and install requirements.

        Returns:
            backup_dir: Path to backup directory
        """
        logger.info("Clearing workspace and cloning from remote")

        # Create temporary backup
        backup_dir = Path(tempfile.mkdtemp(prefix="bifrost_backup_"))
        logger.info(f"Creating backup at {backup_dir}")

        # Move all files to backup
        for item in self.workspace_path.iterdir():
            shutil.move(str(item), str(backup_dir / item.name))

        # Clone repository
        self._clone_repo(auth_url, branch)

        logger.info(f"Replaced workspace with remote content. Backup available at {backup_dir}")

        # Install requirements if requirements.txt exists
        requirements_file = self.workspace_path / "requirements.txt"
        if requirements_file.exists():
            logger.info("Installing requirements from requirements.txt")
            from shared.package_manager import PackageManager  # type: ignore[attr-defined]

            package_manager = PackageManager(workspace_path=self.workspace_path)
            try:
                # Note: We can't stream here since this is called from initialize_repo
                # Just run the install silently
                await package_manager.install_requirements_streaming()
                logger.info("Requirements installed successfully")
            except Exception as e:
                logger.warning(f"Failed to install requirements: {e}")
                # Don't fail the whole operation if requirements install fails

        return str(backup_dir)

    async def fetch_from_remote(self, context: Any) -> None:
        """
        Fetch latest refs from remote without merging.
        Lightweight operation to update remote tracking branches.

        Args:
            context: Organization context for retrieving GitHub configuration
        """
        if not self.is_git_repo():
            logger.warning("Not a git repo, skipping fetch")
            return

        # Get authenticated URL
        auth_url = await self._get_authenticated_remote_url(context)
        if not auth_url:
            logger.warning("No GitHub configuration found, cannot fetch")
            return

        logger.info(f"Fetching from remote: {auth_url.replace(auth_url.split('@')[0].split('//')[1], '***') if '@' in auth_url else auth_url}")

        try:
            repo = self.get_repo()
            result = porcelain.fetch(repo, remote_location=auth_url)
            logger.info(f"Fetched latest refs from remote. Refs: {result.refs}")

            # Update remote tracking branches manually
            # porcelain.fetch() downloads objects but doesn't update remote refs
            for remote_ref, sha in result.refs.items():
                # Skip symbolic refs like HEAD
                if remote_ref == b'HEAD':
                    continue

                # Map refs/heads/branch to refs/remotes/origin/branch
                if remote_ref.startswith(b'refs/heads/'):
                    branch_name = remote_ref[len(b'refs/heads/'):]
                    local_remote_ref = b'refs/remotes/origin/' + branch_name
                    repo.refs[local_remote_ref] = sha
                    logger.info(f"Updated {local_remote_ref.decode()} to {sha.decode()}")

        except Exception as e:
            logger.error(f"Failed to fetch from remote: {e}", exc_info=True)

    async def get_commits_ahead_behind(self) -> tuple[int, int]:
        """
        Get number of commits ahead/behind remote.

        Returns:
            Tuple of (commits_ahead, commits_behind)
        """
        if not self.is_git_repo():
            logger.warning("Not a git repo, returning (0, 0)")
            return (0, 0)

        try:
            repo = self.get_repo()

            # Get current branch name from symbolic ref
            head_path = repo.refs.read_ref(b'HEAD')
            if not head_path or not head_path.startswith(b'ref: '):
                logger.warning("HEAD is detached or invalid, returning (0, 0)")
                return (0, 0)

            branch_ref = head_path[5:].strip()  # Remove "ref: " prefix
            branch_name = branch_ref.split(b'/')[-1].decode('utf-8')
            logger.info(f"Current branch: {branch_name}")

            # Get remote tracking branch
            remote_ref = f'refs/remotes/origin/{branch_name}'.encode('utf-8')
            logger.info(f"Looking for remote ref: {remote_ref.decode('utf-8')}")

            # List all refs to debug
            all_refs = list(repo.refs.keys())
            logger.info(f"All refs in repo: {[r.decode('utf-8') for r in all_refs if b'remote' in r]}")

            if remote_ref not in repo.refs:
                logger.warning(f"Remote ref {remote_ref.decode('utf-8')} not found, returning (0, 0)")
                return (0, 0)

            local_commit = repo.refs[branch_ref]
            remote_commit = repo.refs[remote_ref]

            logger.info(f"Local commit: {local_commit.decode('utf-8')}")
            logger.info(f"Remote commit: {remote_commit.decode('utf-8')}")

            if local_commit == remote_commit:
                logger.info("Local and remote are at same commit")
                return (0, 0)

            # Walk commit graph to count commits ahead and behind
            # Ahead: commits in local that aren't in remote
            walker = repo.get_walker(include=[local_commit], exclude=[remote_commit])
            ahead = sum(1 for _ in walker)

            # Behind: commits in remote that aren't in local
            walker = repo.get_walker(include=[remote_commit], exclude=[local_commit])
            behind = sum(1 for _ in walker)

            logger.info(f"Commits ahead: {ahead}, behind: {behind}")
            return (ahead, behind)

        except Exception as e:
            logger.error(f"Failed to get commits ahead/behind: {e}", exc_info=True)
            return (0, 0)

    def get_current_branch(self) -> str | None:
        """
        Get the name of the current branch.

        Returns:
            Branch name or None if not in a Git repo or detached HEAD
        """
        if not self.is_git_repo():
            return None

        try:
            repo = self.get_repo()
            head_path = repo.refs.read_ref(b'HEAD')

            if not head_path or not head_path.startswith(b'ref: '):
                return None

            # Extract branch name from "ref: refs/heads/main"
            branch_ref = head_path[5:].strip()  # Remove "ref: " prefix
            if branch_ref.startswith(b'refs/heads/'):
                return branch_ref[11:].decode('utf-8')  # Remove "refs/heads/"

            return None

        except Exception as e:
            logger.warning(f"Failed to get current branch: {e}")
            return None

    async def get_commit_history(self, limit: int = 20) -> list[CommitInfo]:
        """
        Get commit history for the current branch.

        Args:
            limit: Maximum number of commits to return (default 20)

        Returns:
            List of CommitInfo objects with commit details
        """
        if not self.is_git_repo():
            return []

        try:
            repo = self.get_repo()
            current_branch = self.get_current_branch()
            if not current_branch:
                return []

            # Get current HEAD commit
            head_ref = f'refs/heads/{current_branch}'.encode('utf-8')
            if head_ref not in repo.refs:
                return []

            head_commit_sha = repo.refs[head_ref]

            # Get remote tracking ref to determine which commits are pushed
            remote_ref = f'refs/remotes/origin/{current_branch}'.encode('utf-8')
            remote_commit_sha = repo.refs[remote_ref] if remote_ref in repo.refs else None

            # Get all commits reachable from remote (these are pushed)
            pushed_shas = set()
            if remote_commit_sha:
                walker = repo.get_walker(include=[remote_commit_sha])
                pushed_shas = {entry.commit.id for entry in walker}

            # Walk the commit history
            commits = []
            walker = repo.get_walker(include=[head_commit_sha], max_entries=limit)

            for entry in walker:
                commit = entry.commit
                commit_sha = commit.id

                # Parse commit message (first line)
                message_bytes = commit.message
                message = message_bytes.decode('utf-8').strip() if isinstance(message_bytes, bytes) else message_bytes.strip()

                # Parse author
                author_bytes = commit.author
                if isinstance(author_bytes, bytes):
                    author = author_bytes.decode('utf-8')
                else:
                    author = str(author_bytes)

                # Extract just the name part (before <email>)
                if '<' in author:
                    author = author.split('<')[0].strip()

                # Convert timestamp to ISO 8601
                from datetime import datetime, timezone
                timestamp = datetime.fromtimestamp(commit.commit_time, tz=timezone.utc).isoformat()

                # Check if this commit is pushed
                is_pushed = commit_sha in pushed_shas

                commits.append(CommitInfo(
                    sha=commit_sha.decode('utf-8') if isinstance(commit_sha, bytes) else commit_sha,
                    message=message,
                    author=author,
                    timestamp=timestamp,
                    is_pushed=is_pushed
                ))

            return commits

        except Exception as e:
            logger.error(f"Failed to get commit history: {e}", exc_info=True)
            return []

    async def get_changed_files(self) -> list[FileChange]:
        """
        Get list of changed files in workspace.

        Returns:
            List of FileChange objects with status and diff info
        """
        repo = self.get_repo()
        changes = []

        # Get status using Dulwich
        status = porcelain.status(repo)

        # Helper to decode path (handles both bytes and str)
        def decode_path(path):
            return path.decode('utf-8') if isinstance(path, bytes) else path

        # Staged changes (added to index)
        for path in status.staged['add']:
            changes.append(FileChange(
                path=decode_path(path),
                status=GitFileStatus.ADDED,
                additions=None,
                deletions=None
            ))

        for path in status.staged['modify']:
            changes.append(FileChange(
                path=decode_path(path),
                status=GitFileStatus.MODIFIED,
                additions=None,
                deletions=None
            ))

        for path in status.staged['delete']:
            changes.append(FileChange(
                path=decode_path(path),
                status=GitFileStatus.DELETED,
                additions=None,
                deletions=None
            ))

        # Unstaged changes
        for path in status.unstaged:
            decoded_path = decode_path(path)
            if decoded_path not in [f.path for f in changes]:
                changes.append(FileChange(
                    path=decoded_path,
                    status=GitFileStatus.MODIFIED,
                    additions=None,
                    deletions=None
                ))

        # Untracked files
        for path in status.untracked:
            changes.append(FileChange(
                path=decode_path(path),
                status=GitFileStatus.UNTRACKED,
                additions=None,
                deletions=None
            ))

        return changes

    async def get_conflicts(self) -> list[ConflictInfo]:
        """
        Get list of files with merge conflicts by checking Git index.

        Returns:
            List of ConflictInfo objects (minimal - just file paths from index)
        """
        repo = self.get_repo()
        conflicts = []

        try:
            # Load saved conflicts with full content
            from pathlib import Path
            import json
            conflicts_file = Path(repo.controldir()) / 'BIFROST_CONFLICTS'
            saved_conflicts_map = {}

            if conflicts_file.exists():
                try:
                    saved_conflicts = json.loads(conflicts_file.read_text())
                    saved_conflicts_map = {c['file_path']: c for c in saved_conflicts}
                except Exception as e:
                    logger.warning(f"Failed to load saved conflicts: {e}")

            # Check index for unmerged entries (stage > 0)
            index = repo.open_index()
            path_entries = {}
            for path_bytes, entry in index.items():
                path_str = path_bytes.decode('utf-8', errors='replace')
                stage = (entry.flags >> 12) & 3  # type: ignore[attr-defined]

                if stage > 0:
                    if path_str not in path_entries:
                        path_entries[path_str] = []
                    path_entries[path_str].append(stage)

            # Build conflicts list
            for path_str, stages in path_entries.items():
                if len(stages) > 1:  # Multiple stages = conflict
                    # Use saved conflict data if available, otherwise minimal info
                    if path_str in saved_conflicts_map:
                        conflicts.append(saved_conflicts_map[path_str])
                    else:
                        conflicts.append({
                            "file_path": path_str,
                            "current_content": "",
                            "incoming_content": "",
                            "base_content": None,
                        })

        except Exception as e:
            logger.warning(f"Failed to check for conflicts: {e}")
            return []

        return conflicts

    async def commit(self, message: str) -> dict:
        """
        Commit all changes locally without pushing to remote.

        Args:
            message: Commit message

        Returns:
            dict with commit_sha, files_committed, success status
        """
        repo = self.get_repo()

        try:
            # Stage all changes
            porcelain.add(repo, paths=[b'.'])

            # Commit
            commit_sha = porcelain.commit(
                repo,
                message=message.encode('utf-8'),
                author=b'Bifrost <noreply@bifrost.io>',
                committer=b'Bifrost <noreply@bifrost.io>'
            )

            # Count committed files
            status = porcelain.status(repo)
            files_committed = (
                len(status.staged.get('add', [])) +
                len(status.staged.get('modify', [])) +
                len(status.staged.get('delete', []))
            )

            # If we were in a merge state, clean it up now that merge is complete
            from pathlib import Path
            merge_head_path = Path(repo.controldir()) / 'MERGE_HEAD'
            if merge_head_path.exists():
                merge_head_path.unlink()
                logger.info("Deleted MERGE_HEAD - merge complete")

                # Also clear saved conflicts
                conflicts_file = Path(repo.controldir()) / 'BIFROST_CONFLICTS'
                if conflicts_file.exists():
                    conflicts_file.unlink()
                    logger.info("Cleared saved conflicts file")

            return {
                "success": True,
                "commit_sha": commit_sha.decode('utf-8') if commit_sha else None,
                "files_committed": files_committed,
                "error": None
            }

        except Exception as e:
            logger.error(f"Failed to commit: {e}", exc_info=True)
            return {
                "success": False,
                "commit_sha": None,
                "files_committed": 0,
                "error": f"Failed to commit changes: {str(e)}"
            }

    async def push(self, context: Any) -> dict:
        """
        Push local commits to remote without committing.

        Args:
            context: Organization context for retrieving GitHub configuration

        Returns:
            dict with success status
        """
        repo = self.get_repo()

        try:
            auth_url = await self._get_authenticated_remote_url(context)
            if not auth_url:
                raise Exception("No GitHub configuration found")

            # Get current branch
            current_branch = self.get_current_branch() or 'main'
            refspec = f'refs/heads/{current_branch}:refs/heads/{current_branch}'.encode('utf-8')

            porcelain.push(repo, remote_location=auth_url, refspecs=refspec)

            # Update remote tracking ref to match local after successful push
            local_ref = f'refs/heads/{current_branch}'.encode('utf-8')
            remote_ref = f'refs/remotes/origin/{current_branch}'.encode('utf-8')
            local_commit = repo.refs[local_ref]
            repo.refs.set_if_equals(remote_ref, None, local_commit) if remote_ref not in repo.refs else repo.refs.set_if_equals(remote_ref, repo.refs[remote_ref], local_commit)
            logger.info(f"Updated {remote_ref.decode('utf-8')} to {local_commit.decode('utf-8')}")

            return {
                "success": True,
                "error": None
            }

        except DivergedBranches as e:
            logger.warning(f"Branches have diverged: {e}")
            return {
                "success": False,
                "error": "Cannot push: your local branch has diverged from the remote. Pull the latest changes first, then try pushing again."
            }
        except Exception as e:
            logger.error(f"Failed to push: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to push: {str(e)}"
            }

    async def pull(self, context: Any) -> dict:
        """
        Pull changes from GitHub remote.

        Uses porcelain.merge_tree() to detect conflicts before attempting merge.

        Returns:
            dict with updated_files, conflicts, success status
        """
        repo = self.get_repo()

        # Check if we're already in a merge state
        from pathlib import Path
        merge_head_path = Path(repo.controldir()) / 'MERGE_HEAD'
        if merge_head_path.exists():
            # Already in a merge - check if there are still conflicts
            conflicts = await self.get_conflicts()
            if conflicts:
                # Still have conflicts - user must resolve them
                return {
                    "success": False,
                    "updated_files": [],
                    "conflicts": conflicts,
                    "error": "Repository has unresolved conflicts. Please resolve them and commit, or abort the merge."
                }
            else:
                # No conflicts remaining but merge not committed - clean up and allow pull
                logger.info("MERGE_HEAD exists but no conflicts - cleaning up incomplete merge state")
                merge_head_path.unlink()
                conflicts_file = Path(repo.controldir()) / 'BIFROST_CONFLICTS'
                if conflicts_file.exists():
                    conflicts_file.unlink()
                # Continue with normal pull
                logger.info("Cleaned up merge state, continuing with pull")

        try:
            # Get authenticated URL
            auth_url = await self._get_authenticated_remote_url(context)
            if not auth_url:
                raise Exception("No GitHub configuration found")

            # Fetch changes with authentication (this will update remote refs)
            result = porcelain.fetch(repo, remote_location=auth_url)

            # Update remote tracking branches manually
            for remote_ref, sha in result.refs.items():
                if remote_ref == b'HEAD':
                    continue
                if remote_ref.startswith(b'refs/heads/'):
                    branch_name = remote_ref[len(b'refs/heads/'):]
                    local_remote_ref = b'refs/remotes/origin/' + branch_name
                    repo.refs[local_remote_ref] = sha

            # Get current branch
            current_branch = self.get_current_branch() or 'main'
            local_ref = f'refs/heads/{current_branch}'.encode('utf-8')
            remote_ref = f'refs/remotes/origin/{current_branch}'.encode('utf-8')

            # Get current commit and remote commit
            local_commit = repo.refs[local_ref]
            remote_commit = repo.refs[remote_ref] if remote_ref in repo.refs else None

            if not remote_commit:
                raise Exception(f"Remote branch {current_branch} not found")

            # If already up to date, return success
            if local_commit == remote_commit:
                return {
                    "success": True,
                    "updated_files": [],
                    "conflicts": [],
                    "error": None
                }

            # Check for conflicts by comparing trees (don't write markers)
            from dulwich.merge import three_way_merge

            try:
                # Get commit objects
                local_commit_obj = repo[local_commit]
                remote_commit_obj = repo[remote_commit]

                # Find merge base
                merge_bases = porcelain.merge_base(repo, committishes=[local_commit, remote_commit])
                base_commit = repo[merge_bases[0]] if merge_bases else None

                logger.info(f"Checking for conflicts: base={base_commit.id.decode('utf-8')[:8] if base_commit else 'None'}, ours={local_commit.decode('utf-8')[:8]}, theirs={remote_commit.decode('utf-8')[:8]}")

                # Perform tree-level merge to detect conflicted paths (but don't write markers)
                merged_tree, conflicted_paths = three_way_merge(
                    repo.object_store,
                    base_commit=base_commit,
                    ours_commit=local_commit_obj,
                    theirs_commit=remote_commit_obj
                )

                logger.info(f"Conflict detection result: {len(conflicted_paths)} conflicted path(s)")

                # For each conflicted path, collect local and remote content without writing markers
                conflicts_list = []

                def get_object_for_path(commit_obj, path_b):
                    """Get tree or blob object for a path"""
                    if not commit_obj:
                        return None
                    tree_obj = repo[commit_obj.tree]
                    if not path_b:  # Root
                        return tree_obj
                    parts = path_b.split(b'/')
                    for part in parts:
                        mode, sha = tree_obj[part]
                        obj = repo[sha]
                        if hasattr(obj, 'items'):  # It's a tree
                            tree_obj = obj
                        else:  # It's a blob
                            return obj
                    return tree_obj

                def process_conflicted_tree(path_prefix, base_tree, ours_tree, theirs_tree):
                    """Recursively process a conflicted tree to find actual file conflicts"""
                    # Get all file names from all three trees
                    base_entries = {name: (mode, sha) for name, mode, sha in base_tree.items()} if base_tree else {}
                    ours_entries = {name: (mode, sha) for name, mode, sha in ours_tree.items()} if ours_tree else {}
                    theirs_entries = {name: (mode, sha) for name, mode, sha in theirs_tree.items()} if theirs_tree else {}

                    all_names = set(base_entries.keys()) | set(ours_entries.keys()) | set(theirs_entries.keys())

                    for name in all_names:
                        file_path_bytes = path_prefix + b'/' + name if path_prefix else name
                        file_path_str = file_path_bytes.decode('utf-8')

                        base_entry = base_entries.get(name)
                        ours_entry = ours_entries.get(name)
                        theirs_entry = theirs_entries.get(name)

                        # Check if all three point to same SHA (no conflict)
                        if base_entry and ours_entry and theirs_entry:
                            if base_entry[1] == ours_entry[1] == theirs_entry[1]:
                                continue  # No conflict

                        # Get objects
                        base_obj = repo[base_entry[1]] if base_entry else None
                        ours_obj = repo[ours_entry[1]] if ours_entry else None
                        theirs_obj = repo[theirs_entry[1]] if theirs_entry else None

                        # Check if any is a tree (directory)
                        is_tree = any(hasattr(obj, 'items') for obj in [base_obj, ours_obj, theirs_obj] if obj)

                        if is_tree:
                            # Recursively process subdirectory
                            process_conflicted_tree(
                                file_path_bytes,
                                base_obj if hasattr(base_obj, 'items') else None,
                                ours_obj if hasattr(ours_obj, 'items') else None,
                                theirs_obj if hasattr(theirs_obj, 'items') else None
                            )
                        else:
                            # It's a file conflict - just collect the content from both sides
                            try:
                                current_content = ours_obj.as_raw_string().decode('utf-8', errors='replace') if ours_obj else ""
                                incoming_content = theirs_obj.as_raw_string().decode('utf-8', errors='replace') if theirs_obj else ""
                                base_content = base_obj.as_raw_string().decode('utf-8', errors='replace') if base_obj else None

                                conflicts_list.append({
                                    "file_path": file_path_str,
                                    "current_content": current_content,
                                    "incoming_content": incoming_content,
                                    "base_content": base_content,
                                })
                                logger.info(f"Found conflict in: {file_path_str}")

                            except Exception as e:
                                logger.warning(f"Failed to read content for {file_path_str}: {e}")

                for path_bytes in conflicted_paths:
                    path_str = path_bytes.decode('utf-8') if isinstance(path_bytes, bytes) else path_bytes
                    logger.info(f"Processing conflicted path: {path_str}")

                    try:
                        base_obj = get_object_for_path(base_commit, path_bytes) if base_commit else None
                        ours_obj = get_object_for_path(local_commit_obj, path_bytes)
                        theirs_obj = get_object_for_path(remote_commit_obj, path_bytes)

                        # Check if it's a tree or blob
                        if any(hasattr(obj, 'items') for obj in [base_obj, ours_obj, theirs_obj] if obj):
                            # It's a tree - recursively process
                            process_conflicted_tree(
                                path_bytes,
                                base_obj if hasattr(base_obj, 'items') else None,
                                ours_obj if hasattr(ours_obj, 'items') else None,
                                theirs_obj if hasattr(theirs_obj, 'items') else None
                            )
                        else:
                            # It's a blob - collect content
                            current_content = ours_obj.as_raw_string().decode('utf-8', errors='replace') if ours_obj else ""
                            incoming_content = theirs_obj.as_raw_string().decode('utf-8', errors='replace') if theirs_obj else ""
                            base_content = base_obj.as_raw_string().decode('utf-8', errors='replace') if base_obj else None

                            conflicts_list.append({
                                "file_path": path_str,
                                "current_content": current_content,
                                "incoming_content": incoming_content,
                                "base_content": base_content,
                            })
                            logger.info(f"Found conflict in: {path_str}")

                    except Exception as e:
                        logger.warning(f"Failed to process {path_str}: {e}")

                # If we have conflicts, write merge state to Git and return
                if conflicts_list:
                    logger.warning(f"Pull detected {len(conflicts_list)} conflict(s) in files: {[c['file_path'] for c in conflicts_list]}")

                    # Write MERGE_HEAD to mark that we're in a merge state
                    from pathlib import Path
                    merge_head_path = Path(repo.controldir()) / 'MERGE_HEAD'
                    merge_head_path.write_text(remote_commit.decode('utf-8') + '\n')
                    logger.info(f"Wrote MERGE_HEAD: {remote_commit.decode('utf-8')[:8]}")

                    # Write conflicted files to index with multiple stages
                    # This makes Git recognize them as conflicts (like a real merge)
                    index = repo.open_index()
                    for conflict_path_str in [c['file_path'] for c in conflicts_list]:
                        conflict_path_b = conflict_path_str.encode('utf-8')

                        # Get the three versions from the trees
                        def get_blob_from_tree(tree_obj, path_b):
                            if not tree_obj:
                                return None
                            parts = path_b.split(b'/')
                            current_tree = tree_obj
                            for part in parts[:-1]:
                                try:
                                    mode, sha = current_tree[part]
                                    current_tree = repo[sha]
                                except (KeyError, TypeError):
                                    return None
                            try:
                                mode, sha = current_tree[parts[-1]]
                                return repo[sha]
                            except (KeyError, TypeError):
                                return None

                        base_blob = get_blob_from_tree(repo[base_commit.tree] if base_commit else None, conflict_path_b)
                        ours_blob = get_blob_from_tree(repo[local_commit_obj.tree], conflict_path_b)
                        theirs_blob = get_blob_from_tree(repo[remote_commit_obj.tree], conflict_path_b)

                        # Remove stage 0 entry if it exists
                        if conflict_path_b in index:
                            del index[conflict_path_b]

                        # Add stage 1 (base), stage 2 (ours), stage 3 (theirs)
                        from dulwich.index import IndexEntry
                        import time
                        import stat

                        for stage, blob in [(1, base_blob), (2, ours_blob), (3, theirs_blob)]:
                            if blob:
                                # Create index entry with stage number in flags
                                entry = IndexEntry(
                                    ctime=(int(time.time()), 0),
                                    mtime=(int(time.time()), 0),
                                    dev=0,
                                    ino=0,
                                    mode=stat.S_IFREG | 0o644,
                                    uid=0,
                                    gid=0,
                                    size=len(blob.data),
                                    sha=blob.id,
                                    flags=(stage << 12) | len(conflict_path_b),  # Stage in high bits
                                )
                                index[conflict_path_b] = entry

                    index.write()
                    logger.info(f"Wrote {len(conflicts_list)} conflicted files to index with stages")

                    # Save conflicts to file for UI display (full content)
                    import json
                    conflicts_file = Path(repo.controldir()) / 'BIFROST_CONFLICTS'
                    conflicts_file.write_text(json.dumps(conflicts_list))
                    logger.info(f"Saved {len(conflicts_list)} conflicts for UI")

                    return {
                        "success": False,
                        "updated_files": [],
                        "conflicts": conflicts_list,
                        "error": f"Merge conflicts in {len(conflicts_list)} file(s)"
                    }

                # Merge succeeded without conflicts
                return {
                    "success": True,
                    "updated_files": [],  # TODO: Track which files were merged
                    "conflicts": [],
                    "error": None
                }

            except Exception as merge_error:
                # Unexpected merge error
                error_msg = str(merge_error)
                logger.error(f"Merge failed with error: {error_msg}")
                raise

        except Exception as e:
            logger.error(f"Failed to pull from GitHub: {e}", exc_info=True)

            # Try to get conflicts even on error
            try:
                conflicts = await self.get_conflicts()
                if conflicts:
                    conflict_files = [c.file_path for c in conflicts]
                    return {
                        "success": False,
                        "updated_files": [],
                        "conflicts": [c.model_dump() for c in conflicts],
                        "error": f"Merge conflicts occurred: {', '.join(conflict_files)}"
                    }
            except Exception as conflict_err:
                logger.warning(f"Failed to check for conflicts after pull error: {conflict_err}")

            # Format error message properly
            error_msg = str(e)
            # Clean up bytes representation in error messages
            if "b'" in error_msg:
                import re
                error_msg = re.sub(r"b'([^']+)'", r'\1', error_msg)

            return {
                "success": False,
                "updated_files": [],
                "conflicts": [],
                "error": f"Failed to pull from GitHub: {error_msg}"
            }

    async def refresh_status(self, context: Any) -> dict:
        """
        Unified method that fetches from remote and returns complete Git status.
        This combines fetch + status + commit history into a single call.

        Returns:
            dict with complete refresh status (GitRefreshStatusResponse format)
        """
        try:
            # Check if Git repo is initialized
            initialized = self.is_git_repo()

            # Check if GitHub is configured (has authenticated remote URL)
            configured = False
            if initialized:
                try:
                    auth_url = await self._get_authenticated_remote_url(context)
                    configured = auth_url is not None
                except Exception:
                    configured = False

            # If not initialized or configured, return early
            if not initialized or not configured:
                return {
                    "success": True,
                    "initialized": initialized,
                    "configured": configured,
                    "current_branch": self.get_current_branch() if initialized else None,
                    "changed_files": [],
                    "conflicts": [],
                    "merging": False,
                    "commits_ahead": 0,
                    "commits_behind": 0,
                    "commit_history": [],
                    "last_synced": datetime.now(timezone.utc).isoformat(),
                    "error": None
                }

            # 1. Fetch from remote to update tracking refs
            await self.fetch_from_remote(context)

            # 2. Get current branch
            current_branch = self.get_current_branch()

            # 3. Get local changes and conflicts
            changed_files = await self.get_changed_files()
            conflicts = await self.get_conflicts()

            # 4. Check if in merge state
            from pathlib import Path
            repo = self.get_repo()
            merge_head_path = Path(repo.controldir()) / 'MERGE_HEAD'
            merging = merge_head_path.exists()

            # 5. Get ahead/behind counts
            ahead, behind = await self.get_commits_ahead_behind()

            # 6. Get commit history
            commit_history = await self.get_commit_history(limit=20)

            return {
                "success": True,
                "initialized": initialized,
                "configured": configured,
                "current_branch": current_branch,
                "changed_files": changed_files,
                "conflicts": conflicts,
                "merging": merging,
                "commits_ahead": ahead,
                "commits_behind": behind,
                "commit_history": commit_history,
                "last_synced": datetime.now(timezone.utc).isoformat(),
                "error": None
            }

        except Exception as e:
            logger.error(f"Failed to refresh status: {e}", exc_info=True)
            return {
                "success": False,
                "initialized": False,
                "configured": False,
                "current_branch": None,
                "changed_files": [],
                "conflicts": [],
                "merging": False,
                "commits_ahead": 0,
                "commits_behind": 0,
                "commit_history": [],
                "last_synced": datetime.now(timezone.utc).isoformat(),
                "error": f"Failed to refresh status: {str(e)}"
            }

    async def discard_unpushed_commits(self, context: Any = None) -> dict:
        """
        Discard all unpushed commits by resetting local branch to remote tracking ref.
        This is useful when local commits are causing issues or are no longer needed.

        Returns:
            dict with success status and list of discarded commits
        """
        repo = self.get_repo()

        try:
            # Fetch from remote first to ensure we have the latest refs
            if context:
                await self._fetch_from_remote(context)

            # Get current branch
            current_branch = self.get_current_branch() or 'main'
            local_ref = f'refs/heads/{current_branch}'.encode('utf-8')
            remote_ref = f'refs/remotes/origin/{current_branch}'.encode('utf-8')

            # Check if remote ref exists
            if remote_ref not in repo.refs:
                return {
                    "success": False,
                    "discarded_commits": [],
                    "new_head": None,
                    "error": "No remote tracking branch found. Cannot discard commits without a remote reference."
                }

            local_commit = repo.refs[local_ref]
            remote_commit = repo.refs[remote_ref]

            # Get list of commits that will be discarded (commits in local but not in remote)
            discarded_commits = []
            if local_commit != remote_commit:
                # Get commits that are ahead (these will be discarded)
                walker = repo.get_walker(include=[local_commit], exclude=[remote_commit])

                for entry in walker:
                    commit = entry.commit
                    discarded_commits.append({
                        "sha": commit.id.decode('utf-8') if isinstance(commit.id, bytes) else commit.id,
                        "message": commit.message.decode('utf-8').strip(),
                        "author": commit.author.decode('utf-8') if isinstance(commit.author, bytes) else commit.author,
                        "timestamp": datetime.fromtimestamp(commit.commit_time, tz=timezone.utc).isoformat(),
                        "is_pushed": False
                    })

                # Reset local branch to remote
                repo.refs[local_ref] = remote_commit

                # Hard reset working directory to match (need tree ID, not commit ID)
                remote_commit_obj = repo[remote_commit]
                repo.reset_index(remote_commit_obj.tree)

                logger.info(f"Discarded {len(discarded_commits)} unpushed commit(s) on {current_branch}")

            return {
                "success": True,
                "discarded_commits": discarded_commits,
                "new_head": remote_commit.decode('utf-8') if isinstance(remote_commit, bytes) else remote_commit,
                "error": None
            }

        except Exception as e:
            logger.error(f"Failed to discard unpushed commits: {e}", exc_info=True)
            return {
                "success": False,
                "discarded_commits": [],
                "new_head": None,
                "error": f"Failed to discard unpushed commits: {str(e)}"
            }

    async def discard_commit(self, commit_sha: str, context: Any = None) -> dict:
        """
        Discard a specific commit and all commits newer than it.
        This resets the branch to the parent of the specified commit.

        Args:
            commit_sha: SHA of the commit to discard
            context: Optional context for async operations like fetch

        Returns:
            dict with success status and list of discarded commits
        """
        repo = self.get_repo()

        try:
            # Fetch from remote first to ensure we have the latest refs
            if context:
                await self._fetch_from_remote(context)
            # Convert SHA to bytes if needed
            target_sha = commit_sha.encode('utf-8') if isinstance(commit_sha, str) else commit_sha

            # Verify the commit exists
            try:
                target_commit = repo[target_sha]
            except KeyError:
                return {
                    "success": False,
                    "discarded_commits": [],
                    "new_head": None,
                    "error": f"Commit {commit_sha} not found in repository"
                }

            # Get current branch
            current_branch = self.get_current_branch() or 'main'
            local_ref = f'refs/heads/{current_branch}'.encode('utf-8')
            current_commit = repo.refs[local_ref]

            # Get the parent of the target commit (this becomes the new HEAD)
            if not target_commit.parents:
                return {
                    "success": False,
                    "discarded_commits": [],
                    "new_head": None,
                    "error": "Cannot discard the initial commit (it has no parent)"
                }

            new_head = target_commit.parents[0]

            # Get list of commits that will be discarded
            discarded_commits = []
            walker = repo.get_walker(include=[current_commit], exclude=[new_head])

            for entry in walker:
                commit = entry.commit
                discarded_commits.append({
                    "sha": commit.id.decode('utf-8') if isinstance(commit.id, bytes) else commit.id,
                    "message": commit.message.decode('utf-8').strip(),
                    "author": commit.author.decode('utf-8') if isinstance(commit.author, bytes) else commit.author,
                    "timestamp": datetime.fromtimestamp(commit.commit_time, tz=timezone.utc).isoformat(),
                    "is_pushed": False
                })

            # Reset branch to parent of target commit
            repo.refs[local_ref] = new_head

            # Hard reset working directory to match (need tree ID, not commit ID)
            new_head_obj = repo[new_head]
            repo.reset_index(new_head_obj.tree)

            logger.info(f"Discarded {len(discarded_commits)} commit(s) on {current_branch}, reset to {new_head.decode('utf-8') if isinstance(new_head, bytes) else new_head}")

            return {
                "success": True,
                "discarded_commits": discarded_commits,
                "new_head": new_head.decode('utf-8') if isinstance(new_head, bytes) else new_head,
                "error": None
            }

        except Exception as e:
            logger.error(f"Failed to discard commit {commit_sha}: {e}", exc_info=True)
            return {
                "success": False,
                "discarded_commits": [],
                "new_head": None,
                "error": f"Failed to discard commit: {str(e)}"
            }

    async def resolve_conflict(
        self,
        file_path: str,
        resolution: Literal["current", "incoming", "both", "manual"],
        manual_content: str | None = None
    ) -> int:
        """
        Resolve a merge conflict in a file by removing conflict stages from index.

        The file content should already be written by the caller.
        This method removes the conflict stages (1/2/3) and adds stage 0.

        Args:
            file_path: Path to conflicted file (already resolved)
            resolution: Resolution strategy (for logging)
            manual_content: Not used (kept for API compatibility)

        Returns:
            Number of remaining conflicts
        """
        full_path = self.workspace_path / file_path

        if not full_path.exists():
            raise ValueError(f"File not found: {file_path}")

        # Remove conflict stages and stage the resolved file
        # We need to manually manipulate the index to ensure the file is staged
        # even if content matches HEAD (which porcelain.add might skip)
        repo = self.get_repo()
        index = repo.open_index()
        file_path_bytes = file_path.encode('utf-8')

        # Remove all stages for this file (0, 1, 2, 3)
        # The index can have multiple entries for the same path with different stages
        entries_to_remove = []
        for path_bytes, entry in index.items():
            if path_bytes == file_path_bytes:
                entries_to_remove.append(path_bytes)

        for path_bytes in entries_to_remove:
            del index[path_bytes]

        # Now add the resolved file at stage 0
        # Force add it by creating an index entry manually
        from dulwich.index import IndexEntry
        import stat

        # Read the resolved file content
        with open(full_path, 'rb') as f:
            file_content = f.read()

        # Create blob object
        from dulwich.objects import Blob
        blob = Blob.from_string(file_content)
        repo.object_store.add_object(blob)

        # Create index entry at stage 0
        file_stat = full_path.stat()
        entry = IndexEntry(
            ctime=(int(file_stat.st_ctime), 0),
            mtime=(int(file_stat.st_mtime), 0),
            dev=file_stat.st_dev,
            ino=file_stat.st_ino,
            mode=stat.S_IFREG | 0o644,
            uid=file_stat.st_uid,
            gid=file_stat.st_gid,
            size=len(file_content),
            sha=blob.id,
            flags=len(file_path_bytes),  # Stage 0 (no stage bits set)
        )
        index[file_path_bytes] = entry
        index.write()

        logger.info(f"Staged resolved file: {file_path} (resolution: {resolution})")

        # Check remaining conflicts
        remaining_conflicts = await self.get_conflicts()
        logger.info(f"Remaining conflicts after staging: {len(remaining_conflicts)}")

        return len(remaining_conflicts)

    async def abort_merge(self) -> dict:
        """
        Abort an in-progress merge and return to pre-merge state.

        This clears MERGE_HEAD and conflict markers, and resets the index.
        Similar to `git merge --abort`.

        Returns:
            dict with success status
        """
        repo = self.get_repo()

        from pathlib import Path
        merge_head_path = Path(repo.controldir()) / 'MERGE_HEAD'

        if not merge_head_path.exists():
            return {
                "success": False,
                "error": "No merge in progress"
            }

        try:
            # Delete MERGE_HEAD
            merge_head_path.unlink()
            logger.info("Deleted MERGE_HEAD")

            # Clear saved conflicts
            conflicts_file = Path(repo.controldir()) / 'BIFROST_CONFLICTS'
            if conflicts_file.exists():
                conflicts_file.unlink()
                logger.info("Cleared saved conflicts")

            # Reset index to HEAD (removes conflict stages)
            # This is equivalent to git reset --mixed HEAD
            index = repo.open_index()
            head_tree = repo[repo.head()].tree
            index.clear()

            # Rebuild index from HEAD tree
            for entry in repo.object_store.iter_tree_contents(head_tree):
                index[entry.path] = entry.in_entry

            index.write()
            logger.info("Reset index to HEAD")

            return {
                "success": True,
                "message": "Merge aborted successfully"
            }

        except Exception as e:
            logger.error(f"Failed to abort merge: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to abort merge: {str(e)}"
            }

    # GitHub API methods (these use PyGithub, not Git)
    def list_repositories(self, token: str) -> list[GitHubRepoInfo]:
        """List accessible GitHub repositories using token"""
        gh = Github(token)
        repos = []

        try:
            for repo in gh.get_user().get_repos():
                repos.append(GitHubRepoInfo(
                    name=repo.name,
                    full_name=repo.full_name,
                    description=repo.description,
                    url=repo.html_url,
                    private=repo.private
                ))
        except GithubException as e:
            raise ValueError(f"Failed to list repositories: {e.data.get('message', str(e))}")

        return repos

    def list_branches(self, token: str, repo_full_name: str) -> list[GitHubBranchInfo]:
        """List branches in a repository"""
        gh = Github(token)

        try:
            repo = gh.get_repo(repo_full_name)
            branches = []

            for branch in repo.get_branches():
                branches.append(GitHubBranchInfo(
                    name=branch.name,
                    protected=branch.protected,
                    commit_sha=branch.commit.sha
                ))

            return branches
        except GithubException as e:
            raise ValueError(f"Failed to list branches: {e.data.get('message', str(e))}")

    def create_repository(
        self,
        token: str,
        name: str,
        description: str | None = None,
        private: bool = True,
        organization: str | None = None
    ) -> dict:
        """Create a new GitHub repository"""
        gh = Github(token)

        try:
            if organization:
                org = gh.get_organization(organization)
                repo = org.create_repo(
                    name=name,
                    description=description or "",
                    private=private
                )
            else:
                repo = gh.get_user().create_repo(  # type: ignore[attr-defined]
                    name=name,
                    description=description or "",
                    private=private
                )

            return {
                "full_name": repo.full_name,
                "url": repo.html_url,
                "clone_url": repo.clone_url
            }
        except GithubException as e:
            raise ValueError(f"Failed to create repository: {e.data.get('message', str(e))}")

    async def analyze_workspace(
        self,
        token: str,
        repo_url: str,
        branch: str = "main"
    ) -> dict:
        """
        Analyze workspace to determine if configuration will require replacing files.
        Simplified for replace-only strategy.

        Returns:
            Dictionary with workspace analysis results
        """
        # Count files in workspace (excluding .git)
        file_count = 0
        if self.workspace_path.exists():
            for item in self.workspace_path.rglob("*"):
                if item.is_file() and ".git" not in item.parts:
                    file_count += 1

        # Check if it's already a Git repo
        is_git = self.is_git_repo()
        existing_remote = None

        if is_git:
            try:
                repo = self.get_repo()
                config = repo.get_config()
                remote_url = config.get((b'remote', b'origin'), b'url')
                if remote_url:
                    existing_remote = remote_url.decode('utf-8')
                    # Remove token from URL if present
                    if '@' in existing_remote:
                        existing_remote = existing_remote.split('@', 1)[1]
                        existing_remote = f"https://{existing_remote}"
            except Exception:
                pass

        # Determine workspace status
        if file_count == 0:
            workspace_status = "empty"
        elif not is_git:
            workspace_status = "has_files_no_git"
        elif existing_remote and existing_remote != repo_url:
            workspace_status = "is_different_git_repo"
        else:
            workspace_status = "is_git_repo"

        # Always requires confirmation if there are files
        requires_confirmation = file_count > 0

        return {
            "workspace_status": workspace_status,
            "file_count": file_count,
            "existing_remote": existing_remote,
            "requires_confirmation": requires_confirmation,
            "backup_will_be_created": file_count > 0
        }
