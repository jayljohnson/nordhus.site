#!/usr/bin/env python3
"""
Unit tests for the Project Manager system.
Tests project creation, photo management, and blog post generation.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import mock_open
from unittest.mock import patch

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from scripts.project.project_manager import SimpleProjectManager
from scripts.project.project_manager import add_photos
from scripts.project.project_manager import create_project_branch
from scripts.project.project_manager import finish_project
from scripts.project.project_manager import get_project_branch
from scripts.project.project_manager import get_project_dir
from scripts.project.project_manager import main
from scripts.project.project_manager import setup_project_directory
from scripts.project.project_manager import start_project


class TestProjectManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Mock git operations
        self.git_patcher = patch("subprocess.run")
        self.mock_subprocess = self.git_patcher.start()
        self.mock_subprocess.return_value.returncode = 0
        self.mock_subprocess.return_value.stdout = ""

        # Change to temp directory for tests
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures"""
        self.git_patcher.stop()
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)


class TestProjectDirectoryOperations(TestProjectManager):
    """Test project directory and branch operations"""

    @patch("scripts.project.project_manager.datetime")
    def test_get_project_dir(self, mock_datetime):
        """Test generating project directory paths"""
        mock_datetime.now.return_value.strftime.return_value = "2025-01"

        result = get_project_dir("deck-repair")
        expected = Path("assets/images/2025-01-deck-repair")

        self.assertEqual(result, expected)

    def test_get_project_branch(self):
        """Test generating project branch names"""
        # Test with explicit date prefix to avoid datetime mocking
        from scripts.utils.git_operations import GitOperations

        result = GitOperations.get_project_branch("deck-repair", "2025-01")
        expected = "project/2025-01-deck-repair"
        self.assertEqual(result, expected)

        # Test that the function returns a properly formatted branch name
        # (we can't easily test the current date without complex mocking)
        result_today = get_project_branch("deck-repair")
        self.assertTrue(result_today.startswith("project/"))
        self.assertTrue(result_today.endswith("-deck-repair"))

    @patch("scripts.project.project_manager.get_project_dir")
    def test_setup_project_directory(self, mock_get_project_dir):
        """Test creating project directory and metadata"""
        project_name = "test-project"

        # Mock the project directory to be in temp directory
        mock_project_dir = self.temp_path / f"2025-01-15-{project_name}"
        mock_get_project_dir.return_value = mock_project_dir

        with patch("scripts.project.project_manager.datetime") as mock_dt:
            mock_dt.now.return_value.isoformat.return_value = "2025-01-15T10:00:00"
            mock_dt.now.return_value.strftime.return_value = "2025-01"

            project_dir = setup_project_directory(project_name)

        # Verify directory creation
        self.assertTrue(project_dir.exists())
        self.assertTrue(project_dir.is_dir())

        # Verify metadata file
        metadata_file = project_dir / "project.json"
        self.assertTrue(metadata_file.exists())

        with open(metadata_file) as f:
            metadata = json.load(f)

        expected_metadata = {
            "project_name": project_name,
            "created_date": "2025-01",
            "total_photos": 0,
            "last_sync": "2025-01-15T10:00:00",
        }

        self.assertEqual(metadata, expected_metadata)

    def test_create_project_branch_new(self):
        """Test creating a new project branch"""

        # Mock git branch list to show branch doesn't exist

        def mock_subprocess_side_effect(cmd, **kwargs):
            mock_result = Mock()
            mock_result.returncode = 0

            if "branch --list" in " ".join(cmd):
                mock_result.stdout = ""  # Branch doesn't exist
            else:
                mock_result.stdout = ""

            return mock_result

        self.mock_subprocess.side_effect = mock_subprocess_side_effect

        result = create_project_branch("test-project")

        self.assertIsNotNone(result)
        self.assertIn("test-project", result)

        # Verify basic git commands were called (simplified check)
        call_args = [str(call) for call in self.mock_subprocess.call_args_list]
        has_checkout = any("checkout" in call for call in call_args)
        self.assertTrue(has_checkout)

    def test_create_project_branch_existing(self):
        """Test switching to existing project branch"""
        # Use current date format for realistic branch name
        current_date = datetime.now().strftime("%Y-%m-%d")
        branch_name = f"project/{current_date}-test-project"

        # Mock git branch list to show branch exists

        def mock_subprocess_side_effect(cmd, **kwargs):
            mock_result = Mock()
            mock_result.returncode = 0

            if "branch --list" in " ".join(cmd):
                mock_result.stdout = branch_name  # Branch exists
            else:
                mock_result.stdout = ""

            return mock_result

        self.mock_subprocess.side_effect = mock_subprocess_side_effect

        result = create_project_branch("test-project")

        self.assertIsNotNone(result)
        self.assertEqual(result, branch_name)

        # Should checkout existing branch
        checkout_calls = [call for call in self.mock_subprocess.call_args_list if "checkout" in str(call)]
        self.assertTrue(any(branch_name in str(call) for call in checkout_calls))


class TestPhotoManagement(TestProjectManager):
    """Test photo discovery and management"""

    @patch("scripts.project.project_manager.Config.is_photo_monitoring_enabled")
    def test_sync_photos_monitoring_disabled(self, mock_config):
        """Test photo sync when monitoring is disabled"""
        mock_config.return_value = False
        manager = SimpleProjectManager("test-project")

        result = manager.sync_photos_from_cloudinary()

        self.assertEqual(result, 0)

    @patch("scripts.project.project_manager.GitOperations.commit_changes")
    @patch("scripts.project.project_manager.CloudinaryClient")
    @patch("scripts.project.project_manager.Config.is_photo_monitoring_enabled")
    def test_sync_photos_success(self, mock_config, mock_cloudinary_class, mock_commit):
        """Test successful photo sync"""
        mock_config.return_value = True
        mock_commit.return_value = True

        # Setup mock Cloudinary client
        mock_client = Mock()
        mock_client.download_folder_photos.return_value = [Path("photo1.jpg"), Path("photo2.jpg")]
        mock_cloudinary_class.return_value = mock_client

        manager = SimpleProjectManager("test-project")

        with patch("pathlib.Path.mkdir"), patch("builtins.open", mock_open()) as mock_file, patch("json.dump") as mock_json_dump:
            result = manager.sync_photos_from_cloudinary()

            self.assertEqual(result, 2)
            mock_client.download_folder_photos.assert_called_once_with("test-project", str(manager.project_directory), tag_downloaded=True)
            mock_commit.assert_called_once()

    @patch("scripts.project.project_manager.CloudinaryClient")
    @patch("scripts.project.project_manager.Config.is_photo_monitoring_enabled")
    def test_sync_photos_exception_handling(self, mock_config, mock_cloudinary_class):
        """Test photo sync exception handling"""
        mock_config.return_value = True
        mock_cloudinary_class.side_effect = Exception("Connection failed")

        manager = SimpleProjectManager("test-project")

        result = manager.sync_photos_from_cloudinary()

        self.assertEqual(result, 0)

    def test_update_project_metadata_new_file(self):
        """Test creating new project metadata"""
        manager = SimpleProjectManager("test-project")

        with patch("pathlib.Path.mkdir"), patch("pathlib.Path.exists", return_value=False), patch("builtins.open", mock_open()) as mock_file, patch(
            "json.dump"
        ) as mock_json_dump:
            manager._update_project_metadata(3)

            metadata_args = mock_json_dump.call_args[0][0]
            self.assertEqual(metadata_args["project_name"], "test-project")
            self.assertEqual(metadata_args["total_photos"], 3)

    def test_update_project_metadata_existing_file(self):
        """Test updating existing project metadata"""
        manager = SimpleProjectManager("test-project")

        existing_metadata = {"project_name": "test-project", "created_date": "2025-08-06", "total_photos": 2}

        with patch("pathlib.Path.mkdir"), patch("pathlib.Path.exists", return_value=True), patch("builtins.open", mock_open()) as mock_file, patch(
            "json.load", return_value=existing_metadata
        ), patch("json.dump") as mock_json_dump:
            manager._update_project_metadata(3)

            updated_metadata = mock_json_dump.call_args[0][0]
            self.assertEqual(updated_metadata["total_photos"], 5)  # 2 + 3


class TestBlogPostGeneration(TestProjectManager):
    """Test blog post generation functionality"""

    def test_simple_project_manager_properties(self):
        """Test SimpleProjectManager property generation"""
        with patch("scripts.project.project_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2025-08-07"

            manager = SimpleProjectManager("deck-repair")

            self.assertEqual(str(manager.project_directory), "assets/images/2025-08-07-deck-repair")
            self.assertEqual(str(manager.blog_post_path), "_posts/2025-08-07-deck-repair.md")
            self.assertEqual(manager.feature_branch, "project/2025-08-07-deck-repair")

    @patch("scripts.project.project_manager.GitOperations.create_or_switch_branch")
    def test_create_project_branch_method(self, mock_git):
        """Test SimpleProjectManager.create_project_branch method"""
        mock_git.return_value = True
        manager = SimpleProjectManager("test-project")

        result = manager.create_project_branch()

        self.assertTrue(result)
        mock_git.assert_called_once_with(manager.feature_branch)

    def test_blog_post_content_generation(self):
        """Test blog post content creation"""
        manager = SimpleProjectManager("deck-repair")

        mock_photos = [
            Path("assets/images/2025-08-07-deck-repair/before.jpg"),
            Path("assets/images/2025-08-07-deck-repair/during.jpg"),
            Path("assets/images/2025-08-07-deck-repair/after.jpg"),
        ]

        content = manager._create_blog_content(mock_photos)

        # Verify content structure and formatting
        self.assertIn('title: "Deck Repair"', content)
        self.assertIn("categories: [construction, projects]", content)
        self.assertIn("3 photos", content)
        self.assertIn("![before](", content)
        self.assertIn("![during](", content)
        self.assertIn("![after](", content)
        self.assertIn("Project documentation generated", content)

    def test_get_photo_files_multiple_extensions(self):
        """Test photo file discovery with different extensions"""
        manager = SimpleProjectManager("test-project")

        # Mock different photo file types
        mock_photos = [Path("photo1.jpg"), Path("photo2.JPG"), Path("photo3.png"), Path("photo4.PNG"), Path("photo5.jpeg"), Path("photo6.JPEG")]

        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.glob") as mock_glob:

            def glob_side_effect(pattern):
                ext_map = {
                    "*.jpg": [mock_photos[0]],
                    "*.JPG": [mock_photos[1]],
                    "*.png": [mock_photos[2]],
                    "*.PNG": [mock_photos[3]],
                    "*.jpeg": [mock_photos[4]],
                    "*.JPEG": [mock_photos[5]],
                }
                return ext_map.get(pattern, [])

            mock_glob.side_effect = glob_side_effect

            result = manager._get_photo_files()

            self.assertEqual(len(result), 6)

    def test_generate_blog_post_success_workflow(self):
        """Test complete blog post generation workflow"""
        manager = SimpleProjectManager("test-project")

        mock_photos = [Path("photo1.jpg"), Path("photo2.jpg")]

        with patch("pathlib.Path.exists", return_value=True), patch.object(manager, "_get_photo_files", return_value=mock_photos), patch(
            "pathlib.Path.mkdir"
        ), patch("builtins.open", mock_open()) as mock_file:
            result = manager.generate_blog_post()

            self.assertEqual(result, manager.blog_post_path)
            mock_file.assert_called_once_with(manager.blog_post_path, "w")

    def test_generate_blog_post_no_directory(self):
        """Test blog post generation when project directory missing"""
        manager = SimpleProjectManager("test-project")

        with patch("pathlib.Path.exists", return_value=False):
            result = manager.generate_blog_post()

            self.assertIsNone(result)


class TestStartProject(TestProjectManager):
    """Test complete project start workflow"""

    @patch("scripts.project.project_manager.GitOperations.commit_changes")
    @patch("scripts.project.project_manager.SimpleProjectManager.create_project_branch")
    def test_start_project_complete_workflow(self, mock_create_branch, mock_commit):
        """Test complete start_project workflow"""
        mock_create_branch.return_value = True
        mock_commit.return_value = True

        with patch("pathlib.Path.mkdir") as mock_mkdir, patch("builtins.open", mock_open()) as mock_file, patch("json.dump") as mock_json_dump:
            result = start_project("test-project")

            self.assertTrue(result)
            mock_create_branch.assert_called_once()
            mock_commit.assert_called_once()

    def test_start_project_invalid_names(self):
        """Test start_project rejects invalid project names"""
        invalid_names = ["project with spaces", "project@special", "project/slash", "project.dot", ""]

        for name in invalid_names:
            with self.subTest(name=name):
                result = start_project(name)
                self.assertFalse(result)

    @patch("scripts.project.project_manager.SimpleProjectManager.create_project_branch")
    def test_start_project_branch_creation_failure(self, mock_create_branch):
        """Test start_project when branch creation fails"""
        mock_create_branch.return_value = False

        result = start_project("test-project")

        self.assertFalse(result)

    @patch("scripts.project.project_manager.GitOperations.checkout_branch")
    def test_add_photos_project_not_found(self, mock_checkout):
        """Test add_photos when project doesn't exist"""
        with patch("pathlib.Path.exists", return_value=False):
            result = add_photos("nonexistent-project")

            self.assertFalse(result)
            mock_checkout.assert_not_called()

    @patch("scripts.project.project_manager.SimpleProjectManager.sync_photos_from_cloudinary")
    @patch("scripts.project.project_manager.GitOperations.checkout_branch")
    def test_add_photos_success(self, mock_checkout, mock_sync):
        """Test successful add_photos workflow"""
        mock_checkout.return_value = True
        mock_sync.return_value = 3

        with patch("pathlib.Path.exists", return_value=True):
            result = add_photos("test-project")

            self.assertTrue(result)
            mock_checkout.assert_called_once()
            mock_sync.assert_called_once()

    @patch("scripts.project.project_manager.GitOperations.checkout_branch")
    def test_add_photos_checkout_failure(self, mock_checkout):
        """Test add_photos when branch checkout fails"""
        mock_checkout.return_value = False

        with patch("pathlib.Path.exists", return_value=True):
            result = add_photos("test-project")

            self.assertFalse(result)

    @patch("scripts.project.project_manager.GitOperations.add_and_commit_files")
    @patch("scripts.project.project_manager.GitOperations.checkout_branch")
    @patch("scripts.project.project_manager.SimpleProjectManager.generate_blog_post")
    def test_finish_project_success(self, mock_generate, mock_checkout, mock_commit):
        """Test successful finish_project workflow"""
        mock_checkout.return_value = True
        mock_generate.return_value = Path("_posts/2025-08-07-test-project.md")
        mock_commit.return_value = True

        with patch("pathlib.Path.exists", return_value=True):
            result = finish_project("test-project")

            self.assertTrue(result)
            mock_checkout.assert_called_once()
            mock_generate.assert_called_once()
            mock_commit.assert_called_once()

    @patch("scripts.project.project_manager.GitOperations.checkout_branch")
    def test_finish_project_no_directory(self, mock_checkout):
        """Test finish_project when project directory doesn't exist"""
        with patch("pathlib.Path.exists", return_value=False):
            result = finish_project("nonexistent-project")

            self.assertFalse(result)
            mock_checkout.assert_not_called()

    @patch("scripts.project.project_manager.GitOperations.checkout_branch")
    @patch("scripts.project.project_manager.SimpleProjectManager.generate_blog_post")
    def test_finish_project_blog_generation_failure(self, mock_generate, mock_checkout):
        """Test finish_project when blog generation fails"""
        mock_checkout.return_value = True
        mock_generate.return_value = None

        with patch("pathlib.Path.exists", return_value=True):
            result = finish_project("test-project")

            self.assertFalse(result)

    @patch("sys.argv", ["project_manager.py", "start", "test-project"])
    @patch("scripts.project.project_manager.start_project")
    def test_main_start_command(self, mock_start):
        """Test main CLI with start command"""
        mock_start.return_value = True

        with patch("sys.exit") as mock_exit:
            main()

            mock_start.assert_called_once_with("test-project")
            mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["project_manager.py", "add-photos", "test-project"])
    @patch("scripts.project.project_manager.add_photos")
    def test_main_add_photos_command(self, mock_add_photos):
        """Test main CLI with add-photos command"""
        mock_add_photos.return_value = True

        with patch("sys.exit") as mock_exit:
            main()

            mock_add_photos.assert_called_once_with("test-project")
            mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["project_manager.py", "finish", "test-project"])
    @patch("scripts.project.project_manager.finish_project")
    def test_main_finish_command(self, mock_finish):
        """Test main CLI with finish command"""
        mock_finish.return_value = True

        with patch("sys.exit") as mock_exit:
            main()

            mock_finish.assert_called_once_with("test-project")
            mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["project_manager.py", "unknown", "test-project"])
    def test_main_unknown_command(self):
        """Test main CLI with unknown command"""
        with patch("sys.exit") as mock_exit:
            main()

            mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["project_manager.py"])
    def test_main_insufficient_args(self):
        """Test main CLI with insufficient arguments"""
        with patch("sys.exit", side_effect=SystemExit) as mock_exit:
            with self.assertRaises(SystemExit):
                main()

            mock_exit.assert_called_once_with(1)

    @patch("scripts.project.project_manager.setup_project_directory")
    @patch("scripts.project.project_manager.create_project_branch")
    def test_start_project_invalid_name(self, mock_create_branch, mock_setup_dir):
        """Test project start with invalid project name"""
        invalid_names = [
            "project with spaces!",
            "project@with$symbols",
            "project/with/slashes",
            "",
        ]

        for name in invalid_names:
            with self.subTest(name=name):
                result = start_project(name)
                self.assertFalse(result)
                # Verify no real operations were attempted for invalid names
                mock_create_branch.assert_not_called()
                mock_setup_dir.assert_not_called()
                mock_create_branch.reset_mock()
                mock_setup_dir.reset_mock()

    @patch("scripts.project.project_manager.SimpleProjectManager.create_project_branch")
    def test_start_project_branch_failure(self, mock_create_branch):
        """Test project start when branch creation fails"""
        mock_create_branch.return_value = False  # Simplified manager returns bool

        result = start_project("test-project")

        self.assertFalse(result)


if __name__ == "__main__":
    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        TestProjectDirectoryOperations,
        TestPhotoManagement,
        TestBlogPostGeneration,
        TestStartProject,
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)
