#!/usr/bin/env python3
"""
Abstract interface for photo client implementations.
Provides a consistent API for different photo services (Imgur, etc.)
"""

from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional


class PhotoClient(ABC):
    """Abstract base class for photo service clients"""

    @abstractmethod
    def authenticate(self) -> bool:
        """Test authentication and return success status"""
        pass

    @abstractmethod
    def get_construction_projects(self) -> List[Dict[str, Any]]:
        """Get all albums/collections tagged as construction projects

        Returns:
            List of project dictionaries with keys:
            - id: Unique identifier for the album/collection
            - title: Human-readable title
            - project_name: Extracted project name for git branching
            - url: Public URL to the album (if available)
            - tags: List of tags associated with the project
            - image_count: Number of images in the project
        """
        pass

    @abstractmethod
    def get_project_images(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all images from a specific project

        Args:
            project_id: Unique identifier for the project

        Returns:
            List of image dictionaries with keys:
            - id: Unique identifier for the image
            - title: Image title/description
            - url: Download URL for the image
            - filename: Suggested filename for download
            - metadata: Additional metadata (creation date, etc.)
        """
        pass

    @abstractmethod
    def download_image(self, image_url: str, download_dir: str, filename: str) -> Optional[Path]:
        """Download an image to local directory

        Args:
            image_url: Direct URL to the image
            download_dir: Local directory to save the image
            filename: Local filename to save as

        Returns:
            Path to downloaded file, or None if failed
        """
        pass

    @abstractmethod
    def download_project_images(self, project_id: str, download_dir: str) -> List[Path]:
        """Download all images from a project

        Args:
            project_id: Unique identifier for the project
            download_dir: Local directory to save images

        Returns:
            List of paths to downloaded files
        """
        pass


class ProjectHasher(ABC):
    """Abstract base class for generating consistent hashes for change detection"""

    @abstractmethod
    def generate_project_hash(self, project: Dict[str, Any]) -> str:
        """Generate a hash for a project to detect changes"""
        pass

    @abstractmethod
    def generate_image_hash(self, image: Dict[str, Any]) -> str:
        """Generate a hash for an image to detect changes"""
        pass


class ProjectExtractor:
    """Utility class for extracting project names from various formats"""

    @staticmethod
    def extract_from_tag(tag: str, prefix: str = "project:") -> Optional[str]:
        """Extract project name from a tag like 'project:deck_repair'"""
        if tag.startswith(prefix):
            project_name = tag[len(prefix) :].strip()
            # Convert to valid branch name
            project_name = project_name.lower().replace(" ", "-").replace("_", "-")
            # Remove special characters
            project_name = "".join(c for c in project_name if c.isalnum() or c in "-")
            return project_name if project_name else None
        return None

    @staticmethod
    def extract_from_title(title: str, prefix: str = "Construction:") -> Optional[str]:
        """Extract project name from a title like 'Construction: Deck Repair'"""
        if title.startswith(prefix):
            project_name = title[len(prefix) :].strip()
            # Convert to valid branch name
            project_name = project_name.lower().replace(" ", "-").replace("_", "-")
            # Remove special characters
            project_name = "".join(c for c in project_name if c.isalnum() or c in "-")
            return project_name if project_name else None
        return None

    @staticmethod
    def get_branch_name(project_name: str, date_prefix: str = None) -> str:
        """Generate branch name for project"""
        if not date_prefix:
            from datetime import datetime

            date_prefix = datetime.now().strftime("%Y-%m-%d")
        return f"project/{date_prefix}-{project_name}"
