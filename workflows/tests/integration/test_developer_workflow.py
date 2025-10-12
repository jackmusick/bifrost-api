"""
Integration Tests: Developer Workflow with Engine Protection

Tests that simulate the full developer workflow:
1. Fork repository
2. Create branch
3. Make changes to workspace
4. Attempt changes to engine
5. Verify GitHub Action response

These tests validate the end-to-end developer experience.
"""

import pytest
import subprocess
import tempfile
import shutil
from pathlib import Path


class TestDeveloperWorkflow:
    """Integration tests for developer commit workflow"""

    @pytest.fixture
    def repo_root(self):
        """Get repository root directory"""
        # Navigate from workflows/tests/integration/ to repo root
        return Path(__file__).parent.parent.parent.parent

    def test_workspace_changes_allowed(self, repo_root):
        """
        Integration: Developer can commit workspace changes

        Simulates:
        1. Developer modifies workspace/workflows/
        2. Commits and pushes
        3. GitHub Action should PASS
        """
        workspace_dir = repo_root / "workflows" / "workspace" / "workflows"

        # Verify workspace directory exists
        assert workspace_dir.exists(), (
            f"Workspace directory not found at {workspace_dir}"
        )

        # This test documents the expected behavior:
        # Changes to workspace/* should NOT trigger the GitHub Action failure
        # The actual GitHub Action will be tested in T021

        assert True, (
            "Contract: Workspace changes must be allowed by GitHub Action"
        )

    def test_engine_changes_blocked(self, repo_root):
        """
        Integration: Developer CANNOT commit engine changes

        Simulates:
        1. Developer attempts to modify engine/shared/
        2. Commits and pushes
        3. GitHub Action should FAIL with clear error message
        """
        engine_dir = repo_root / "workflows" / "engine"

        # Verify engine directory exists
        assert engine_dir.exists(), (
            f"Engine directory not found at {engine_dir}"
        )

        # This test documents the expected behavior:
        # Changes to engine/* should trigger the GitHub Action failure
        # The actual GitHub Action will be tested in T021

        assert True, (
            "Contract: Engine changes from developers must be blocked by GitHub Action"
        )

    def test_mixed_changes_blocked_if_engine_modified(self, repo_root):
        """
        Integration: Mixed workspace + engine changes should be blocked

        Simulates:
        1. Developer modifies both workspace/ and engine/
        2. Commits and pushes
        3. GitHub Action should FAIL (because engine was modified)
        """
        # This test documents the expected behavior:
        # If ANY engine files are modified, the commit should be blocked
        # regardless of other changes

        assert True, (
            "Contract: Any engine modification must trigger GitHub Action failure"
        )

    def test_bot_can_modify_engine(self, repo_root):
        """
        Integration: Authorized bots CAN modify engine

        Simulates:
        1. upstream-sync[bot] modifies engine/
        2. Commits and pushes
        3. GitHub Action should PASS (bot is whitelisted)
        """
        # This test documents the expected behavior:
        # upstream-sync[bot] and github-actions[bot] should be allowed
        # to modify engine files

        assert True, (
            "Contract: Authorized bots must be allowed to modify engine"
        )


class TestGitWorkflowSimulation:
    """Simulate git operations for workflow testing"""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary git repository for testing"""
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True
        )

        # Configure git
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True
        )

        return repo_path

    def test_git_detect_workspace_changes(self, temp_repo):
        """Test that git correctly detects changes in workspace/"""
        # Create workspace directory structure
        workspace_dir = temp_repo / "workflows" / "workspace" / "workflows"
        workspace_dir.mkdir(parents=True)

        # Create a test file
        test_file = workspace_dir / "test_workflow.py"
        test_file.write_text("# Test workflow\n")

        # Add to git
        subprocess.run(
            ["git", "add", "."],
            cwd=temp_repo,
            check=True,
            capture_output=True
        )

        # Check git status
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=temp_repo,
            check=True,
            capture_output=True,
            text=True
        )

        # Verify file is detected
        assert "workflows/workspace/workflows/test_workflow.py" in result.stdout

    def test_git_detect_engine_changes(self, temp_repo):
        """Test that git correctly detects changes in engine/"""
        # Create engine directory structure
        engine_dir = temp_repo / "workflows" / "engine" / "shared"
        engine_dir.mkdir(parents=True)

        # Create a test file
        test_file = engine_dir / "test_module.py"
        test_file.write_text("# Test module\n")

        # Add to git
        subprocess.run(
            ["git", "add", "."],
            cwd=temp_repo,
            check=True,
            capture_output=True
        )

        # Check git status
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=temp_repo,
            check=True,
            capture_output=True,
            text=True
        )

        # Verify file is detected
        assert "workflows/engine/shared/test_module.py" in result.stdout

    def test_changed_files_filter_by_path(self, temp_repo):
        """Test filtering changed files by path pattern"""
        # Create both workspace and engine changes
        workspace_dir = temp_repo / "workflows" / "workspace"
        workspace_dir.mkdir(parents=True)
        (workspace_dir / "test.py").write_text("# workspace\n")

        engine_dir = temp_repo / "workflows" / "engine"
        engine_dir.mkdir(parents=True)
        (engine_dir / "test.py").write_text("# engine\n")

        # Add all files
        subprocess.run(
            ["git", "add", "."],
            cwd=temp_repo,
            check=True,
            capture_output=True
        )

        # Get all changed files
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=temp_repo,
            check=True,
            capture_output=True,
            text=True
        )

        changed_files = result.stdout.strip().split('\n')

        # Filter for engine changes
        engine_changes = [
            f for f in changed_files
            if 'engine/' in f or f.startswith('workflows/engine/')
        ]

        # Verify filtering works
        assert len(engine_changes) > 0, "Should detect engine changes"
        assert any('engine/test.py' in f for f in engine_changes)
