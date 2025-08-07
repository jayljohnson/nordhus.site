#!/usr/bin/env python3
"""
Unit tests for the Construction Workflow system.
Tests workflow orchestration, git operations, and GitHub integration.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import mock_open
from unittest.mock import patch

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from scripts.interfaces.photo_client_interface import PhotoClient
from scripts.interfaces.photo_client_interface import ProjectExtractor
from scripts.interfaces.photo_client_interface import ProjectHasher
from scripts.utils.git_operations import GitOperations
from scripts.workflows.construction_workflow import ConstructionWorkflow
from scripts.workflows.construction_workflow import GitHubManager
from scripts.workflows.construction_workflow import ProjectStateManager


class MockPhotoClient(PhotoClient):
    """Mock implementation of PhotoClient for testing"""

    def __init__(self):
        self.projects = []
        self.images = {}
        self.authenticated = True

    def authenticate(self) -> bool:
        return self.authenticated

    def get_construction_projects(self):
        return self.projects

    def get_project_images(self, project_id: str):
        return self.images.get(project_id, [])

    def download_image(self, image_url: str, download_dir: str, filename: str):
        # Create fake file
        file_path = Path(download_dir) / filename
        os.makedirs(download_dir, exist_ok=True)
        file_path.touch()
        return file_path

    def download_project_images(self, project_id: str, download_dir: str):
        images = self.get_project_images(project_id)
        downloaded = []
        for image in images:
            file_path = self.download_image(image["url"], download_dir, image["filename"])
            if file_path:
                downloaded.append(file_path)
        return downloaded


class MockProjectHasher(ProjectHasher):
    """Mock implementation of ProjectHasher for testing"""

    def generate_project_hash(self, project):
        return f"project_hash_{project.get('id', 'unknown')}"

    def generate_image_hash(self, image):
        return f"image_hash_{image.get('id', 'unknown')}"


class TestProjectExtractor(unittest.TestCase):
    """Test project name extraction utilities"""

    def test_extract_from_tag_valid(self):
        """Test extracting project name from valid tags"""
        test_cases = [
            ("project:deck_repair", "deck-repair"),
            ("project:kitchen-remodel", "kitchen-remodel"),
            ("project:Front Yard Fence", "front-yard-fence"),
            ("project:Bath Room #2", "bath-room-2"),
        ]

        for tag, expected in test_cases:
            with self.subTest(tag=tag):
                result = ProjectExtractor.extract_from_tag(tag)
                self.assertEqual(result, expected)

    def test_extract_from_tag_invalid(self):
        """Test extracting project name from invalid tags"""
        invalid_tags = ["not_a_project_tag", "project:", "construction:deck_repair", ""]

        for tag in invalid_tags:
            with self.subTest(tag=tag):
                result = ProjectExtractor.extract_from_tag(tag)
                self.assertIsNone(result)

    def test_extract_from_title_valid(self):
        """Test extracting project name from valid titles"""
        test_cases = [
            ("Construction: Deck Repair", "deck-repair"),
            ("Construction: Kitchen Remodel Project", "kitchen-remodel-project"),
            ("Construction: Front_Yard Fence", "front-yard-fence"),
        ]

        for title, expected in test_cases:
            with self.subTest(title=title):
                result = ProjectExtractor.extract_from_title(title)
                self.assertEqual(result, expected)

    def test_get_branch_name(self):
        """Test generating branch names"""
        result = ProjectExtractor.get_branch_name("deck-repair", "2025-01")
        self.assertEqual(result, "project/2025-01-deck-repair")


class TestGitOperations(unittest.TestCase):
    """Test git operations"""

    def setUp(self):
        """Set up test fixtures"""
        self.git_patcher = patch("subprocess.run")
        self.mock_subprocess = self.git_patcher.start()
        self.mock_subprocess.return_value.returncode = 0
        self.mock_subprocess.return_value.stdout = ""

        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures"""
        self.git_patcher.stop()
        shutil.rmtree(self.temp_dir)

    def test_create_new_branch(self):
        """Test creating a new branch"""

        def mock_subprocess_side_effect(cmd, **kwargs):
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""

            if "branch --list" in " ".join(cmd):
                mock_result.stdout = ""  # Branch doesn't exist locally
            elif "ls-remote" in " ".join(cmd):
                mock_result.stdout = ""  # Branch doesn't exist remotely

            return mock_result

        self.mock_subprocess.side_effect = mock_subprocess_side_effect

        result = GitOperations.create_or_switch_branch("project/2025-01-test")

        self.assertTrue(result)

        # Verify git commands were called
        expected_calls = [
            (["git", "branch", "--list", "project/2025-01-test"],),
            (["git", "ls-remote", "--heads", "origin", "project/2025-01-test"],),
            (["git", "checkout", "main"],),
            (["git", "pull", "origin", "main"],),
            (["git", "checkout", "-b", "project/2025-01-test"],),
        ]

        for expected_call in expected_calls:
            self.assertIn(expected_call, [call[0] for call in self.mock_subprocess.call_args_list])

    def test_switch_to_existing_branch(self):
        """Test switching to existing local branch"""

        def mock_subprocess_side_effect(cmd, **kwargs):
            mock_result = Mock()
            mock_result.returncode = 0

            if "branch --list" in " ".join(cmd):
                mock_result.stdout = "project/2025-01-test"  # Branch exists locally
            else:
                mock_result.stdout = ""

            return mock_result

        self.mock_subprocess.side_effect = mock_subprocess_side_effect

        result = GitOperations.create_or_switch_branch("project/2025-01-test")

        self.assertTrue(result)

        # Should checkout existing branch
        checkout_calls = [call for call in self.mock_subprocess.call_args_list if "checkout" in str(call)]
        self.assertTrue(any("project/2025-01-test" in str(call) for call in checkout_calls))

    def test_commit_changes(self):
        """Test committing changes"""
        project_dir = self.temp_path / "test_project"
        project_dir.mkdir()

        result = GitOperations.commit_changes(project_dir, "Test commit message")

        # Verify that the method succeeds (indicates git commands were called)
        # The mock subprocess returns success, so if the result is True,
        # it means the git commands were attempted
        self.assertTrue(result)


class TestGitHubManager(unittest.TestCase):
    """Test GitHub API operations"""

    def setUp(self):
        """Set up test fixtures"""
        self.github = GitHubManager("fake_token", "test_owner", "test_repo")

    @patch("requests.request")
    def test_create_issue_success(self, mock_request):
        """Test successful issue creation"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "number": 42,
            "title": "Construction Project: Test Project",
            "html_url": "https://github.com/test_owner/test_repo/issues/42",
        }
        mock_request.return_value = mock_response

        issue = self.github.create_issue("test-project", "Test Project", "http://example.com")

        self.assertIsNotNone(issue)
        self.assertEqual(issue["number"], 42)

    @patch("requests.request")
    def test_find_existing_issue_success(self, mock_request):
        """Test finding existing GitHub issue"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"number": 42, "title": "Construction Project: Test Project"}, {"number": 43, "title": "Other Issue"}]
        mock_request.return_value = mock_response

        result = self.github.find_existing_issue("test-project")

        self.assertIsNotNone(result)
        self.assertEqual(result["number"], 42)
        self.assertEqual(result["title"], "Construction Project: Test Project")

    @patch("requests.request")
    def test_find_existing_issue_not_found(self, mock_request):
        """Test when no existing GitHub issue is found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"number": 43, "title": "Other Issue"}]
        mock_request.return_value = mock_response

        result = self.github.find_existing_issue("test-project")

        self.assertIsNone(result)

        # Verify API call
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "GET")
        self.assertIn("issues", args[1])

    @patch("requests.request")
    def test_add_issue_comment_success(self, mock_request):
        """Test successful issue comment addition"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123}
        mock_request.return_value = mock_response

        self.github.add_issue_comment(42, "test-project", 5, 2)

        # Verify API call
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "POST")
        self.assertIn("issues/42/comments", args[1])
        self.assertIn("2 new photos", kwargs["json"]["body"])

    @patch("requests.request")
    def test_api_request_failure(self, mock_request):
        """Test API request failure handling"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_request.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.github._api_request("GET", "test")

        self.assertIn("GitHub API error: 400 - Bad Request", str(context.exception))


class TestProjectStateManager(unittest.TestCase):
    """Test project state management"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.state_file = self.temp_path / "test-state.json"
        self.state_manager = ProjectStateManager(self.state_file)

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)

    def test_load_empty_state(self):
        """Test loading state when no state file exists"""
        state = self.state_manager.load_state()

        expected = {"projects": {}, "last_scan": None}
        self.assertEqual(state, expected)

    def test_save_and_load_state(self):
        """Test saving and loading state"""
        test_state = {
            "projects": {
                "test-project": {
                    "project_id": "album123",
                    "issue_number": 42,
                    "images": {"hash1": {"image_id": "img1"}},
                }
            },
            "last_scan": "2025-01-15T10:00:00Z",
        }

        self.state_manager.save_state(test_state)
        loaded_state = self.state_manager.load_state()

        self.assertEqual(loaded_state, test_state)
        self.assertTrue(self.state_file.exists())


class TestConstructionWorkflow(unittest.TestCase):
    """Test complete workflow orchestration"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.state_file = self.temp_path / "workflow-state.json"

        # Mock dependencies
        self.photo_client = MockPhotoClient()
        self.project_hasher = MockProjectHasher()

        # Setup workflow
        self.workflow = ConstructionWorkflow(
            photo_client=self.photo_client,
            project_hasher=self.project_hasher,
            github_token="fake_token",
            repo_owner="test_owner",
            repo_name="test_repo",
            state_file=self.state_file,
        )

        # Mock git operations
        self.git_patcher = patch("subprocess.run")
        self.mock_subprocess = self.git_patcher.start()
        self.mock_subprocess.return_value.returncode = 0
        self.mock_subprocess.return_value.stdout = ""

    def tearDown(self):
        """Clean up test fixtures"""
        self.git_patcher.stop()
        shutil.rmtree(self.temp_dir)

    @patch("scripts.workflows.construction_workflow.GitHubManager.create_issue")
    @patch("scripts.workflows.construction_workflow.GitHubManager.add_issue_comment")
    def test_workflow_new_project(self, mock_add_comment, mock_create_issue):
        """Test workflow with new project"""
        # Setup mock data
        mock_create_issue.return_value = {"number": 42}

        self.photo_client.projects = [
            {
                "id": "album123",
                "title": "Test Project",
                "project_name": "test-project",
                "url": "http://example.com",
                "tags": ["project:test_project"],
                "image_count": 2,
            }
        ]

        self.photo_client.images["album123"] = [
            {
                "id": "img1",
                "title": "First Image",
                "url": "http://example.com/img1.jpg",
                "filename": "001_first.jpg",
                "metadata": {},
            },
            {
                "id": "img2",
                "title": "Second Image",
                "url": "http://example.com/img2.jpg",
                "filename": "002_second.jpg",
                "metadata": {},
            },
        ]

        # Run workflow
        result = self.workflow.run()

        self.assertTrue(result)

        # Verify issue was created
        mock_create_issue.assert_called_once()

        # Verify comment was added
        mock_add_comment.assert_called_once()

        # Verify state was saved
        state = self.workflow.state_manager.load_state()
        self.assertIn("test-project", state["projects"])
        self.assertEqual(state["projects"]["test-project"]["issue_number"], 42)

    @patch("scripts.workflows.construction_workflow.GitHubManager.add_issue_comment")
    def test_workflow_existing_project_no_new_images(self, mock_add_comment):
        """Test workflow with existing project and no new images"""
        # Setup existing state
        existing_state = {
            "projects": {
                "test-project": {
                    "project_id": "album123",
                    "issue_number": 42,
                    "images": {"image_hash_img1": {"image_id": "img1"}},
                }
            },
            "last_scan": "2025-01-15T09:00:00Z",
        }
        self.workflow.state_manager.save_state(existing_state)

        # Setup mock data (same images as existing state)
        self.photo_client.projects = [
            {
                "id": "album123",
                "title": "Test Project",
                "project_name": "test-project",
                "url": "http://example.com",
                "tags": ["project:test_project"],
                "image_count": 1,
            }
        ]

        self.photo_client.images["album123"] = [
            {
                "id": "img1",
                "title": "First Image",
                "url": "http://example.com/img1.jpg",
                "filename": "001_first.jpg",
                "metadata": {},
            }
        ]

        # Run workflow
        result = self.workflow.run()

        self.assertTrue(result)

        # Verify no comment was added (no new images)
        mock_add_comment.assert_not_called()

    def test_workflow_authentication_failure(self):
        """Test workflow when photo client authentication fails"""
        self.photo_client.authenticated = False

        result = self.workflow.run()

        self.assertFalse(result)

    def test_sync_project_photos_with_new_images(self):
        """Test syncing photos when new images are available"""
        # Setup mock photo client with new images
        mock_client = MockPhotoClient()
        mock_hasher = MockProjectHasher()

        workflow = ConstructionWorkflow(mock_client, mock_hasher, "test_token", "owner", "repo", Path("/tmp/test_state.json"))

        # Setup project data
        project = {"id": "project123", "project_name": "deck-repair", "title": "Deck Repair Project", "url": "http://example.com/album"}

        # Setup new images in mock client
        mock_client.images["project123"] = [
            {
                "id": "img1",
                "title": "Before photo",
                "url": "http://example.com/img1.jpg",
                "filename": "before.jpg",
                "metadata": {"date": "2025-08-07"},
            },
            {
                "id": "img2",
                "title": "During photo",
                "url": "http://example.com/img2.jpg",
                "filename": "during.jpg",
                "metadata": {"date": "2025-08-07"},
            },
        ]

        # Test with no existing images
        existing_images = {}

        with patch("scripts.workflows.construction_workflow.GitOperations") as mock_git, patch(
            "scripts.workflows.construction_workflow.Path.mkdir"
        ) as mock_mkdir, patch("builtins.open", mock_open()) as mock_file:
            mock_git.create_or_switch_branch.return_value = True
            mock_git.commit_changes.return_value = True

            new_images, total_count = workflow.sync_project_photos(project, existing_images)

            # Verify results
            self.assertEqual(len(new_images), 2)
            self.assertEqual(total_count, 2)

            # Verify git operations were called
            mock_git.create_or_switch_branch.assert_called_once()
            mock_git.commit_changes.assert_called_once()

    def test_sync_project_photos_no_new_images(self):
        """Test syncing photos when no new images are available"""
        mock_client = MockPhotoClient()
        mock_hasher = MockProjectHasher()

        workflow = ConstructionWorkflow(mock_client, mock_hasher, "test_token", "owner", "repo", Path("/tmp/test_state.json"))

        project = {"id": "project123", "project_name": "deck-repair", "title": "Deck Repair Project"}

        # Setup existing images that match current images
        mock_client.images["project123"] = [
            {
                "id": "img1",
                "title": "Before photo",
                "url": "http://example.com/img1.jpg",
                "filename": "before.jpg",
                "metadata": {"date": "2025-08-07"},
            }
        ]

        # All images already exist (use the actual hash format from MockProjectHasher)
        existing_images = {"image_hash_img1": {"id": "img1"}}

        new_images, total_count = workflow.sync_project_photos(project, existing_images)

        # Should return no new images but correct total count
        self.assertEqual(len(new_images), 0)
        self.assertEqual(total_count, 1)

    def test_sync_project_photos_no_images_in_service(self):
        """Test syncing when photo service has no images"""
        mock_client = MockPhotoClient()
        mock_hasher = MockProjectHasher()

        workflow = ConstructionWorkflow(mock_client, mock_hasher, "test_token", "owner", "repo", Path("/tmp/test_state.json"))

        project = {"id": "project123", "project_name": "deck-repair", "title": "Deck Repair Project"}

        # No images in photo service
        mock_client.images["project123"] = []
        existing_images = {}

        new_images, total_count = workflow.sync_project_photos(project, existing_images)

        self.assertEqual(len(new_images), 0)
        self.assertEqual(total_count, 0)

    def test_setup_project_issue_creates_new_issue(self):
        """Test project issue setup when no existing issue exists"""
        mock_client = MockPhotoClient()
        mock_hasher = MockProjectHasher()

        workflow = ConstructionWorkflow(mock_client, mock_hasher, "test_token", "owner", "repo", Path("/tmp/test_state.json"))

        with patch.object(workflow.github, "find_existing_issue", return_value=None), patch.object(
            workflow.github, "create_issue", return_value={"number": 42}
        ):
            issue_number = workflow._setup_project_issue("deck-repair", "Deck Repair", "http://example.com")

            self.assertEqual(issue_number, 42)
            workflow.github.create_issue.assert_called_once()

    def test_setup_project_issue_uses_existing_issue(self):
        """Test project issue setup when existing issue is found"""
        mock_client = MockPhotoClient()
        mock_hasher = MockProjectHasher()

        workflow = ConstructionWorkflow(mock_client, mock_hasher, "test_token", "owner", "repo", Path("/tmp/test_state.json"))

        existing_issue = {"number": 123, "title": "Construction Project: Deck Repair"}

        with patch.object(workflow.github, "find_existing_issue", return_value=existing_issue), patch.object(
            workflow.github, "create_issue"
        ) as mock_create:
            issue_number = workflow._setup_project_issue("deck-repair", "Deck Repair", "http://example.com")

            self.assertEqual(issue_number, 123)
            # Should not create new issue since existing one was found
            mock_create.assert_not_called()

    def test_setup_project_issue_handles_permission_errors(self):
        """Test project issue setup with permission errors"""
        mock_client = MockPhotoClient()
        mock_hasher = MockProjectHasher()

        workflow = ConstructionWorkflow(mock_client, mock_hasher, "test_token", "owner", "repo", Path("/tmp/test_state.json"))

        # Both finding and creating issues fail due to permissions
        with patch.object(workflow.github, "find_existing_issue", side_effect=PermissionError("403")), patch.object(
            workflow.github, "create_issue", side_effect=PermissionError("403")
        ):
            issue_number = workflow._setup_project_issue("deck-repair", "Deck Repair", "http://example.com")

            # Should gracefully handle permission errors and return None
            self.assertIsNone(issue_number)

    def test_process_project_new_project_initialization(self):
        """Test processing a completely new project"""
        mock_client = MockPhotoClient()
        mock_hasher = MockProjectHasher()

        workflow = ConstructionWorkflow(mock_client, mock_hasher, "test_token", "owner", "repo", Path("/tmp/test_state.json"))

        project = {"id": "project123", "project_name": "deck-repair", "title": "Deck Repair Project", "url": "http://example.com/album"}

        # Empty initial state
        state = {"projects": {}, "last_scan": None}

        with patch.object(workflow, "_setup_project_issue", return_value=42):
            project_state = workflow._process_project(project, state)

            # _process_project returns the individual project state, not full state
            # But it also modifies the passed-in state object
            self.assertIn("deck-repair", state["projects"])

            self.assertEqual(project_state["project_id"], "project123")
            self.assertEqual(project_state["project_title"], "Deck Repair Project")
            self.assertEqual(project_state["issue_number"], 42)
            self.assertIn("branch_name", project_state)
            self.assertIn("created_at", project_state)
            # Images might be populated by sync_project_photos, so just verify it exists
            self.assertIn("images", project_state)

    def test_github_manager_issue_body_formatting(self):
        """Test that GitHub issue body contains proper project information"""
        github = GitHubManager("test_token", "owner", "repo")

        with patch.object(github, "_api_request", return_value={"number": 42}) as mock_request:
            github.create_issue("deck-repair", "Deck Repair Project", "http://example.com")

            # Verify the issue body contains expected elements
            call_args = mock_request.call_args[0][2]
            body = call_args["body"]

            self.assertIn("Construction Project: Deck Repair Project", body)
            self.assertIn("project/", body)  # Branch name
            self.assertIn("project:deck_repair", body)  # Tag format
            self.assertIn("[Deck Repair Project](http://example.com)", body)  # Album link
            self.assertIn("Photo sync enabled", body)

    def test_github_manager_comment_formatting_new_photos(self):
        """Test comment formatting when new photos are synced"""
        github = GitHubManager("test_token", "owner", "repo")

        with patch.object(github, "_api_request") as mock_request:
            github.add_issue_comment(42, "kitchen-renovation", 15, 5)

            call_args = mock_request.call_args[0][2]
            body = call_args["body"]

            self.assertIn("5 new photos", body)
            self.assertIn("Total photos**: 15", body)
            self.assertIn("project/", body)  # Branch reference
            self.assertIn("Photos have been committed", body)

    def test_github_manager_comment_formatting_no_new_photos(self):
        """Test comment formatting when no new photos are found"""
        github = GitHubManager("test_token", "owner", "repo")

        with patch.object(github, "_api_request") as mock_request:
            github.add_issue_comment(42, "bathroom-remodel", 8, 0)

            call_args = mock_request.call_args[0][2]
            body = call_args["body"]

            self.assertIn("No new photos found", body)
            self.assertIn("Total photos**: 8", body)
            self.assertIn("Next sync**: In ~1 hour", body)

    def test_project_state_manager_directory_creation(self):
        """Test that state manager creates parent directories"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Deep nested path that doesn't exist
            state_file = Path(temp_dir) / "nested" / "deep" / "state.json"
            manager = ProjectStateManager(state_file)

            test_state = {"projects": {}, "last_scan": "2025-08-07T10:00:00"}

            # Should create parent directories
            manager.save_state(test_state)

            # Verify file was created and directories exist
            self.assertTrue(state_file.exists())
            self.assertTrue(state_file.parent.exists())

            # Verify content is correct
            loaded_state = manager.load_state()
            self.assertEqual(loaded_state, test_state)

    def test_sync_photos_skips_images_without_url(self):
        """Test that photo sync skips images that have no URL"""
        mock_client = MockPhotoClient()
        mock_hasher = MockProjectHasher()

        workflow = ConstructionWorkflow(mock_client, mock_hasher, "test_token", "owner", "repo", Path("/tmp/test_state.json"))

        project = {"id": "project123", "project_name": "deck-repair", "title": "Deck Repair Project"}

        # Mix of images with and without URLs
        mock_client.images["project123"] = [
            {"id": "img1", "title": "Good photo", "url": "http://example.com/img1.jpg", "filename": "good.jpg", "metadata": {}},
            {
                "id": "img2",
                "title": "Bad photo",
                "url": "",  # No URL
                "filename": "bad.jpg",
                "metadata": {},
            },
            {"id": "img3", "title": "Another good photo", "url": "http://example.com/img3.jpg", "filename": "good2.jpg", "metadata": {}},
        ]

        with patch("scripts.workflows.construction_workflow.GitOperations") as mock_git, patch(
            "scripts.workflows.construction_workflow.Path.mkdir"
        ), patch("builtins.open", mock_open()):
            mock_git.create_or_switch_branch.return_value = True
            mock_git.commit_changes.return_value = True

            # Track download calls to verify only images with URLs are downloaded
            download_calls = []
            original_download = mock_client.download_image

            def track_downloads(*args, **kwargs):
                download_calls.append(args)
                return original_download(*args, **kwargs)

            mock_client.download_image = track_downloads

            workflow.sync_project_photos(project, {})

            # Should only download images with valid URLs (img1 and img3)
            self.assertEqual(len(download_calls), 2)
            downloaded_urls = [call[0] for call in download_calls]
            self.assertIn("http://example.com/img1.jpg", downloaded_urls)
            self.assertIn("http://example.com/img3.jpg", downloaded_urls)


if __name__ == "__main__":
    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        TestProjectExtractor,
        TestGitOperations,
        TestGitHubManager,
        TestProjectStateManager,
        TestConstructionWorkflow,
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)
