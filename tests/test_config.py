#!/usr/bin/env python3
"""
Unit tests for the Config system.
Tests configuration management, environment variables, and feature flags.
"""

import os
import sys
import unittest
from unittest.mock import patch

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from scripts.utils.config import Config


class TestConfig(unittest.TestCase):
    """Test centralized configuration management"""

    def setUp(self):
        """Set up test fixtures"""
        # Store original environment
        self.original_env = os.environ.copy()

    def tearDown(self):
        """Clean up test fixtures"""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_photo_monitoring_enabled_true(self):
        """Test photo monitoring when enabled"""
        os.environ["ENABLE_PHOTO_MONITORING"] = "true"

        result = Config.is_photo_monitoring_enabled()

        self.assertTrue(result)

    def test_photo_monitoring_enabled_true_case_insensitive(self):
        """Test photo monitoring with mixed case 'True'"""
        os.environ["ENABLE_PHOTO_MONITORING"] = "True"

        result = Config.is_photo_monitoring_enabled()

        self.assertTrue(result)

    def test_photo_monitoring_enabled_true_uppercase(self):
        """Test photo monitoring with uppercase 'TRUE'"""
        os.environ["ENABLE_PHOTO_MONITORING"] = "TRUE"

        result = Config.is_photo_monitoring_enabled()

        self.assertTrue(result)

    def test_photo_monitoring_disabled_false(self):
        """Test photo monitoring when disabled with 'false'"""
        os.environ["ENABLE_PHOTO_MONITORING"] = "false"

        result = Config.is_photo_monitoring_enabled()

        self.assertFalse(result)

    def test_photo_monitoring_disabled_other_value(self):
        """Test photo monitoring when set to other value"""
        os.environ["ENABLE_PHOTO_MONITORING"] = "maybe"

        result = Config.is_photo_monitoring_enabled()

        self.assertFalse(result)

    def test_photo_monitoring_disabled_not_set(self):
        """Test photo monitoring when environment variable not set"""
        if "ENABLE_PHOTO_MONITORING" in os.environ:
            del os.environ["ENABLE_PHOTO_MONITORING"]

        result = Config.is_photo_monitoring_enabled()

        self.assertFalse(result)

    def test_enable_photo_monitoring(self):
        """Test enabling photo monitoring programmatically"""
        Config.enable_photo_monitoring()

        result = Config.is_photo_monitoring_enabled()

        self.assertTrue(result)
        self.assertEqual(os.environ["ENABLE_PHOTO_MONITORING"], "true")

    def test_get_github_token_present(self):
        """Test getting GitHub token when present"""
        test_token = "ghp_test_token_12345"
        os.environ["GITHUB_TOKEN"] = test_token

        result = Config.get_github_token()

        self.assertEqual(result, test_token)

    def test_get_github_token_absent(self):
        """Test getting GitHub token when absent"""
        if "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]

        result = Config.get_github_token()

        self.assertIsNone(result)

    def test_get_cloudinary_url_present(self):
        """Test getting Cloudinary URL when present"""
        test_url = "cloudinary://api_key:api_secret@cloud_name"
        os.environ["CLOUDINARY_URL"] = test_url

        result = Config.get_cloudinary_url()

        self.assertEqual(result, test_url)

    def test_get_cloudinary_url_absent(self):
        """Test getting Cloudinary URL when absent"""
        if "CLOUDINARY_URL" in os.environ:
            del os.environ["CLOUDINARY_URL"]

        result = Config.get_cloudinary_url()

        self.assertIsNone(result)

    def test_validate_required_env_monitoring_disabled(self):
        """Test validation when photo monitoring is disabled"""
        os.environ["ENABLE_PHOTO_MONITORING"] = "false"
        # Don't set any required vars
        if "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]
        if "CLOUDINARY_URL" in os.environ:
            del os.environ["CLOUDINARY_URL"]

        result = Config.validate_required_env()

        # Should return empty list since monitoring is disabled
        self.assertEqual(result, [])

    def test_validate_required_env_all_present(self):
        """Test validation when all required vars are present"""
        os.environ["ENABLE_PHOTO_MONITORING"] = "true"
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["CLOUDINARY_URL"] = "test_url"

        result = Config.validate_required_env()

        self.assertEqual(result, [])

    def test_validate_required_env_github_token_missing(self):
        """Test validation when GitHub token is missing"""
        os.environ["ENABLE_PHOTO_MONITORING"] = "true"
        os.environ["CLOUDINARY_URL"] = "test_url"
        if "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]

        result = Config.validate_required_env()

        self.assertEqual(result, ["GITHUB_TOKEN"])

    def test_validate_required_env_cloudinary_url_missing(self):
        """Test validation when Cloudinary URL is missing"""
        os.environ["ENABLE_PHOTO_MONITORING"] = "true"
        os.environ["GITHUB_TOKEN"] = "test_token"
        if "CLOUDINARY_URL" in os.environ:
            del os.environ["CLOUDINARY_URL"]

        result = Config.validate_required_env()

        self.assertEqual(result, ["CLOUDINARY_URL"])

    def test_validate_required_env_both_missing(self):
        """Test validation when both required vars are missing"""
        os.environ["ENABLE_PHOTO_MONITORING"] = "true"
        if "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]
        if "CLOUDINARY_URL" in os.environ:
            del os.environ["CLOUDINARY_URL"]

        result = Config.validate_required_env()

        # Should contain both missing variables
        self.assertEqual(set(result), {"GITHUB_TOKEN", "CLOUDINARY_URL"})
        self.assertEqual(len(result), 2)

    @patch("scripts.utils.logging.logger")
    def test_validate_or_exit_success(self, mock_logger):
        """Test validate_or_exit when all requirements are met"""
        os.environ["ENABLE_PHOTO_MONITORING"] = "true"
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["CLOUDINARY_URL"] = "test_url"

        # Should complete without calling logger.error
        Config.validate_or_exit()

        mock_logger.error.assert_not_called()

    @patch("scripts.utils.logging.logger")
    def test_validate_or_exit_missing_vars(self, mock_logger):
        """Test validate_or_exit when required vars are missing"""
        os.environ["ENABLE_PHOTO_MONITORING"] = "true"
        if "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]
        if "CLOUDINARY_URL" in os.environ:
            del os.environ["CLOUDINARY_URL"]

        Config.validate_or_exit()

        # Should call logger.error with exit_code=1
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        self.assertIn("Missing required environment variables", call_args[0][0])
        self.assertEqual(call_args[1]["exit_code"], 1)

    @patch("scripts.utils.logging.logger")
    def test_validate_or_exit_monitoring_disabled(self, mock_logger):
        """Test validate_or_exit when monitoring is disabled"""
        os.environ["ENABLE_PHOTO_MONITORING"] = "false"
        if "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]
        if "CLOUDINARY_URL" in os.environ:
            del os.environ["CLOUDINARY_URL"]

        Config.validate_or_exit()

        # Should not call logger.error since monitoring is disabled
        mock_logger.error.assert_not_called()


if __name__ == "__main__":
    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test class
    tests = unittest.TestLoader().loadTestsFromTestCase(TestConfig)
    test_suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)
