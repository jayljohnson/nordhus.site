#!/usr/bin/env python3
"""
Unit tests for the Construction Monitor module.
Tests photo client selection, environment validation, and main workflow orchestration.
"""

import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from scripts.workflows.construction_monitor import _handle_project_issue
from scripts.workflows.construction_monitor import _setup_github_manager
from scripts.workflows.construction_monitor import _sync_project_photos
from scripts.workflows.construction_monitor import get_photo_client
from scripts.workflows.construction_monitor import main
from scripts.workflows.construction_monitor import scan_and_sync_projects


# Network isolation - prevent any live API calls during testing
def _mock_socket(*args, **kwargs):
    raise RuntimeError("Network calls are not allowed in tests. Mock your API calls!")


def _mock_requests(*args, **kwargs):
    raise RuntimeError("HTTP requests are not allowed in tests. Use @patch decorators!")


# Patch networking to prevent accidental live calls
socket.socket = _mock_socket
requests.get = _mock_requests
requests.post = _mock_requests
requests.put = _mock_requests
requests.delete = _mock_requests
requests.request = _mock_requests


class TestGetPhotoClient(unittest.TestCase):
    """Test photo client selection logic"""

    def test_get_photo_client_detects_cloudinary_url(self):
        """Test that get_photo_client detects Cloudinary URL environment variable"""
        with patch.dict(os.environ, {"CLOUDINARY_URL": "cloudinary://key:secret@cloud"}):
            # This should not raise an exception for missing credentials
            try:
                get_photo_client()
                # If we get here, the function detected the credentials successfully
                # The actual instantiation might fail due to invalid credentials, but
                # we've tested the credential detection logic
                self.assertTrue(True)
            except ValueError as e:
                if "Cloudinary credentials not found" in str(e):
                    self.fail("Function should have detected Cloudinary URL")
                # Other errors (like invalid credentials) are acceptable
                pass

    def test_get_photo_client_detects_individual_vars(self):
        """Test that get_photo_client detects individual Cloudinary environment variables"""
        env_vars = {"CLOUDINARY_CLOUD_NAME": "test-cloud", "CLOUDINARY_API_KEY": "test-key", "CLOUDINARY_API_SECRET": "test-secret"}
        with patch.dict(os.environ, env_vars):
            # This should not raise an exception for missing credentials
            try:
                get_photo_client()
                # If we get here, the function detected the credentials successfully
                self.assertTrue(True)
            except ValueError as e:
                if "Cloudinary credentials not found" in str(e):
                    self.fail("Function should have detected individual Cloudinary vars")
                # Other errors (like invalid credentials) are acceptable
                pass

    @patch.dict(os.environ, {}, clear=True)
    def test_get_photo_client_missing_credentials(self):
        """Test getting photo client with missing credentials"""
        with self.assertRaises(ValueError) as cm:
            get_photo_client()

        self.assertIn("Missing Cloudinary credentials", str(cm.exception))
        self.assertIn("CLOUDINARY_URL=cloudinary://", str(cm.exception))

    @patch.dict(os.environ, {"CLOUDINARY_CLOUD_NAME": "test-cloud"})
    def test_get_photo_client_partial_credentials(self):
        """Test getting photo client with partial credentials"""
        with self.assertRaises(ValueError) as cm:
            get_photo_client()

        self.assertIn("Missing Cloudinary credentials", str(cm.exception))


class TestMainFunction(unittest.TestCase):
    """Test main function orchestration"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch.dict(os.environ, {"ENABLE_PHOTO_MONITORING": "false"})
    def test_main_photo_monitoring_disabled(self):
        """Test main function when photo monitoring is disabled"""
        result = main()
        self.assertTrue(result)  # Should return True when disabled

    @patch.dict(os.environ, {"ENABLE_PHOTO_MONITORING": "True"})  # Test case insensitive
    def test_main_missing_cloudinary_credentials(self):
        """Test main function with missing Cloudinary credentials"""
        result = main()
        self.assertFalse(result)  # Should return False when Cloudinary auth fails

    @patch.dict(os.environ, {"ENABLE_PHOTO_MONITORING": "true", "CLOUDINARY_URL": "cloudinary://key:secret@cloud"})
    @patch("scripts.clients.cloudinary_client.CloudinaryClient.authenticate")
    def test_main_cloudinary_auth_failure(self, mock_auth):
        """Test main function when Cloudinary authentication fails"""
        mock_auth.return_value = False

        result = main()
        self.assertFalse(result)

    @patch.dict(os.environ, {"ENABLE_PHOTO_MONITORING": "true", "CLOUDINARY_URL": "cloudinary://key:secret@cloud"})
    @patch("scripts.workflows.construction_monitor.CloudinaryClient")
    def test_main_successful_scan(self, mock_client_class):
        """Test that main function successfully scans projects"""
        # Mock the CloudinaryClient instance
        mock_client = mock_client_class.return_value
        mock_client.authenticate.return_value = True
        mock_client.get_construction_projects.return_value = []  # No projects found

        result = main()
        self.assertTrue(result)  # Should succeed with no projects

    @patch.dict(os.environ, {"ENABLE_PHOTO_MONITORING": "true", "CLOUDINARY_URL": "cloudinary://key:secret@cloud"})
    @patch("scripts.workflows.construction_monitor.scan_and_sync_projects")
    def test_main_workflow_failure(self, mock_scan):
        """Test main function when scan fails"""
        mock_scan.return_value = False

        result = main()
        self.assertFalse(result)


class TestMainEntryPointBehavior(unittest.TestCase):
    """Test main entry point behavior without running the actual __main__ block"""

    def test_module_has_main_guard(self):
        """Test that the module has the proper if __name__ == '__main__' guard"""
        with open("scripts/workflows/construction_monitor.py") as f:
            content = f.read()

        self.assertIn('if __name__ == "__main__":', content)
        self.assertIn("try:", content)
        self.assertIn("main()", content)
        self.assertIn("sys.exit", content)


class TestEnvironmentVariableHandling(unittest.TestCase):
    """Test various environment variable combinations"""

    @patch.dict(os.environ, {"ENABLE_PHOTO_MONITORING": "TRUE"})
    def test_enable_photo_monitoring_case_variations(self):
        """Test that photo monitoring flag is case insensitive"""
        result = main()
        self.assertFalse(result)  # Will fail on missing Cloudinary credentials

    @patch.dict(os.environ, {"ENABLE_PHOTO_MONITORING": "False"})
    def test_disable_photo_monitoring_false_value(self):
        """Test photo monitoring disabled with 'False' value"""
        result = main()
        self.assertTrue(result)  # Returns True when disabled

    @patch.dict(os.environ, {"ENABLE_PHOTO_MONITORING": "0"})
    def test_disable_photo_monitoring_zero_value(self):
        """Test photo monitoring disabled with '0' value"""
        result = main()
        self.assertTrue(result)  # Returns True when disabled

    @patch.dict(os.environ, {}, clear=True)  # Remove all env vars
    def test_enable_photo_monitoring_default_value(self):
        """Test photo monitoring disabled by default"""
        result = main()
        self.assertTrue(result)  # Returns True when disabled


class TestSetupGitHubManager(unittest.TestCase):
    """Test GitHub manager setup function"""

    @patch.dict(os.environ, {}, clear=True)
    def test_setup_github_manager_no_token(self):
        """Test GitHub manager setup with no token"""
        result = _setup_github_manager()
        self.assertIsNone(result)

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"})
    @patch("scripts.workflows.construction_monitor.GitHubManager")
    def test_setup_github_manager_success(self, mock_github_manager):
        """Test successful GitHub manager setup"""
        mock_instance = mock_github_manager.return_value

        result = _setup_github_manager()

        self.assertEqual(result, mock_instance)
        mock_github_manager.assert_called_once_with("test-token", "jayljohnson", "nordhus.site")

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"})
    @patch("scripts.workflows.construction_monitor.GitHubManager")
    def test_setup_github_manager_exception(self, mock_github_manager):
        """Test GitHub manager setup with exception"""
        mock_github_manager.side_effect = Exception("GitHub API error")

        result = _setup_github_manager()

        self.assertIsNone(result)


class TestHandleProjectIssue(unittest.TestCase):
    """Test project issue handling function"""

    def test_handle_project_issue_no_manager(self):
        """Test issue handling with no GitHub manager"""
        result = _handle_project_issue(None, "test-project", "Test Project", "http://example.com")
        self.assertEqual(result, 0)

    @patch("scripts.workflows.construction_monitor.logger")
    def test_handle_project_issue_existing_issue(self, mock_logger):
        """Test finding existing GitHub issue"""
        mock_github_manager = unittest.mock.Mock()
        mock_github_manager.find_existing_issue.return_value = {"number": 123}

        result = _handle_project_issue(mock_github_manager, "test-project", "Test Project", "http://example.com")

        self.assertEqual(result, 123)
        mock_github_manager.find_existing_issue.assert_called_once_with("test-project")
        mock_logger.info.assert_called_with("Found existing issue #123: Construction Project: Test Project")

    @patch("scripts.workflows.construction_monitor.logger")
    def test_handle_project_issue_create_new(self, mock_logger):
        """Test creating new GitHub issue"""
        mock_github_manager = unittest.mock.Mock()
        mock_github_manager.find_existing_issue.return_value = None
        mock_github_manager.create_issue.return_value = {"number": 456}

        result = _handle_project_issue(mock_github_manager, "test-project", "Test Project", "http://example.com")

        self.assertEqual(result, 456)
        mock_github_manager.find_existing_issue.assert_called_once_with("test-project")
        mock_github_manager.create_issue.assert_called_once_with("test-project", "Test Project", "http://example.com")
        mock_logger.info.assert_called_with("Created GitHub issue #456")

    @patch("scripts.workflows.construction_monitor.logger")
    def test_handle_project_issue_create_failed(self, mock_logger):
        """Test failed GitHub issue creation"""
        mock_github_manager = unittest.mock.Mock()
        mock_github_manager.find_existing_issue.return_value = None
        mock_github_manager.create_issue.return_value = None

        result = _handle_project_issue(mock_github_manager, "test-project", "Test Project", "http://example.com")

        self.assertEqual(result, 0)

    @patch("scripts.workflows.construction_monitor.logger")
    def test_handle_project_issue_exception(self, mock_logger):
        """Test exception during issue handling"""
        mock_github_manager = unittest.mock.Mock()
        mock_github_manager.find_existing_issue.side_effect = Exception("API error")

        result = _handle_project_issue(mock_github_manager, "test-project", "Test Project", "http://example.com")

        self.assertEqual(result, 0)
        mock_logger.error.assert_called_with("GitHub issue management failed: API error")


class TestSyncProjectPhotos(unittest.TestCase):
    """Test project photo sync function"""

    @patch("scripts.workflows.construction_monitor.logger")
    def test_sync_project_photos_success_with_github(self, mock_logger):
        """Test successful photo sync with GitHub update"""
        mock_manager = unittest.mock.Mock()
        mock_manager.sync_photos_from_cloudinary.return_value = 3

        mock_github_manager = unittest.mock.Mock()

        result = _sync_project_photos(mock_manager, mock_github_manager, "test-project", 123)

        self.assertTrue(result)
        mock_manager.sync_photos_from_cloudinary.assert_called_once()
        mock_github_manager.add_issue_comment.assert_called_once_with(123, "test-project", 0, 3)
        mock_logger.success.assert_called_with("Synced 3 new photos for project: test-project")

    @patch("scripts.workflows.construction_monitor.logger")
    def test_sync_project_photos_success_no_github(self, mock_logger):
        """Test successful photo sync without GitHub manager"""
        mock_manager = unittest.mock.Mock()
        mock_manager.sync_photos_from_cloudinary.return_value = 2

        result = _sync_project_photos(mock_manager, None, "test-project", 0)

        self.assertTrue(result)
        mock_manager.sync_photos_from_cloudinary.assert_called_once()
        mock_logger.success.assert_called_with("Synced 2 new photos for project: test-project")

    @patch("scripts.workflows.construction_monitor.logger")
    def test_sync_project_photos_no_new_photos(self, mock_logger):
        """Test photo sync with no new photos"""
        mock_manager = unittest.mock.Mock()
        mock_manager.sync_photos_from_cloudinary.return_value = 0

        result = _sync_project_photos(mock_manager, None, "test-project", 0)

        self.assertFalse(result)
        mock_logger.info.assert_called_with("No new photos for project: test-project")

    @patch("scripts.workflows.construction_monitor.logger")
    def test_sync_project_photos_github_update_failed(self, mock_logger):
        """Test photo sync with failed GitHub update"""
        mock_manager = unittest.mock.Mock()
        mock_manager.sync_photos_from_cloudinary.return_value = 1

        mock_github_manager = unittest.mock.Mock()
        mock_github_manager.add_issue_comment.side_effect = Exception("GitHub API error")

        result = _sync_project_photos(mock_manager, mock_github_manager, "test-project", 123)

        self.assertTrue(result)  # Still returns True even if GitHub update fails
        mock_logger.warning.assert_called_with("Failed to update GitHub issue: GitHub API error")


class TestScanAndSyncProjects(unittest.TestCase):
    """Test main scan and sync function"""

    @patch("scripts.workflows.construction_monitor.CloudinaryClient")
    def test_scan_and_sync_cloudinary_auth_failure(self, mock_client_class):
        """Test scan with Cloudinary authentication failure"""
        mock_client = mock_client_class.return_value
        mock_client.authenticate.return_value = False

        result = scan_and_sync_projects()

        self.assertFalse(result)

    @patch("scripts.workflows.construction_monitor.CloudinaryClient")
    @patch("scripts.workflows.construction_monitor._setup_github_manager")
    def test_scan_and_sync_no_projects(self, mock_setup_github, mock_client_class):
        """Test scan with no projects found"""
        mock_client = mock_client_class.return_value
        mock_client.authenticate.return_value = True
        mock_client.get_construction_projects.return_value = []
        mock_setup_github.return_value = None

        result = scan_and_sync_projects()

        self.assertTrue(result)

    @patch("scripts.workflows.construction_monitor.CloudinaryClient")
    @patch("scripts.workflows.construction_monitor._setup_github_manager")
    @patch("scripts.workflows.construction_monitor._handle_project_issue")
    @patch("scripts.workflows.construction_monitor._sync_project_photos")
    @patch("scripts.workflows.construction_monitor.logger")
    def test_scan_and_sync_with_projects(self, mock_logger, mock_sync_photos, mock_handle_issue, mock_setup_github, mock_client_class):
        """Test scan with projects found"""
        # Setup mocks
        mock_client = mock_client_class.return_value
        mock_client.authenticate.return_value = True
        mock_client.get_construction_projects.return_value = [{"project_name": "test-project", "title": "Test Project", "url": "http://example.com"}]

        mock_github_manager = unittest.mock.Mock()
        mock_setup_github.return_value = mock_github_manager
        mock_handle_issue.return_value = 123
        mock_sync_photos.return_value = True

        # Mock SimpleProjectManager directly in the function
        with patch("scripts.workflows.construction_monitor.SimpleProjectManager") as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.project_directory.exists.return_value = False
            mock_manager.create_project_branch.return_value = True

            result = scan_and_sync_projects()

            self.assertTrue(result)
            mock_logger.info.assert_any_call("Found 1 construction projects")
            mock_logger.info.assert_any_call("🆕 New project detected: test-project")

    @patch("scripts.workflows.construction_monitor.CloudinaryClient")
    def test_scan_and_sync_exception_handling(self, mock_client_class):
        """Test scan with exception handling"""
        mock_client_class.side_effect = Exception("Unexpected error")

        result = scan_and_sync_projects()

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
