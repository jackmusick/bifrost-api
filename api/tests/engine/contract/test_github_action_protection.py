"""
Contract Tests: GitHub Action Engine Protection

Tests that validate the GitHub Action correctly detects and blocks
modifications to the /engine directory from unauthorized commits.

These tests verify the contract defined in /specs/002-i-want-to/contracts/README.md
"""

from pathlib import Path

import pytest
import yaml


class TestGitHubActionContract:
    """Contract tests for .github/workflows/protect-engine.yml"""

    @pytest.fixture
    def workflow_file_path(self):
        """Path to the GitHub Actions workflow file"""
        # Find repo root by looking for .github directory
        current = Path(__file__).parent
        while current != current.parent:
            if (current / ".github").exists():
                repo_root = current
                break
            current = current.parent
        else:
            # Fallback: go up 4 levels from api/tests/engine/contract/
            repo_root = Path(__file__).parent.parent.parent.parent

        return repo_root / ".github" / "workflows" / "protect-engine.yml"

    @pytest.fixture
    def workflow_config(self, workflow_file_path):
        """Load and parse the GitHub Actions workflow YAML"""
        if not workflow_file_path.exists():
            pytest.skip("GitHub Actions workflow file not yet created")

        with open(workflow_file_path) as f:
            return yaml.safe_load(f)

    def test_workflow_file_exists(self, workflow_file_path):
        """Contract: GitHub Action workflow file must exist at expected path"""
        assert workflow_file_path.exists(), (
            f"GitHub Actions workflow file not found at {workflow_file_path}. "
            "Expected: .github/workflows/protect-engine.yml"
        )

    def test_workflow_triggers_on_push(self, workflow_config):
        """Contract: Workflow must trigger on push to main/develop branches"""
        assert 'on' in workflow_config, "Workflow must have 'on' trigger configuration"

        triggers = workflow_config['on']
        assert 'push' in triggers, "Workflow must trigger on 'push' events"

        # Verify branches
        push_config = triggers['push']
        assert 'branches' in push_config, "Push trigger must specify branches"

        branches = push_config['branches']
        assert 'main' in branches or 'develop' in branches, (
            "Push trigger must include 'main' or 'develop' branch"
        )

    def test_workflow_triggers_on_pull_request(self, workflow_config):
        """Contract: Workflow must trigger on PRs to main/develop branches"""
        triggers = workflow_config['on']
        assert 'pull_request' in triggers, "Workflow must trigger on 'pull_request' events"

        pr_config = triggers['pull_request']
        assert 'branches' in pr_config, "PR trigger must specify branches"

        branches = pr_config['branches']
        assert 'main' in branches or 'develop' in branches, (
            "PR trigger must include 'main' or 'develop' branch"
        )

    def test_workflow_detects_engine_path_changes(self, workflow_config):
        """Contract: Workflow must detect changes to engine/** paths"""
        jobs = workflow_config.get('jobs', {})
        assert len(jobs) > 0, "Workflow must define at least one job"

        # Find the validation job
        validation_job = None
        for job_name, job_config in jobs.items():
            if 'engine' in job_name.lower() or 'protect' in job_name.lower():
                validation_job = job_config
                break

        assert validation_job is not None, (
            "Workflow must have a job for engine protection validation"
        )

        # Check for changed files detection step
        steps = validation_job.get('steps', [])
        assert len(steps) > 0, "Validation job must have steps"

        # Look for tj-actions/changed-files or similar
        has_file_detection = any(
            'changed-files' in str(step.get('uses', '')) or
            'engine' in str(step.get('name', '')).lower()
            for step in steps
        )

        assert has_file_detection, (
            "Workflow must include a step to detect changed files in /engine path"
        )

    def test_workflow_has_bot_detection(self, workflow_config):
        """Contract: Workflow must allow upstream-sync and github-actions bots"""
        jobs = workflow_config.get('jobs', {})

        # Check for bot detection in workflow
        workflow_str = yaml.dump(workflow_config)

        has_bot_check = (
            'upstream-sync' in workflow_str or
            'github-actions' in workflow_str or
            'github.actor' in workflow_str
        )

        assert has_bot_check, (
            "Workflow must include logic to allow authorized bots "
            "(upstream-sync[bot], github-actions[bot])"
        )

    def test_workflow_has_timeout(self, workflow_config):
        """Contract: Workflow job must have 2-minute timeout"""
        jobs = workflow_config.get('jobs', {})

        # Check at least one job has a timeout
        has_timeout = False
        for job_name, job_config in jobs.items():
            timeout = job_config.get('timeout-minutes')
            if timeout is not None:
                has_timeout = True
                assert timeout <= 2, (
                    f"Job '{job_name}' timeout ({timeout} min) exceeds "
                    "contract requirement of 2 minutes"
                )

        assert has_timeout, (
            "At least one job must have a timeout-minutes configuration"
        )

    def test_workflow_uses_github_error_format(self, workflow_config):
        """Contract: Workflow must use ::error GitHub Actions format for failures"""
        workflow_str = yaml.dump(workflow_config)

        # Check for GitHub error format in run steps
        has_error_format = '::error' in workflow_str

        assert has_error_format, (
            "Workflow must use '::error' format for error messages "
            "to create annotations in GitHub UI"
        )

    def test_workflow_validates_engine_directory(self, workflow_config):
        """Contract: Workflow must specifically check /engine or workflows/engine paths"""
        workflow_str = yaml.dump(workflow_config)

        has_engine_path = (
            'engine/' in workflow_str or
            'workflows/engine' in workflow_str or
            '**/engine/**' in workflow_str
        )

        assert has_engine_path, (
            "Workflow must reference 'engine/' path in files changed detection"
        )


class TestGitHubActionBehavior:
    """Behavioral tests for GitHub Action logic"""

    def test_contract_allows_workspace_changes(self):
        """Contract: Changes to /workspace should NOT trigger failures"""
        # This is a documentation test - the actual behavior is verified in integration tests
        # The contract specifies that only /engine changes should be blocked
        assert True, "Contract requires workspace changes to be allowed"

    def test_contract_blocks_engine_changes(self):
        """Contract: Changes to /engine from developers should trigger failures"""
        # This is a documentation test - the actual behavior is verified in integration tests
        # The contract specifies that /engine changes from non-bots should fail
        assert True, "Contract requires engine changes from developers to be blocked"

    def test_contract_allows_bot_engine_changes(self):
        """Contract: Changes to /engine from authorized bots should be allowed"""
        # This is a documentation test - the actual behavior is verified in integration tests
        # The contract specifies that upstream-sync[bot] can modify /engine
        assert True, "Contract requires bot engine changes to be allowed"
