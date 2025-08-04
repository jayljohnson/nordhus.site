#!/usr/bin/env python3
"""
Unit tests for the Construction Monitor module.
Tests photo client selection, environment validation, and main workflow orchestration.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from scripts.workflows.construction_monitor import get_photo_client
from scripts.workflows.construction_monitor import main


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

        self.assertIn("Cloudinary credentials not found", str(cm.exception))
        self.assertIn("CLOUDINARY_URL=cloudinary://", str(cm.exception))

    @patch.dict(os.environ, {"CLOUDINARY_CLOUD_NAME": "test-cloud"})
    def test_get_photo_client_partial_credentials(self):
        """Test getting photo client with partial credentials"""
        with self.assertRaises(ValueError) as cm:
            get_photo_client()

        self.assertIn("Cloudinary credentials not found", str(cm.exception))


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
        with patch("builtins.print") as mock_print:
            result = main()

            self.assertIsNone(result)
            mock_print.assert_any_call("Photo monitoring is disabled via ENABLE_PHOTO_MONITORING environment variable")
            mock_print.assert_any_call("Set ENABLE_PHOTO_MONITORING=true to enable photo album integration")

    @patch.dict(os.environ, {"ENABLE_PHOTO_MONITORING": "True"})  # Test case insensitive
    def test_main_missing_github_token(self):
        """Test main function with missing GitHub token"""
        with self.assertRaises(Exception) as cm:
            main()

        self.assertIn("GITHUB_TOKEN environment variable required", str(cm.exception))

    @patch.dict(os.environ, {"ENABLE_PHOTO_MONITORING": "true", "GITHUB_TOKEN": "test-token"})
    @patch("scripts.workflows.construction_monitor.get_photo_client")
    def test_main_photo_client_error(self, mock_get_client):
        """Test main function when photo client configuration fails"""
        mock_get_client.side_effect = ValueError("Test photo client error")

        with patch("builtins.print") as mock_print:
            result = main()

            self.assertFalse(result)
            mock_print.assert_called_with("❌ Photo service configuration error: Test photo client error")

    @patch.dict(os.environ, {"ENABLE_PHOTO_MONITORING": "true", "GITHUB_TOKEN": "test-token"})
    @patch("scripts.workflows.construction_monitor.get_photo_client")
    def test_main_workflow_initialization(self, mock_get_client):
        """Test that main function initializes workflow components correctly"""
        # Mock photo client
        mock_client = Mock()
        mock_hasher = Mock()
        mock_get_client.return_value = (mock_client, mock_hasher)

        # We expect this to fail when trying to run the workflow, but we want to test
        # that we get to the point of creating the workflow
        import contextlib

        with contextlib.suppress(Exception):
            main()  # Expected to fail at workflow.run()

        # Verify get_photo_client was called
        mock_get_client.assert_called_once()

    @patch.dict(os.environ, {"ENABLE_PHOTO_MONITORING": "true", "GITHUB_TOKEN": "test-token"})
    @patch("scripts.workflows.construction_monitor.get_photo_client")
    @patch("scripts.workflows.construction_workflow.ConstructionWorkflow")
    def test_main_workflow_failure(self, mock_workflow_class, mock_get_client):
        """Test main function when workflow fails"""
        # Mock photo client
        mock_client = Mock()
        mock_hasher = Mock()
        mock_get_client.return_value = (mock_client, mock_hasher)

        # Mock workflow failure
        mock_workflow = Mock()
        mock_workflow.run.return_value = False
        mock_workflow_class.return_value = mock_workflow

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
        with self.assertRaises(ValueError):  # Will fail on missing GITHUB_TOKEN
            main()
        # If we get to the point of checking GITHUB_TOKEN, photo monitoring was enabled

    @patch.dict(os.environ, {"ENABLE_PHOTO_MONITORING": "False"})
    def test_disable_photo_monitoring_false_value(self):
        """Test photo monitoring disabled with 'False' value"""
        result = main()
        self.assertIsNone(result)

    @patch.dict(os.environ, {"ENABLE_PHOTO_MONITORING": "0"})
    def test_disable_photo_monitoring_zero_value(self):
        """Test photo monitoring disabled with '0' value"""
        result = main()
        self.assertIsNone(result)

    @patch.dict(os.environ, {}, clear=True)  # Remove all env vars
    def test_enable_photo_monitoring_default_value(self):
        """Test photo monitoring disabled by default"""
        result = main()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
