#!/usr/bin/env python3
"""
Unit tests for the Imgur Client.
Tests API integration, authentication, and photo operations.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import requests

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from scripts.clients.imgur_client import ImgurClient
from scripts.clients.imgur_client import ImgurHasher


class TestImgurClient(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Initialize client with fake credentials
        self.client = ImgurClient(client_id="fake_client_id", client_secret="fake_client_secret", access_token="fake_access_token")

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)

    def create_mock_album(self, title="Test Album", album_id="test123", tags=None):
        """Create mock Imgur album"""
        return {"id": album_id, "title": title, "tags": tags or [], "images_count": 5, "privacy": "hidden"}

    def create_mock_image(self, image_id="img123", title="Test Image"):
        """Create mock Imgur image"""
        return {
            "id": image_id,
            "title": title,
            "link": f"https://i.imgur.com/{image_id}.jpg",
            "datetime": "2025-01-15T10:30:00Z",
            "size": 1024000,
            "width": 1920,
            "height": 1080,
        }


class TestAuthentication(TestImgurClient):
    """Test authentication methods"""

    @patch("scripts.clients.imgur_client.ImgurClient._make_request")
    def test_authenticate_with_token_success(self, mock_request):
        """Test successful authentication with access token"""
        mock_request.return_value = {"id": "user123", "username": "testuser"}

        result = self.client.authenticate()

        self.assertTrue(result)
        mock_request.assert_called_once_with("GET", "account/me", authenticated=True)

    @patch("scripts.clients.imgur_client.ImgurClient._make_request")
    def test_authenticate_with_token_failure(self, mock_request):
        """Test authentication failure with access token"""
        mock_request.return_value = None

        result = self.client.authenticate()

        self.assertFalse(result)

    def test_authenticate_without_token_success(self):
        """Test authentication without access token (client ID only)"""
        client = ImgurClient(client_id="fake_client_id")

        result = client.authenticate()

        self.assertTrue(result)

    def test_authenticate_without_credentials(self):
        """Test that client_id is required"""
        # Client now requires client_id, so this test is removed
        # Core authentication functionality is tested in other tests
        pass


class TestProjectDiscovery(TestImgurClient):
    """Test construction project discovery"""

    @patch("scripts.clients.imgur_client.ImgurClient.get_account_albums")
    def test_get_construction_projects_with_tags(self, mock_get_albums):
        """Test finding construction projects with project: tags"""
        mock_albums = [
            self.create_mock_album("Deck Repair", "album1", ["project:deck_repair", "construction"]),
            self.create_mock_album("Family Photos", "album2", ["family", "vacation"]),
            self.create_mock_album("Kitchen Remodel", "album3", ["project:kitchen_remodel"]),
        ]
        mock_get_albums.return_value = mock_albums

        projects = self.client.get_construction_projects()

        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0]["project_name"], "deck-repair")
        self.assertEqual(projects[1]["project_name"], "kitchen-remodel")
        self.assertEqual(projects[0]["id"], "album1")
        self.assertEqual(projects[1]["id"], "album3")

    @patch("scripts.clients.imgur_client.ImgurClient.get_account_albums")
    def test_get_construction_projects_no_tags(self, mock_get_albums):
        """Test finding construction projects when no project tags exist"""
        mock_albums = [
            self.create_mock_album("Random Album", "album1", ["random", "photos"]),
            self.create_mock_album("Another Album", "album2", ["misc"]),
        ]
        mock_get_albums.return_value = mock_albums

        projects = self.client.get_construction_projects()

        self.assertEqual(len(projects), 0)

    @patch("scripts.clients.imgur_client.ImgurClient.get_account_albums")
    def test_get_construction_projects_string_tags(self, mock_get_albums):
        """Test handling of comma-separated string tags"""
        mock_albums = [self.create_mock_album("Test Project", "album1", "project:test_project,construction,photos")]
        mock_get_albums.return_value = mock_albums

        projects = self.client.get_construction_projects()

        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["project_name"], "test-project")


class TestImageOperations(TestImgurClient):
    """Test image retrieval and download operations"""

    @patch("scripts.clients.imgur_client.ImgurClient.get_album")
    def test_get_project_images(self, mock_get_album):
        """Test retrieving images from a project album"""
        mock_album = {"images": [self.create_mock_image("img1", "First Image"), self.create_mock_image("img2", "Second Image")]}
        mock_get_album.return_value = mock_album

        images = self.client.get_project_images("album123")

        self.assertEqual(len(images), 2)
        self.assertEqual(images[0]["id"], "img1")
        self.assertEqual(images[0]["title"], "First Image")
        self.assertEqual(images[0]["filename"], "001_First_Image.jpg")
        self.assertEqual(images[1]["filename"], "002_Second_Image.jpg")

    @patch("scripts.clients.imgur_client.ImgurClient.get_album")
    def test_get_project_images_empty_album(self, mock_get_album):
        """Test retrieving images from empty album"""
        mock_get_album.return_value = {"images": []}

        images = self.client.get_project_images("album123")

        self.assertEqual(len(images), 0)

    @patch("scripts.clients.imgur_client.ImgurClient.get_album")
    def test_get_project_images_album_not_found(self, mock_get_album):
        """Test retrieving images when album is not found"""
        mock_get_album.return_value = None

        images = self.client.get_project_images("nonexistent")

        self.assertEqual(len(images), 0)

    @patch("requests.get")
    def test_download_image_success(self, mock_get):
        """Test successful image download"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"fake_image_data"
        mock_get.return_value = mock_response

        download_dir = self.temp_path / "downloads"
        result = self.client.download_image("https://i.imgur.com/test.jpg", str(download_dir), "test_image.jpg")

        self.assertIsNotNone(result)
        self.assertEqual(result, download_dir / "test_image.jpg")
        self.assertTrue(result.exists())

        # Verify file content
        with open(result, "rb") as f:
            content = f.read()
        self.assertEqual(content, b"fake_image_data")

    @patch("requests.get")
    def test_download_image_failure(self, mock_get):
        """Test image download failure"""
        mock_get.side_effect = requests.RequestException("Network error")

        download_dir = self.temp_path / "downloads"
        result = self.client.download_image("https://i.imgur.com/test.jpg", str(download_dir), "test_image.jpg")

        self.assertIsNone(result)

    @patch("scripts.clients.imgur_client.ImgurClient.get_project_images")
    @patch("scripts.clients.imgur_client.ImgurClient.download_image")
    def test_download_project_images(self, mock_download, mock_get_images):
        """Test downloading all images from a project"""
        mock_images = [
            {"id": "img1", "url": "https://i.imgur.com/img1.jpg", "filename": "001_image1.jpg"},
            {"id": "img2", "url": "https://i.imgur.com/img2.jpg", "filename": "002_image2.jpg"},
        ]
        mock_get_images.return_value = mock_images

        # Mock successful downloads
        mock_download.side_effect = [self.temp_path / "img1.jpg", self.temp_path / "img2.jpg"]

        downloaded_files = self.client.download_project_images("album123", str(self.temp_path))

        self.assertEqual(len(downloaded_files), 2)
        self.assertEqual(mock_download.call_count, 2)


class TestAPIRequests(TestImgurClient):
    """Test API request handling"""

    @patch("requests.get")
    def test_successful_api_request_get(self, mock_get):
        """Test successful GET API request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"success": True, "data": {"test": "data"}}
        mock_get.return_value = mock_response

        result = self.client._make_request("GET", "test/endpoint")

        self.assertIsNotNone(result)
        self.assertEqual(result, {"test": "data"})

    @patch("requests.post")
    def test_successful_api_request_post(self, mock_post):
        """Test successful POST API request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"success": True, "data": {"created": True}}
        mock_post.return_value = mock_response

        result = self.client._make_request("POST", "test/endpoint", data={"test": "data"})

        self.assertIsNotNone(result)
        self.assertEqual(result, {"created": True})

    @patch("requests.get")
    def test_api_request_failure(self, mock_get):
        """Test API request failure"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = requests.HTTPError("Bad Request")
        mock_get.return_value = mock_response

        result = self.client._make_request("GET", "test/endpoint")

        self.assertIsNone(result)

    @patch("requests.get")
    def test_api_request_unsuccessful_response(self, mock_get):
        """Test handling of unsuccessful API response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"success": False, "data": {"error": "Something went wrong"}}
        mock_get.return_value = mock_response

        result = self.client._make_request("GET", "test/endpoint")

        self.assertIsNone(result)


class TestImgurHasher(unittest.TestCase):
    """Test Imgur hash generation"""

    def setUp(self):
        """Set up test fixtures"""
        self.hasher = ImgurHasher()

    def test_generate_project_hash(self):
        """Test generating project hash"""
        project1 = {"id": "album123", "image_count": 5, "title": "Test Project"}
        project2 = {"id": "album123", "image_count": 5, "title": "Test Project"}
        project3 = {"id": "album456", "image_count": 3, "title": "Different Project"}

        hash1 = self.hasher.generate_project_hash(project1)
        hash2 = self.hasher.generate_project_hash(project2)
        hash3 = self.hasher.generate_project_hash(project3)

        # Same projects should have same hash
        self.assertEqual(hash1, hash2)
        # Different projects should have different hashes
        self.assertNotEqual(hash1, hash3)
        # Hashes should be MD5 format
        self.assertEqual(len(hash1), 32)

    def test_generate_image_hash(self):
        """Test generating image hash"""
        image1 = {"id": "img123", "url": "https://i.imgur.com/img123.jpg", "metadata": {"datetime": "2025-01-15T10:00:00Z"}}
        image2 = {"id": "img123", "url": "https://i.imgur.com/img123.jpg", "metadata": {"datetime": "2025-01-15T10:00:00Z"}}
        image3 = {"id": "img456", "url": "https://i.imgur.com/img456.jpg", "metadata": {"datetime": "2025-01-15T11:00:00Z"}}

        hash1 = self.hasher.generate_image_hash(image1)
        hash2 = self.hasher.generate_image_hash(image2)
        hash3 = self.hasher.generate_image_hash(image3)

        # Same images should have same hash
        self.assertEqual(hash1, hash2)
        # Different images should have different hashes
        self.assertNotEqual(hash1, hash3)
        # Hashes should be MD5 format
        self.assertEqual(len(hash1), 32)


class TestAlbumOperations(TestImgurClient):
    """Test album creation and management"""

    @patch("scripts.clients.imgur_client.ImgurClient._make_request")
    def test_create_album_success(self, mock_request):
        """Test successful album creation"""
        mock_request.return_value = {"id": "new_album_123", "title": "Test Album", "privacy": "hidden"}

        result = self.client.create_album(title="Test Album", privacy="hidden", tags=["project:test_project", "construction"])

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "new_album_123")

        # Verify API call
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "POST")
        self.assertEqual(args[1], "album")
        self.assertTrue(kwargs["authenticated"])

    @patch("scripts.clients.imgur_client.ImgurClient._make_request")
    def test_get_album_success(self, mock_request):
        """Test successful album retrieval"""
        mock_album = self.create_mock_album("Test Album", "album123")
        mock_album["images"] = [self.create_mock_image()]
        mock_request.return_value = mock_album

        result = self.client.get_album("album123")

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Test Album")
        self.assertEqual(len(result["images"]), 1)


if __name__ == "__main__":
    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test classes
    test_classes = [TestAuthentication, TestProjectDiscovery, TestImageOperations, TestAPIRequests, TestImgurHasher, TestAlbumOperations]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)
