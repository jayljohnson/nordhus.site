#!/usr/bin/env python3
"""
Unit tests for the photo client interface module.
Tests abstract base classes and utility functions.
"""

import os
import sys
import unittest
from unittest.mock import Mock
from unittest.mock import patch

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from scripts.interfaces.photo_client_interface import PhotoClient
from scripts.interfaces.photo_client_interface import ProjectExtractor
from scripts.interfaces.photo_client_interface import ProjectHasher


class ConcretePhotoClient(PhotoClient):
    """Concrete implementation for testing abstract methods"""

    def authenticate(self) -> bool:
        return True

    def get_construction_projects(self):
        return []

    def get_project_images(self, project_id: str):
        return []

    def download_image(self, image_url: str, download_dir: str, filename: str):
        return None

    def download_project_images(self, project_id: str, download_dir: str):
        return []


class ConcreteProjectHasher(ProjectHasher):
    """Concrete implementation for testing abstract methods"""

    def generate_project_hash(self, project):
        return "test_hash"

    def generate_image_hash(self, image):
        return "test_hash"


class TestPhotoClientInterface(unittest.TestCase):
    """Test the PhotoClient abstract base class"""

    def test_abstract_methods_can_be_implemented(self):
        """Test that abstract methods can be implemented"""
        client = ConcretePhotoClient()

        # Test all abstract methods can be called
        self.assertTrue(client.authenticate())
        self.assertEqual(client.get_construction_projects(), [])
        self.assertEqual(client.get_project_images("test"), [])
        self.assertIsNone(client.download_image("url", "dir", "file"))
        self.assertEqual(client.download_project_images("test", "dir"), [])

    def test_abstract_methods_coverage(self):
        """Test abstract method pass statements for coverage"""
        # This test covers the pass statements in abstract methods
        with self.assertRaises(TypeError):
            # Cannot instantiate abstract class
            PhotoClient()

    def test_abstract_method_signatures(self):
        """Test that abstract methods have the right signatures"""
        # This forces coverage of abstract method definitions

        # Check PhotoClient abstract methods
        self.assertTrue(hasattr(PhotoClient, "authenticate"))
        self.assertTrue(hasattr(PhotoClient, "get_construction_projects"))
        self.assertTrue(hasattr(PhotoClient, "get_project_images"))
        self.assertTrue(hasattr(PhotoClient, "download_image"))
        self.assertTrue(hasattr(PhotoClient, "download_project_images"))

        # Verify they are abstract
        self.assertTrue(getattr(PhotoClient.authenticate, "__isabstractmethod__", False))
        self.assertTrue(getattr(PhotoClient.get_construction_projects, "__isabstractmethod__", False))
        self.assertTrue(getattr(PhotoClient.get_project_images, "__isabstractmethod__", False))
        self.assertTrue(getattr(PhotoClient.download_image, "__isabstractmethod__", False))
        self.assertTrue(getattr(PhotoClient.download_project_images, "__isabstractmethod__", False))


class TestProjectHasherInterface(unittest.TestCase):
    """Test the ProjectHasher abstract base class"""

    def test_abstract_methods_can_be_implemented(self):
        """Test that abstract methods can be implemented"""
        hasher = ConcreteProjectHasher()

        # Test all abstract methods can be called
        self.assertEqual(hasher.generate_project_hash({}), "test_hash")
        self.assertEqual(hasher.generate_image_hash({}), "test_hash")

    def test_abstract_methods_coverage(self):
        """Test abstract method pass statements for coverage"""
        # This test covers the pass statements in abstract methods
        with self.assertRaises(TypeError):
            # Cannot instantiate abstract class
            ProjectHasher()

    def test_abstract_method_signatures(self):
        """Test that abstract methods have the right signatures"""
        # Check ProjectHasher abstract methods
        self.assertTrue(hasattr(ProjectHasher, "generate_project_hash"))
        self.assertTrue(hasattr(ProjectHasher, "generate_image_hash"))

        # Verify they are abstract
        self.assertTrue(getattr(ProjectHasher.generate_project_hash, "__isabstractmethod__", False))
        self.assertTrue(getattr(ProjectHasher.generate_image_hash, "__isabstractmethod__", False))


class TestProjectExtractor(unittest.TestCase):
    """Test the ProjectExtractor utility class"""

    def test_extract_from_tag_valid(self):
        """Test extracting project name from valid tag"""
        result = ProjectExtractor.extract_from_tag("project:deck_repair")
        self.assertEqual(result, "deck-repair")

    def test_extract_from_tag_with_spaces(self):
        """Test extracting project name from tag with spaces"""
        result = ProjectExtractor.extract_from_tag("project:Deck Repair")
        self.assertEqual(result, "deck-repair")

    def test_extract_from_tag_with_special_chars(self):
        """Test extracting project name from tag with special characters"""
        result = ProjectExtractor.extract_from_tag("project:deck@repair#2024")
        self.assertEqual(result, "deckrepair2024")

    def test_extract_from_tag_invalid_prefix(self):
        """Test extracting project name from tag with invalid prefix"""
        result = ProjectExtractor.extract_from_tag("invalid:deck_repair")
        self.assertIsNone(result)

    def test_extract_from_tag_empty_name(self):
        """Test extracting project name from tag with empty name"""
        result = ProjectExtractor.extract_from_tag("project:")
        self.assertIsNone(result)

    def test_extract_from_tag_custom_prefix(self):
        """Test extracting project name with custom prefix"""
        result = ProjectExtractor.extract_from_tag("custom:deck_repair", prefix="custom:")
        self.assertEqual(result, "deck-repair")

    def test_extract_from_title_valid(self):
        """Test extracting project name from valid title"""
        result = ProjectExtractor.extract_from_title("Construction: Deck Repair")
        self.assertEqual(result, "deck-repair")

    def test_extract_from_title_with_underscores(self):
        """Test extracting project name from title with underscores"""
        result = ProjectExtractor.extract_from_title("Construction: deck_repair_2024")
        self.assertEqual(result, "deck-repair-2024")

    def test_extract_from_title_invalid_prefix(self):
        """Test extracting project name from title with invalid prefix"""
        result = ProjectExtractor.extract_from_title("Invalid: Deck Repair")
        self.assertIsNone(result)

    def test_extract_from_title_empty_name(self):
        """Test extracting project name from title with empty name"""
        result = ProjectExtractor.extract_from_title("Construction:")
        self.assertIsNone(result)

    def test_extract_from_title_custom_prefix(self):
        """Test extracting project name from title with custom prefix"""
        result = ProjectExtractor.extract_from_title("Custom: Deck Repair", prefix="Custom:")
        self.assertEqual(result, "deck-repair")

    def test_get_branch_name_with_date_prefix(self):
        """Test generating branch name with provided date prefix"""
        result = ProjectExtractor.get_branch_name("deck-repair", "2025-08-07")
        self.assertEqual(result, "project/2025-08-07-deck-repair")

    @patch("datetime.datetime")
    def test_get_branch_name_without_date_prefix(self, mock_datetime):
        """Test generating branch name without date prefix (uses current date)"""
        # Mock datetime.now() to return our test date
        mock_now = Mock()
        mock_now.strftime.return_value = "2025-08-07"
        mock_datetime.now.return_value = mock_now

        result = ProjectExtractor.get_branch_name("deck-repair")
        self.assertEqual(result, "project/2025-08-07-deck-repair")
        mock_datetime.now.assert_called_once()


if __name__ == "__main__":
    unittest.main()
