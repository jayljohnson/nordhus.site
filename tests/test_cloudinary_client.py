#!/usr/bin/env python3
"""
Tests for Cloudinary client implementation
"""

import os

# Add scripts to path for imports
import sys
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import requests

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


class TestDownloadFolderPhotos:
    """Test download_folder_photos method with comprehensive business logic"""

    @pytest.fixture
    def client_with_mocked_cloudinary(self):
        """Create client with fully mocked Cloudinary"""
        with patch("clients.cloudinary_client.cloudinary") as mock_cloudinary:
            mock_config = Mock()
            mock_config.cloud_name = "test"
            mock_config.api_key = "test"
            mock_config.api_secret = "test"
            mock_cloudinary.config.return_value = mock_config

            with patch.dict(os.environ, {"CLOUDINARY_URL": "cloudinary://key:secret@cloud"}):
                client = CloudinaryClient()
                yield client, mock_cloudinary

    @patch("clients.cloudinary_client.requests.get")
    @patch("clients.cloudinary_client.os.makedirs")
    @patch("builtins.open")
    def test_download_folder_photos_basic_success(self, mock_open, mock_makedirs, mock_requests, client_with_mocked_cloudinary):
        """Test successful photo download from folder"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        # Mock API response with resources
        mock_cloudinary.api.resources.return_value = {
            "resources": [
                {"public_id": "test-folder/image1", "secure_url": "https://cloudinary.com/image1.jpg", "format": "jpg", "tags": []},
                {"public_id": "test-folder/image2", "secure_url": "https://cloudinary.com/image2.png", "format": "png", "tags": []},
            ]
        }

        # Mock successful HTTP responses
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock file operations
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        result = client.download_folder_photos("test-folder", "/tmp/downloads")

        assert len(result) == 2
        assert all(isinstance(p, Path) for p in result)
        assert str(result[0]) == "/tmp/downloads/image1.jpg"
        assert str(result[1]) == "/tmp/downloads/image2.png"

        # Verify API calls
        mock_cloudinary.api.resources.assert_called_once()
        assert mock_requests.call_count == 2
        mock_makedirs.assert_called_once_with("/tmp/downloads", exist_ok=True)

    @patch("clients.cloudinary_client.requests.get")
    @patch("clients.cloudinary_client.os.makedirs")
    @patch("builtins.open")
    def test_download_folder_photos_with_tagging(self, mock_open, mock_makedirs, mock_requests, client_with_mocked_cloudinary):
        """Test photo download with tagging enabled"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        # Mock resources - one already downloaded, one new
        mock_cloudinary.api.resources.return_value = {
            "resources": [
                {
                    "public_id": "folder/downloaded_image",
                    "secure_url": "https://cloudinary.com/downloaded.jpg",
                    "format": "jpg",
                    "tags": ["downloaded"],  # Already tagged
                },
                {
                    "public_id": "folder/new_image",
                    "secure_url": "https://cloudinary.com/new.jpg",
                    "format": "jpg",
                    "tags": [],  # Not tagged yet
                },
            ]
        }

        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"fake image"
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock file operations
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        result = client.download_folder_photos("folder", "/tmp", tag_downloaded=True)

        # Should only download 1 image (the untagged one)
        assert len(result) == 1
        assert str(result[0]) == "/tmp/new_image.jpg"

        # Should attempt to tag the downloaded image
        mock_cloudinary.uploader.add_tag.assert_called_once_with("downloaded", "folder/new_image")

    def test_download_folder_photos_no_resources(self, client_with_mocked_cloudinary):
        """Test download when folder has no resources"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        mock_cloudinary.api.resources.return_value = {"resources": []}

        result = client.download_folder_photos("empty-folder", "/tmp")

        assert result == []

    @patch("clients.cloudinary_client.os.makedirs")
    def test_download_folder_photos_api_failure(self, mock_makedirs, client_with_mocked_cloudinary):
        """Test download when Cloudinary API fails"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        mock_cloudinary.api.resources.side_effect = Exception("API Error")

        result = client.download_folder_photos("failing-folder", "/tmp")

        assert result == []

    @patch("clients.cloudinary_client.requests.get")
    @patch("clients.cloudinary_client.os.makedirs")
    @patch("builtins.open")
    def test_download_folder_photos_filename_collision_handling(self, mock_open, mock_makedirs, mock_requests, client_with_mocked_cloudinary):
        """Test handling of filename collisions"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        mock_cloudinary.api.resources.return_value = {
            "resources": [{"public_id": "folder/image", "secure_url": "https://cloudinary.com/image.jpg", "format": "jpg", "tags": []}]
        }

        mock_response = Mock()
        mock_response.content = b"fake image"
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock Path.exists to simulate existing file for first attempt
        with patch.object(Path, "exists") as mock_exists:
            mock_exists.side_effect = [True, False]  # First exists, second doesn't

            result = client.download_folder_photos("folder", "/tmp")

            assert len(result) == 1
            assert str(result[0]) == "/tmp/image_1.jpg"  # Should append _1

    @patch("clients.cloudinary_client.requests.get")
    @patch("clients.cloudinary_client.os.makedirs")
    @patch("builtins.open")
    def test_download_folder_photos_download_error_handling(self, mock_open, mock_makedirs, mock_requests, client_with_mocked_cloudinary):
        """Test handling of individual download failures"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        mock_cloudinary.api.resources.return_value = {
            "resources": [
                {"public_id": "folder/good_image", "secure_url": "https://cloudinary.com/good.jpg", "format": "jpg", "tags": []},
                {"public_id": "folder/bad_image", "secure_url": "https://cloudinary.com/bad.jpg", "format": "jpg", "tags": []},
            ]
        }

        # First request succeeds, second fails
        def mock_get_side_effect(url):
            if "good.jpg" in url:
                mock_response = Mock()
                mock_response.content = b"good image"
                mock_response.raise_for_status.return_value = None
                return mock_response
            else:
                raise requests.RequestException("Download failed")

        mock_requests.side_effect = mock_get_side_effect

        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        result = client.download_folder_photos("folder", "/tmp")

        # Should successfully download only the good image
        assert len(result) == 1
        assert str(result[0]) == "/tmp/good_image.jpg"

    @patch("clients.cloudinary_client.requests.get")
    @patch("clients.cloudinary_client.os.makedirs")
    @patch("builtins.open")
    def test_download_folder_photos_tagging_error_handling(self, mock_open, mock_makedirs, mock_requests, client_with_mocked_cloudinary):
        """Test handling of tagging errors during download"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        mock_cloudinary.api.resources.return_value = {
            "resources": [{"public_id": "folder/image", "secure_url": "https://cloudinary.com/image.jpg", "format": "jpg", "tags": []}]
        }

        # Mock successful download but failed tagging
        mock_response = Mock()
        mock_response.content = b"image data"
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock tagging failure
        mock_cloudinary.uploader.add_tag.side_effect = Exception("Tagging failed")

        result = client.download_folder_photos("folder", "/tmp", tag_downloaded=True)

        # Download should still succeed despite tagging failure
        assert len(result) == 1
        assert str(result[0]) == "/tmp/image.jpg"

    @patch("clients.cloudinary_client.os.makedirs")
    def test_download_folder_photos_empty_filename_handling(self, mock_makedirs, client_with_mocked_cloudinary):
        """Test handling of resources with empty/missing filename parts"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        mock_cloudinary.api.resources.return_value = {
            "resources": [
                {
                    "public_id": "folder/",  # Empty filename part
                    "secure_url": "https://cloudinary.com/empty.jpg",
                    "format": "jpg",
                    "tags": [],
                }
            ]
        }

        with patch("clients.cloudinary_client.requests.get") as mock_requests, patch("builtins.open") as mock_open:
            mock_response = Mock()
            mock_response.content = b"image"
            mock_response.raise_for_status.return_value = None
            mock_requests.return_value = mock_response

            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            result = client.download_folder_photos("folder", "/tmp")

            # Should generate default filename
            assert len(result) == 1
            assert str(result[0]) == "/tmp/image_1.jpg"


class TestCreateFolder:
    """Test folder creation functionality"""

    @pytest.fixture
    def client_with_mocked_cloudinary(self):
        """Create client with mocked Cloudinary"""
        with patch("clients.cloudinary_client.cloudinary") as mock_cloudinary:
            mock_config = Mock()
            mock_config.cloud_name = "test"
            mock_config.api_key = "test"
            mock_config.api_secret = "test"
            mock_cloudinary.config.return_value = mock_config

            with patch.dict(os.environ, {"CLOUDINARY_URL": "cloudinary://key:secret@cloud"}):
                client = CloudinaryClient()
                yield client, mock_cloudinary

    def test_create_folder_success(self, client_with_mocked_cloudinary):
        """Test successful folder creation"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        # Mock successful upload
        mock_cloudinary.uploader.upload.return_value = {"public_id": "test-folder/.placeholder"}

        result = client.create_folder("test-folder", "Test Description")

        assert result is not None
        assert result["id"] == "test-folder"
        assert result["name"] == "test-folder"

        # Verify upload was called with correct parameters
        mock_cloudinary.uploader.upload.assert_called_once()
        call_args = mock_cloudinary.uploader.upload.call_args
        assert call_args[1]["folder"] == "test-folder"
        assert call_args[1]["public_id"] == "test-folder/.placeholder"
        assert call_args[1]["resource_type"] == "raw"

    def test_create_folder_failure(self, client_with_mocked_cloudinary):
        """Test folder creation failure"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        # Mock upload failure
        mock_cloudinary.uploader.upload.side_effect = Exception("Upload failed")

        result = client.create_folder("failing-folder")

        assert result is None


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases in existing methods"""

    @pytest.fixture
    def client_with_mocked_cloudinary(self):
        with patch("clients.cloudinary_client.cloudinary") as mock_cloudinary:
            mock_config = Mock()
            mock_config.cloud_name = "test"
            mock_config.api_key = "test"
            mock_config.api_secret = "test"
            mock_cloudinary.config.return_value = mock_config

            with patch.dict(os.environ, {"CLOUDINARY_URL": "cloudinary://key:secret@cloud"}):
                client = CloudinaryClient()
                yield client, mock_cloudinary

    def test_get_construction_projects_resource_count_failure(self, client_with_mocked_cloudinary):
        """Test handling of resource count failures in get_construction_projects"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        # Mock folder listing success but resource count failure
        mock_cloudinary.api.root_folders.return_value = {"folders": [{"name": "project-test"}]}
        mock_cloudinary.api.resources.side_effect = Exception("Resource count failed")

        projects = client.get_construction_projects()

        assert len(projects) == 1
        assert projects[0]["image_count"] == 0  # Should default to 0 on failure

    def test_get_project_images_datetime_parsing_error(self, client_with_mocked_cloudinary):
        """Test datetime parsing error handling in get_project_images"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        mock_cloudinary.api.resources.return_value = {
            "resources": [
                {
                    "public_id": "test/image",
                    "secure_url": "https://test.com/image.jpg",
                    "format": "jpg",
                    "created_at": "invalid-date-format",  # Invalid date
                    "bytes": 1000,
                    "width": 100,
                    "height": 100,
                }
            ]
        }

        images = client.get_project_images("test")

        assert len(images) == 1
        assert images[0]["metadata"]["datetime"] is None  # Should be None on parse error

    def test_get_project_images_missing_created_at(self, client_with_mocked_cloudinary):
        """Test handling of missing created_at field"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        mock_cloudinary.api.resources.return_value = {
            "resources": [
                {
                    "public_id": "test/image",
                    "secure_url": "https://test.com/image.jpg",
                    "format": "jpg",
                    # created_at field missing
                    "bytes": 1000,
                }
            ]
        }

        images = client.get_project_images("test")

        assert len(images) == 1
        assert images[0]["metadata"]["datetime"] is None

    @patch("clients.cloudinary_client.requests.get")
    def test_download_image_no_filename_provided(self, mock_requests, client_with_mocked_cloudinary):
        """Test download_image when no filename is provided"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        mock_response = Mock()
        mock_response.content = b"image data"
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        with patch("clients.cloudinary_client.os.makedirs") as mock_makedirs, patch("builtins.open") as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            # Test URL without extension
            result = client.download_image("https://test.com/image_id", "/tmp", "")
            assert str(result) == "/tmp/image_id.jpg"  # Should add default .jpg extension

            # Test URL with extension in path
            result2 = client.download_image("https://test.com/path/image.png", "/tmp", "")
            assert str(result2) == "/tmp/image.png"

    @patch("clients.cloudinary_client.requests.get")
    def test_download_image_request_failure(self, mock_requests, client_with_mocked_cloudinary):
        """Test download_image when HTTP request fails"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        mock_requests.side_effect = requests.RequestException("Network error")

        result = client.download_image("https://test.com/image.jpg", "/tmp", "test.jpg")

        assert result is None

    def test_upload_image_file_not_found(self, client_with_mocked_cloudinary):
        """Test upload_image when file doesn't exist"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        result = client.upload_image("/nonexistent/path.jpg")

        assert result is None

    def test_upload_image_upload_failure(self, client_with_mocked_cloudinary):
        """Test upload_image when Cloudinary upload fails"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        # Create a temporary test file
        test_file = Path("test_upload_fail.jpg")
        test_file.write_bytes(b"fake image")

        try:
            mock_cloudinary.uploader.upload.side_effect = Exception("Upload failed")

            result = client.upload_image(str(test_file))

            assert result is None

        finally:
            if test_file.exists():
                test_file.unlink()

    def test_upload_image_with_title_context(self, client_with_mocked_cloudinary):
        """Test upload_image with title context"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        mock_cloudinary.uploader.upload.return_value = {"public_id": "folder/image", "secure_url": "https://test.com/image.jpg"}

        test_file = Path("test_context.jpg")
        test_file.write_bytes(b"fake image")

        try:
            result = client.upload_image(str(test_file), folder="test-folder", title="Test Image")

            assert result is not None

            # Verify context was set
            call_args = mock_cloudinary.uploader.upload.call_args
            assert call_args[1]["context"] == "title=Test Image"
            assert call_args[1]["folder"] == "test-folder"

        finally:
            if test_file.exists():
                test_file.unlink()


class TestInitializationEdgeCases:
    """Test initialization with various credential scenarios"""

    @patch("clients.cloudinary_client.os.getenv")
    def test_init_with_env_fallback(self, mock_getenv):
        """Test initialization falls back to os.getenv"""
        mock_getenv.return_value = "cloudinary://key:secret@cloud"

        with patch("clients.cloudinary_client.cloudinary") as mock_cloudinary:
            # First config call returns empty, second returns proper config
            mock_config_empty = Mock()
            mock_config_empty.cloud_name = None
            mock_config_empty.api_key = None
            mock_config_empty.api_secret = None

            mock_config_full = Mock()
            mock_config_full.cloud_name = "cloud"
            mock_config_full.api_key = "key"
            mock_config_full.api_secret = "secret"

            mock_cloudinary.config.side_effect = [mock_config_empty, mock_config_full]

            client = CloudinaryClient()
            assert client.cloud_name == "cloud"

    def test_init_custom_cloudinary_url(self):
        """Test initialization with custom cloudinary_url parameter"""
        with patch("clients.cloudinary_client.cloudinary") as mock_cloudinary:
            mock_config = Mock()
            mock_config.cloud_name = "custom-cloud"
            mock_config.api_key = "custom-key"
            mock_config.api_secret = "custom-secret"
            mock_cloudinary.config.return_value = mock_config

            client = CloudinaryClient(cloudinary_url="cloudinary://custom-key:custom-secret@custom-cloud")

            assert client.cloud_name == "custom-cloud"
            # Verify environment was set
            assert os.environ.get("CLOUDINARY_URL") == "cloudinary://custom-key:custom-secret@custom-cloud"


class TestAdditionalBusinessLogic:
    """Test additional business logic to improve coverage"""

    @pytest.fixture
    def client_with_mocked_cloudinary(self):
        with patch("clients.cloudinary_client.cloudinary") as mock_cloudinary:
            mock_config = Mock()
            mock_config.cloud_name = "test"
            mock_config.api_key = "test"
            mock_config.api_secret = "test"
            mock_cloudinary.config.return_value = mock_config

            with patch.dict(os.environ, {"CLOUDINARY_URL": "cloudinary://key:secret@cloud"}):
                client = CloudinaryClient()
                yield client, mock_cloudinary

    def test_download_project_images_method(self, client_with_mocked_cloudinary):
        """Test download_project_images method as part of business logic coverage"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        # Mock get_project_images to return test data
        with patch.object(client, "get_project_images") as mock_get_images, patch.object(client, "download_image") as mock_download:
            mock_get_images.return_value = [
                {"url": "https://test.com/img1.jpg", "filename": "img1.jpg"},
                {"url": "https://test.com/img2.jpg", "filename": "img2.jpg"},
                {"url": "", "filename": "no_url.jpg"},  # Test empty URL handling
            ]

            mock_download.return_value = Path("/tmp/downloaded.jpg")

            result = client.download_project_images("test-project", "/tmp/downloads")

            # Should download 2 images (skip the one with empty URL)
            assert len(result) == 2
            assert mock_download.call_count == 2

    def test_pattern_matching_edge_cases(self, client_with_mocked_cloudinary):
        """Test edge cases in project name extraction patterns"""
        client, mock_cloudinary = client_with_mocked_cloudinary

        # Test various edge cases for project extraction
        test_cases = [
            ("construction-deck-repair", "construction-deck-repair"),  # contains construction
            ("My-Project-Name", "My-Project-Name"),  # contains project (case preserved)
            ("regular-folder", None),  # doesn't match patterns
            ("project-", ""),  # edge case with empty suffix
            ("2025-01-01-", None),  # edge case - date pattern needs content after dash
            ("weekend-project", "weekend-project"),  # contains project
        ]

        for folder_name, expected in test_cases:
            result = client._extract_project_from_folder(folder_name)
            assert result == expected, f"Failed for {folder_name}: got {result}, expected {expected}"
