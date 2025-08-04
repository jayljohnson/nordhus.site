#!/usr/bin/env python3
"""
Tests for Cloudinary client implementation
"""

import os

# Add scripts to path for imports
import sys
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from clients.cloudinary_client import CloudinaryClient
from clients.cloudinary_client import CloudinaryHasher


@pytest.fixture
def mock_cloudinary_config():
    """Mock Cloudinary configuration"""
    with patch("clients.cloudinary_client.cloudinary") as mock_cloudinary:
        # Mock config object
        mock_config = Mock()
        mock_config.cloud_name = "test-cloud"
        mock_config.api_key = "test-key"
        mock_config.api_secret = "test-secret"

        mock_cloudinary.config.return_value = mock_config
        yield mock_cloudinary


@pytest.fixture
def cloudinary_client(mock_cloudinary_config):
    """Create a Cloudinary client for testing"""
    with patch.dict(os.environ, {"CLOUDINARY_URL": "cloudinary://test-key:test-secret@test-cloud"}):
        return CloudinaryClient()


class TestCloudinaryClient:
    """Test Cloudinary client functionality"""

    def test_init_with_env_url(self, mock_cloudinary_config):
        """Test initialization with CLOUDINARY_URL"""
        with patch.dict(os.environ, {"CLOUDINARY_URL": "cloudinary://key:secret@cloud"}):
            client = CloudinaryClient()
            assert client.cloud_name == "test-cloud"

    def test_init_missing_credentials(self):
        """Test initialization fails without credentials"""
        # Mock config to return empty values
        with patch("clients.cloudinary_client.cloudinary") as mock_cloudinary:
            mock_config = Mock()
            mock_config.cloud_name = None
            mock_config.api_key = None
            mock_config.api_secret = None
            mock_cloudinary.config.return_value = mock_config

            with pytest.raises(ValueError, match="Missing Cloudinary credentials"):
                CloudinaryClient()

    def test_authenticate_success(self, cloudinary_client, mock_cloudinary_config):
        """Test successful authentication"""
        # Mock successful API call
        mock_cloudinary_config.api.resources.return_value = {"resources": []}

        assert cloudinary_client.authenticate() is True

    def test_authenticate_failure(self, cloudinary_client, mock_cloudinary_config):
        """Test authentication failure"""
        # Mock API call that raises exception
        mock_cloudinary_config.api.resources.side_effect = Exception("Auth failed")

        assert cloudinary_client.authenticate() is False

    def test_get_construction_projects(self, cloudinary_client, mock_cloudinary_config):
        """Test getting construction projects from folders"""
        # Mock folder listing
        mock_cloudinary_config.api.root_folders.return_value = {
            "folders": [
                {"name": "test-construction-project"},
                {"name": "2025-08-02-deck-repair"},
                {"name": "vacation-photos"},  # Should be ignored
                {"name": "project-workshop-insulation"},
            ]
        }

        # Mock resource count calls
        mock_cloudinary_config.api.resources.return_value = {"total_count": 5}

        projects = cloudinary_client.get_construction_projects()

        # Should find 3 construction projects
        assert len(projects) == 3

        # Check project extraction
        project_names = [p["project_name"] for p in projects]
        assert "test-construction-project" in project_names
        assert "deck-repair" in project_names
        assert "workshop-insulation" in project_names

    def test_get_project_images(self, cloudinary_client, mock_cloudinary_config):
        """Test getting images from a project folder"""
        # Mock resources API call
        mock_cloudinary_config.api.resources.return_value = {
            "resources": [
                {
                    "public_id": "test-project/IMG001",
                    "secure_url": "https://res.cloudinary.com/test/image/upload/test-project/IMG001.jpg",
                    "format": "jpg",
                    "bytes": 12345,
                    "width": 1920,
                    "height": 1080,
                    "created_at": "2025-01-01T12:00:00Z",
                },
                {
                    "public_id": "test-project/IMG002",
                    "secure_url": "https://res.cloudinary.com/test/image/upload/test-project/IMG002.png",
                    "format": "png",
                    "bytes": 54321,
                    "width": 1280,
                    "height": 720,
                    "created_at": "2025-01-01T13:00:00Z",
                },
            ]
        }

        images = cloudinary_client.get_project_images("test-project")

        assert len(images) == 2

        # Check first image
        img1 = images[0]
        assert img1["id"] == "test-project/IMG001"
        assert img1["filename"] == "001_IMG001.jpg"
        assert img1["url"] == "https://res.cloudinary.com/test/image/upload/test-project/IMG001.jpg"
        assert img1["metadata"]["size"] == 12345
        assert img1["metadata"]["width"] == 1920

    @patch("clients.cloudinary_client.requests.get")
    @patch("clients.cloudinary_client.os.makedirs")
    @patch("builtins.open", create=True)
    def test_download_image(self, mock_open, mock_makedirs, mock_requests, cloudinary_client):
        """Test downloading an image"""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock file operations
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Test download
        result = cloudinary_client.download_image("https://example.com/image.jpg", "/tmp/downloads", "test.jpg")

        # Verify result
        assert result == Path("/tmp/downloads/test.jpg")
        mock_makedirs.assert_called_once_with("/tmp/downloads", exist_ok=True)
        mock_file.write.assert_called_once_with(b"fake image data")

    def test_upload_image(self, cloudinary_client, mock_cloudinary_config):
        """Test uploading an image"""
        # Mock successful upload
        mock_cloudinary_config.uploader.upload.return_value = {
            "public_id": "test-folder/uploaded-image",
            "secure_url": "https://res.cloudinary.com/test/image/upload/test-folder/uploaded-image.jpg",
        }

        # Create a temporary test file
        test_file = Path("test_upload.jpg")
        test_file.write_bytes(b"fake image")

        try:
            result = cloudinary_client.upload_image(str(test_file), folder="test-folder")

            assert result is not None
            assert result["public_id"] == "test-folder/uploaded-image"

            # Verify upload was called with correct parameters
            mock_cloudinary_config.uploader.upload.assert_called_once()
            call_args = mock_cloudinary_config.uploader.upload.call_args
            assert call_args[1]["folder"] == "test-folder"
            assert call_args[1]["use_filename"] is True

        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()


class TestCloudinaryHasher:
    """Test Cloudinary hasher functionality"""

    def test_generate_project_hash(self):
        """Test project hash generation"""
        hasher = CloudinaryHasher()

        project = {"id": "test-project", "title": "Test Project", "image_count": 5}

        hash1 = hasher.generate_project_hash(project)
        hash2 = hasher.generate_project_hash(project)

        # Same project should generate same hash
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hash length

        # Different project should generate different hash
        project["image_count"] = 6
        hash3 = hasher.generate_project_hash(project)
        assert hash1 != hash3

    def test_generate_image_hash(self):
        """Test image hash generation"""
        hasher = CloudinaryHasher()

        image = {"id": "test-project/image1", "url": "https://example.com/image1.jpg", "metadata": {"datetime": "2025-01-01T12:00:00Z"}}

        hash1 = hasher.generate_image_hash(image)
        hash2 = hasher.generate_image_hash(image)

        # Same image should generate same hash
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hash length

        # Different image should generate different hash
        image["url"] = "https://example.com/image2.jpg"
        hash3 = hasher.generate_image_hash(image)
        assert hash1 != hash3


class TestProjectExtraction:
    """Test project name extraction from folder names"""

    def test_extract_project_from_folder(self):
        """Test various folder name patterns"""
        from clients.cloudinary_client import CloudinaryClient

        # Create client with mocked config
        with patch("clients.cloudinary_client.cloudinary") as mock_cloudinary:
            mock_config = Mock()
            mock_config.cloud_name = "test"
            mock_config.api_key = "test"
            mock_config.api_secret = "test"
            mock_cloudinary.config.return_value = mock_config

            client = CloudinaryClient()

            # Test different patterns
            assert client._extract_project_from_folder("project-deck-repair") == "deck-repair"
            assert client._extract_project_from_folder("2025-08-02-workshop-insulation") == "workshop-insulation"
            assert client._extract_project_from_folder("test-construction-project") == "test-construction-project"
            assert client._extract_project_from_folder("vacation-photos") is None
            assert client._extract_project_from_folder("my-project-folder") == "my-project-folder"
