#!/usr/bin/env python3
"""
Unit tests for the CLI module.
Tests all CLI commands and their error handling.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

from click.testing import CliRunner

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from scripts.cli import cli


class TestCLI(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_cli_version(self):
        """Test CLI version command"""
        result = self.runner.invoke(cli, ["--version"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("1.0.0", result.output)

    def test_cli_help(self):
        """Test CLI help command"""
        result = self.runner.invoke(cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Jekyll Site Management CLI", result.output)

    def test_project_group_help(self):
        """Test project group help"""
        result = self.runner.invoke(cli, ["project", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Construction project management commands", result.output)

    def test_cloudinary_group_help(self):
        """Test cloudinary group help"""
        result = self.runner.invoke(cli, ["cloudinary", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Cloudinary API integration commands", result.output)

    def test_dev_group_help(self):
        """Test dev group help"""
        result = self.runner.invoke(cli, ["dev", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Development and maintenance commands", result.output)

    @patch("scripts.cli.start_project")
    @patch("scripts.cli.get_project_branch")
    @patch("scripts.cli.get_project_dir")
    def test_start_project_success(self, mock_get_dir, mock_get_branch, mock_start):
        """Test successful project start"""
        mock_get_branch.return_value = "project/test-project"
        mock_get_dir.return_value = Path("/test/project")

        result = self.runner.invoke(cli, ["project", "start", "test-project"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Starting construction project: test-project", result.output)
        self.assertIn("✅ Project 'test-project' started successfully!", result.output)
        mock_start.assert_called_once_with("test-project")

    @patch("scripts.cli.start_project")
    def test_start_project_failure(self, mock_start):
        """Test project start failure"""
        mock_start.side_effect = Exception("Test error")

        result = self.runner.invoke(cli, ["project", "start", "test-project"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("❌ Error starting project: Test error", result.output)

    @patch("scripts.cli.start_project")
    @patch("scripts.cli.get_project_branch")
    @patch("scripts.cli.get_project_dir")
    def test_start_project_with_photos(self, mock_get_dir, mock_get_branch, mock_start):
        """Test project start with photo integration enabled"""
        mock_get_branch.return_value = "project/test-project"
        mock_get_dir.return_value = Path("/test/project")

        # Clear only the specific env var we're testing
        old_env = os.environ.get("ENABLE_PHOTO_MONITORING")
        if "ENABLE_PHOTO_MONITORING" in os.environ:
            del os.environ["ENABLE_PHOTO_MONITORING"]

        try:
            result = self.runner.invoke(cli, ["project", "start", "test-project", "--enable-photos"])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("Photo integration enabled", result.output)
            self.assertIn("Photo monitoring: Enabled", result.output)
            self.assertEqual(os.environ.get("ENABLE_PHOTO_MONITORING"), "true")
        finally:
            # Restore original env var state
            if old_env is not None:
                os.environ["ENABLE_PHOTO_MONITORING"] = old_env
            elif "ENABLE_PHOTO_MONITORING" in os.environ:
                del os.environ["ENABLE_PHOTO_MONITORING"]

    @patch("scripts.cli.add_photos")
    def test_add_photos_success(self, mock_add_photos):
        """Test successful add photos command"""
        result = self.runner.invoke(cli, ["project", "add-photos", "test-project"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Adding photos to project: test-project", result.output)
        self.assertIn("✅ Photos added to project 'test-project' successfully!", result.output)
        mock_add_photos.assert_called_once_with("test-project")

    @patch("scripts.cli.add_photos")
    def test_add_photos_failure(self, mock_add_photos):
        """Test add photos command failure"""
        mock_add_photos.side_effect = Exception("Photo error")

        result = self.runner.invoke(cli, ["project", "add-photos", "test-project"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("❌ Error adding photos: Photo error", result.output)

    @patch("scripts.cli.finish_project")
    def test_finish_project_success(self, mock_finish):
        """Test successful finish project command"""
        result = self.runner.invoke(cli, ["project", "finish", "test-project"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Finishing project: test-project", result.output)
        self.assertIn("✅ Project 'test-project' finished successfully!", result.output)
        mock_finish.assert_called_once_with("test-project")

    @patch("scripts.cli.finish_project")
    def test_finish_project_failure(self, mock_finish):
        """Test finish project command failure"""
        mock_finish.side_effect = Exception("Finish error")

        result = self.runner.invoke(cli, ["project", "finish", "test-project"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("❌ Error finishing project: Finish error", result.output)

    @patch("scripts.cli.get_project_branch")
    @patch("scripts.cli.get_project_dir")
    def test_project_status_no_photos(self, mock_get_dir, mock_get_branch):
        """Test project status command with no photos"""
        mock_get_branch.return_value = "project/test-project"
        mock_project_dir = Mock()
        mock_project_dir.exists.return_value = False
        mock_get_dir.return_value = mock_project_dir

        result = self.runner.invoke(cli, ["project", "status", "test-project"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Project: test-project", result.output)
        self.assertIn("Branch: project/test-project", result.output)
        self.assertIn("Directory exists: False", result.output)

    @patch("scripts.cli.get_project_branch")
    @patch("scripts.cli.get_project_dir")
    def test_project_status_with_photos(self, mock_get_dir, mock_get_branch):
        """Test project status command with photos"""
        mock_get_branch.return_value = "project/test-project"
        mock_project_dir = Mock()
        mock_project_dir.exists.return_value = True
        mock_project_dir.glob.side_effect = lambda pattern: [Path("photo1.jpg"), Path("photo2.png")] if "*.jpg" in pattern else []
        mock_get_dir.return_value = mock_project_dir

        result = self.runner.invoke(cli, ["project", "status", "test-project"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Project: test-project", result.output)
        self.assertIn("Directory exists: True", result.output)
        self.assertIn("Photos: 2 files", result.output)

    @patch("scripts.cli.CloudinaryClient")
    def test_cloudinary_test_success(self, mock_client_class):
        """Test successful Cloudinary test command"""
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client

        result = self.runner.invoke(cli, ["cloudinary", "test"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Testing Cloudinary API connection...", result.output)
        self.assertIn("✅ Cloudinary API connection successful!", result.output)

    @patch("scripts.cli.CloudinaryClient")
    def test_cloudinary_test_auth_failure(self, mock_client_class):
        """Test Cloudinary test command authentication failure"""
        mock_client = Mock()
        mock_client.authenticate.return_value = False
        mock_client_class.return_value = mock_client

        result = self.runner.invoke(cli, ["cloudinary", "test"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("❌ Cloudinary API authentication failed", result.output)

    @patch("scripts.cli.CloudinaryClient")
    def test_cloudinary_test_exception(self, mock_client_class):
        """Test Cloudinary test command with exception"""
        mock_client_class.side_effect = Exception("Connection error")

        result = self.runner.invoke(cli, ["cloudinary", "test"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("❌ Error testing Cloudinary connection: Connection error", result.output)

    @patch("scripts.cli.CloudinaryClient")
    def test_cloudinary_projects_success(self, mock_client_class):
        """Test successful Cloudinary projects command"""
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_projects = [
            {"title": "Deck Repair", "id": "deck-repair-2023", "image_count": 15, "url": "https://cloudinary.com/folder/deck-repair-2023"}
        ]
        mock_client.get_construction_projects.return_value = mock_projects
        mock_client_class.return_value = mock_client

        result = self.runner.invoke(cli, ["cloudinary", "projects"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Found 1 project(s):", result.output)
        self.assertIn("📁 Deck Repair", result.output)
        self.assertIn("Images: 15", result.output)

    @patch("scripts.cli.CloudinaryClient")
    def test_cloudinary_projects_no_projects(self, mock_client_class):
        """Test Cloudinary projects command with no projects"""
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client.get_construction_projects.return_value = []
        mock_client_class.return_value = mock_client

        result = self.runner.invoke(cli, ["cloudinary", "projects"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("No construction projects found", result.output)

    @patch("scripts.cli.CloudinaryClient")
    def test_cloudinary_projects_auth_failure(self, mock_client_class):
        """Test Cloudinary projects command authentication failure"""
        mock_client = Mock()
        mock_client.authenticate.return_value = False
        mock_client_class.return_value = mock_client

        result = self.runner.invoke(cli, ["cloudinary", "projects"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("❌ Failed to authenticate with Cloudinary", result.output)

    @patch("scripts.cli.CloudinaryClient")
    def test_cloudinary_projects_exception(self, mock_client_class):
        """Test Cloudinary projects command with exception"""
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client.get_construction_projects.side_effect = Exception("API error")
        mock_client_class.return_value = mock_client

        result = self.runner.invoke(cli, ["cloudinary", "projects"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("❌ Error fetching projects: API error", result.output)

    @patch("subprocess.run")
    def test_dev_lint_success(self, mock_subprocess):
        """Test successful lint command"""
        mock_subprocess.return_value.returncode = 0

        result = self.runner.invoke(cli, ["dev", "lint"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Running linter (ruff check)...", result.output)
        self.assertIn("✅ Code linting passed", result.output)

    @patch("subprocess.run")
    def test_dev_lint_failure(self, mock_subprocess):
        """Test lint command failure"""
        mock_subprocess.return_value.returncode = 1

        result = self.runner.invoke(cli, ["dev", "lint"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("❌ Code linting failed", result.output)

    @patch("subprocess.run")
    def test_dev_lint_with_fix_success(self, mock_subprocess):
        """Test successful lint command with fix option"""
        mock_subprocess.return_value.returncode = 0

        result = self.runner.invoke(cli, ["dev", "lint", "--fix"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Running code formatter (ruff format)...", result.output)
        self.assertIn("✅ Code formatting completed", result.output)
        self.assertIn("Running linter with auto-fix (ruff check --fix)...", result.output)
        self.assertIn("✅ Code linting with auto-fix completed", result.output)

    @patch("subprocess.run")
    def test_dev_lint_format_failure(self, mock_subprocess):
        """Test lint command with format failure"""
        mock_subprocess.return_value.returncode = 1

        result = self.runner.invoke(cli, ["dev", "lint", "--fix"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("❌ Code formatting failed", result.output)

    @patch("subprocess.run")
    def test_dev_test_success(self, mock_subprocess):
        """Test successful test command"""
        mock_subprocess.return_value.returncode = 0

        result = self.runner.invoke(cli, ["dev", "test"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Running test suite...", result.output)
        self.assertIn("✅ All tests passed", result.output)

    @patch("subprocess.run")
    def test_dev_test_failure(self, mock_subprocess):
        """Test test command failure"""
        mock_subprocess.return_value.returncode = 1

        result = self.runner.invoke(cli, ["dev", "test"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("❌ Some tests failed", result.output)

    @patch("subprocess.run")
    def test_dev_test_with_coverage(self, mock_subprocess):
        """Test test command with coverage option"""
        mock_subprocess.return_value.returncode = 0

        result = self.runner.invoke(cli, ["dev", "test", "--coverage"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Running test suite...", result.output)
        self.assertIn("✅ All tests passed", result.output)
        self.assertIn("Coverage report generated in htmlcov/index.html", result.output)

    @patch("shutil.rmtree")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_dir")
    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.rglob")
    @patch("pathlib.Path.glob")
    def test_dev_clean_success(self, mock_glob, mock_rglob, mock_unlink, mock_is_dir, mock_exists, mock_rmtree):
        """Test successful clean command"""
        # Mock directory structure
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_rglob.return_value = [Path("scripts/__pycache__")]
        mock_glob.return_value = []

        result = self.runner.invoke(cli, ["dev", "clean"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Cleaning build artifacts...", result.output)
        self.assertIn("✅ Cleanup completed", result.output)


if __name__ == "__main__":
    unittest.main()
