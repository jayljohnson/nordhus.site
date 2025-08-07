#!/usr/bin/env python3
"""
Unit tests for Git Operations utility module.
Tests centralized git operations for construction project workflows.
"""

import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from scripts.utils.git_operations import GitOperations


# Network isolation - prevent any live API calls during testing
def _mock_socket(*args, **kwargs):
    raise RuntimeError("Network calls are not allowed in tests. Mock your networking!")


def _fail_on_git_remote_calls(cmd, *args, **kwargs):
    """Fail if git commands that could make network calls are used without proper mocking"""
    if isinstance(cmd, list) and len(cmd) >= 2 and cmd[0] == "git":
        remote_commands = ["fetch", "pull", "push", "ls-remote", "clone"]
        if any(remote_cmd in cmd for remote_cmd in remote_commands):
            raise RuntimeError(f"Git remote command '{' '.join(cmd)}' detected! Mock subprocess.run properly.")
    # Allow other subprocess calls to proceed normally in tests
    return subprocess.run.__wrapped__(cmd, *args, **kwargs)


# Patch networking to prevent accidental live calls
socket.socket = _mock_socket

# Store original subprocess.run and patch it to catch unmocked git remote calls
if not hasattr(subprocess.run, "__wrapped__"):
    subprocess.run.__wrapped__ = subprocess.run
    subprocess.run = _fail_on_git_remote_calls


class TestEnsureGitConfig(unittest.TestCase):
    """Test git configuration setup"""

    @patch("subprocess.run")
    def test_ensure_git_config_success(self, mock_subprocess):
        """Test successful git config setup"""
        mock_subprocess.return_value = Mock(returncode=0)

        GitOperations.ensure_git_config()

        expected_calls = [
            call(["git", "config", "user.name", "Construction Bot"], check=True),
            call(["git", "config", "user.email", "noreply@nordhus.site"], check=True),
        ]
        mock_subprocess.assert_has_calls(expected_calls)

    @patch("subprocess.run")
    @patch("scripts.utils.git_operations.logger")
    def test_ensure_git_config_failure(self, mock_logger, mock_subprocess):
        """Test git config setup with failure"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git config")

        GitOperations.ensure_git_config()

        mock_logger.warning.assert_called_with("Could not set git config: Command 'git config' returned non-zero exit status 1.")


class TestBranchExistence(unittest.TestCase):
    """Test branch existence checking functions"""

    @patch("subprocess.run")
    def test_branch_exists_locally_true(self, mock_subprocess):
        """Test local branch exists"""
        mock_result = Mock()
        mock_result.stdout = "  feature-branch\n  main\n"
        mock_subprocess.return_value = mock_result

        result = GitOperations.branch_exists_locally("feature-branch")

        self.assertTrue(result)
        mock_subprocess.assert_called_once_with(["git", "branch", "--list", "feature-branch"], check=False, capture_output=True, text=True)

    @patch("subprocess.run")
    def test_branch_exists_locally_false(self, mock_subprocess):
        """Test local branch does not exist"""
        mock_result = Mock()
        mock_result.stdout = "  main\n  other-branch\n"
        mock_subprocess.return_value = mock_result

        result = GitOperations.branch_exists_locally("feature-branch")

        self.assertFalse(result)

    @patch("subprocess.run")
    def test_branch_exists_locally_exception(self, mock_subprocess):
        """Test local branch check with exception"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git branch")

        result = GitOperations.branch_exists_locally("feature-branch")

        self.assertFalse(result)

    @patch("subprocess.run")
    def test_branch_exists_remotely_true(self, mock_subprocess):
        """Test remote branch exists"""
        mock_result = Mock()
        mock_result.stdout = "abc123def456\trefs/heads/feature-branch\n"
        mock_subprocess.return_value = mock_result

        result = GitOperations.branch_exists_remotely("feature-branch")

        self.assertTrue(result)
        mock_subprocess.assert_called_once_with(
            ["git", "ls-remote", "--heads", "origin", "feature-branch"], check=False, capture_output=True, text=True
        )

    @patch("subprocess.run")
    def test_branch_exists_remotely_false(self, mock_subprocess):
        """Test remote branch does not exist"""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        result = GitOperations.branch_exists_remotely("feature-branch")

        self.assertFalse(result)

    @patch("subprocess.run")
    def test_branch_exists_remotely_exception(self, mock_subprocess):
        """Test remote branch check with exception"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git ls-remote")

        result = GitOperations.branch_exists_remotely("feature-branch")

        self.assertFalse(result)


class TestBranchOperations(unittest.TestCase):
    """Test branch creation and switching operations"""

    @patch("subprocess.run")
    @patch("scripts.utils.git_operations.logger")
    def test_checkout_branch_success(self, mock_logger, mock_subprocess):
        """Test successful branch checkout"""
        mock_subprocess.return_value = Mock(returncode=0)

        result = GitOperations.checkout_branch("feature-branch")

        self.assertTrue(result)
        mock_subprocess.assert_called_once_with(["git", "checkout", "feature-branch"], check=True)
        mock_logger.info.assert_called_once_with("Switched to existing branch: feature-branch")

    @patch("subprocess.run")
    @patch("scripts.utils.git_operations.logger")
    def test_checkout_branch_failure(self, mock_logger, mock_subprocess):
        """Test failed branch checkout"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git checkout")

        result = GitOperations.checkout_branch("feature-branch")

        self.assertFalse(result)
        mock_logger.error.assert_called_with("Error switching to branch feature-branch: Command 'git checkout' returned non-zero exit status 1.")

    @patch("subprocess.run")
    @patch("scripts.utils.git_operations.logger")
    def test_fetch_and_checkout_remote_branch_success(self, mock_logger, mock_subprocess):
        """Test successful remote branch fetch and checkout"""
        mock_subprocess.return_value = Mock(returncode=0)

        result = GitOperations.fetch_and_checkout_remote_branch("feature-branch")

        self.assertTrue(result)
        expected_calls = [
            call(["git", "fetch", "origin", "feature-branch"], check=True),
            call(["git", "checkout", "-b", "feature-branch", "origin/feature-branch"], check=True),
        ]
        mock_subprocess.assert_has_calls(expected_calls)
        mock_logger.info.assert_called_once_with("Checked out remote branch: feature-branch")

    @patch("subprocess.run")
    @patch("scripts.utils.git_operations.logger")
    def test_fetch_and_checkout_remote_branch_failure(self, mock_logger, mock_subprocess):
        """Test failed remote branch fetch and checkout"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git fetch")

        result = GitOperations.fetch_and_checkout_remote_branch("feature-branch")

        self.assertFalse(result)
        mock_logger.error.assert_called_with("Error checking out remote branch feature-branch: Command 'git fetch' returned non-zero exit status 1.")


class TestMainBranchOperations(unittest.TestCase):
    """Test main branch operations"""

    @patch("subprocess.run")
    def test_ensure_main_branch_local_exists(self, mock_subprocess):
        """Test ensure main branch when it exists locally"""
        mock_subprocess.return_value = Mock(returncode=0)

        GitOperations.ensure_main_branch()

        expected_calls = [call(["git", "checkout", "main"], check=True), call(["git", "pull", "origin", "main"], check=True)]
        mock_subprocess.assert_has_calls(expected_calls)

    @patch("subprocess.run")
    def test_ensure_main_branch_local_missing(self, mock_subprocess):
        """Test ensure main branch when it doesn't exist locally"""

        def side_effect(cmd, check=False):
            if cmd == ["git", "checkout", "main"]:
                raise subprocess.CalledProcessError(1, "git checkout")
            return Mock(returncode=0)

        mock_subprocess.side_effect = side_effect

        GitOperations.ensure_main_branch()

        expected_calls = [
            call(["git", "checkout", "main"], check=True),
            call(["git", "fetch", "origin", "main"], check=True),
            call(["git", "checkout", "-b", "main", "origin/main"], check=True),
            call(["git", "pull", "origin", "main"], check=True),
        ]
        mock_subprocess.assert_has_calls(expected_calls)

    @patch("subprocess.run")
    @patch("scripts.utils.git_operations.GitOperations.ensure_main_branch")
    def test_create_branch_from_main_success(self, mock_ensure_main, mock_subprocess):
        """Test successful branch creation from main"""
        mock_ensure_main.return_value = None
        mock_subprocess.return_value = Mock(returncode=0)

        result = GitOperations.create_branch_from_main("feature-branch")

        self.assertTrue(result)
        mock_ensure_main.assert_called_once()
        mock_subprocess.assert_called_once_with(["git", "checkout", "-b", "feature-branch"], check=True)

    @patch("subprocess.run")
    @patch("scripts.utils.git_operations.GitOperations.ensure_main_branch")
    def test_create_branch_from_main_failure(self, mock_ensure_main, mock_subprocess):
        """Test failed branch creation from main"""
        mock_ensure_main.return_value = None
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git checkout")

        result = GitOperations.create_branch_from_main("feature-branch")

        self.assertFalse(result)


class TestCreateOrSwitchBranch(unittest.TestCase):
    """Test comprehensive branch creation/switching logic"""

    @patch("scripts.utils.git_operations.GitOperations.branch_exists_locally")
    @patch("scripts.utils.git_operations.GitOperations.checkout_branch")
    def test_create_or_switch_branch_local_exists(self, mock_checkout, mock_local_exists):
        """Test switching to existing local branch"""
        mock_local_exists.return_value = True
        mock_checkout.return_value = True

        result = GitOperations.create_or_switch_branch("feature-branch")

        self.assertTrue(result)
        mock_local_exists.assert_called_once_with("feature-branch")
        mock_checkout.assert_called_once_with("feature-branch")

    @patch("scripts.utils.git_operations.GitOperations.branch_exists_locally")
    @patch("scripts.utils.git_operations.GitOperations.branch_exists_remotely")
    @patch("scripts.utils.git_operations.GitOperations.fetch_and_checkout_remote_branch")
    def test_create_or_switch_branch_remote_exists(self, mock_fetch_checkout, mock_remote_exists, mock_local_exists):
        """Test checking out existing remote branch"""
        mock_local_exists.return_value = False
        mock_remote_exists.return_value = True
        mock_fetch_checkout.return_value = True

        result = GitOperations.create_or_switch_branch("feature-branch")

        self.assertTrue(result)
        mock_local_exists.assert_called_once_with("feature-branch")
        mock_remote_exists.assert_called_once_with("feature-branch")
        mock_fetch_checkout.assert_called_once_with("feature-branch")

    @patch("scripts.utils.git_operations.GitOperations.branch_exists_locally")
    @patch("scripts.utils.git_operations.GitOperations.branch_exists_remotely")
    @patch("scripts.utils.git_operations.GitOperations.create_branch_from_main")
    def test_create_or_switch_branch_create_new(self, mock_create_from_main, mock_remote_exists, mock_local_exists):
        """Test creating new branch"""
        mock_local_exists.return_value = False
        mock_remote_exists.return_value = False
        mock_create_from_main.return_value = True

        result = GitOperations.create_or_switch_branch("feature-branch")

        self.assertTrue(result)
        mock_local_exists.assert_called_once_with("feature-branch")
        mock_remote_exists.assert_called_once_with("feature-branch")
        mock_create_from_main.assert_called_once_with("feature-branch")

    @patch("scripts.utils.git_operations.GitOperations.branch_exists_locally")
    @patch("scripts.utils.git_operations.GitOperations.branch_exists_remotely")
    @patch("scripts.utils.git_operations.GitOperations.create_branch_from_main")
    def test_create_or_switch_branch_exception(self, mock_create_from_main, mock_remote_exists, mock_local_exists):
        """Test branch operations with exception"""
        mock_local_exists.side_effect = subprocess.CalledProcessError(1, "git")

        result = GitOperations.create_or_switch_branch("feature-branch")

        self.assertFalse(result)


class TestCommitOperations(unittest.TestCase):
    """Test git commit operations"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test environment"""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("subprocess.run")
    @patch("scripts.utils.git_operations.GitOperations.ensure_git_config")
    def test_commit_changes_success(self, mock_ensure_config, mock_subprocess):
        """Test successful commit of changes"""
        mock_subprocess.return_value = Mock(returncode=0)

        result = GitOperations.commit_changes(self.temp_path, "Test commit message")

        self.assertTrue(result)
        mock_ensure_config.assert_called_once()
        expected_calls = [call(["git", "add", str(self.temp_path)], check=True), call(["git", "commit", "-m", "Test commit message"], check=True)]
        mock_subprocess.assert_has_calls(expected_calls)

    @patch("subprocess.run")
    def test_commit_changes_no_config(self, mock_subprocess):
        """Test commit without ensuring config"""
        mock_subprocess.return_value = Mock(returncode=0)

        result = GitOperations.commit_changes(self.temp_path, "Test commit", ensure_config=False)

        self.assertTrue(result)
        expected_calls = [call(["git", "add", str(self.temp_path)], check=True), call(["git", "commit", "-m", "Test commit"], check=True)]
        mock_subprocess.assert_has_calls(expected_calls)

    @patch("subprocess.run")
    @patch("scripts.utils.git_operations.GitOperations.ensure_git_config")
    def test_commit_changes_failure(self, mock_ensure_config, mock_subprocess):
        """Test commit failure raises exception"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git add")

        with self.assertRaises(subprocess.CalledProcessError):
            GitOperations.commit_changes(self.temp_path, "Test commit message")

    @patch("subprocess.run")
    @patch("scripts.utils.git_operations.GitOperations.ensure_git_config")
    def test_add_and_commit_files_success(self, mock_ensure_config, mock_subprocess):
        """Test successful file addition and commit"""
        mock_subprocess.return_value = Mock(returncode=0)
        files = [Path("file1.txt"), Path("file2.txt")]

        result = GitOperations.add_and_commit_files(files, "Test commit message")

        self.assertTrue(result)
        mock_ensure_config.assert_called_once()
        expected_calls = [
            call(["git", "add", "file1.txt", "file2.txt"], check=True),
            call(["git", "commit", "-m", "Test commit message"], check=True),
        ]
        mock_subprocess.assert_has_calls(expected_calls)

    @patch("subprocess.run")
    def test_add_and_commit_files_failure(self, mock_subprocess):
        """Test failed file addition and commit"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git add")
        files = [Path("file1.txt")]

        result = GitOperations.add_and_commit_files(files, "Test commit", ensure_config=False)

        self.assertFalse(result)


class TestProjectBranchGeneration(unittest.TestCase):
    """Test project branch name generation"""

    def test_get_project_branch_with_date_prefix(self):
        """Test branch name generation with provided date prefix"""
        result = GitOperations.get_project_branch("test-project", "2025-08-07")

        self.assertEqual(result, "project/2025-08-07-test-project")

    def test_get_project_branch_without_date_prefix(self):
        """Test branch name generation with current date"""

        result = GitOperations.get_project_branch("test-project")

        # Check that result matches the expected pattern with current date
        pattern = r"^project/\d{4}-\d{2}-\d{2}-test-project$"
        self.assertRegex(result, pattern)
        self.assertIn("test-project", result)


class TestIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios combining multiple operations"""

    @patch("scripts.utils.git_operations.GitOperations.branch_exists_locally")
    @patch("scripts.utils.git_operations.GitOperations.checkout_branch")
    @patch("scripts.utils.git_operations.GitOperations.ensure_git_config")
    @patch("subprocess.run")
    def test_typical_project_workflow(self, mock_subprocess, mock_ensure_config, mock_checkout, mock_local_exists):
        """Test typical project workflow: switch to branch and commit"""
        mock_local_exists.return_value = True
        mock_checkout.return_value = True
        mock_subprocess.return_value = Mock(returncode=0)

        # Switch to project branch
        branch_result = GitOperations.create_or_switch_branch("project/2025-08-07-test-project")

        # Commit changes
        commit_result = GitOperations.commit_changes(Path("assets/images"), "Add new project photos")

        self.assertTrue(branch_result)
        self.assertTrue(commit_result)
        mock_local_exists.assert_called_once_with("project/2025-08-07-test-project")
        mock_checkout.assert_called_once_with("project/2025-08-07-test-project")
        mock_ensure_config.assert_called_once()

    @patch("scripts.utils.git_operations.GitOperations.branch_exists_locally")
    @patch("scripts.utils.git_operations.GitOperations.branch_exists_remotely")
    @patch("scripts.utils.git_operations.GitOperations.create_branch_from_main")
    def test_new_project_branch_creation(self, mock_create_from_main, mock_remote_exists, mock_local_exists):
        """Test creating new project branch when none exists"""
        mock_local_exists.return_value = False
        mock_remote_exists.return_value = False
        mock_create_from_main.return_value = True

        result = GitOperations.create_or_switch_branch("project/2025-08-07-new-project")

        self.assertTrue(result)
        mock_local_exists.assert_called_once_with("project/2025-08-07-new-project")
        mock_remote_exists.assert_called_once_with("project/2025-08-07-new-project")
        mock_create_from_main.assert_called_once_with("project/2025-08-07-new-project")


if __name__ == "__main__":
    unittest.main()
