#!/usr/bin/env python3
"""
Simplified Construction Project Manager
Maps Cloudinary folder names directly to project names and feature branches.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List
from typing import Optional

from clients.cloudinary_client import CloudinaryClient
from utils.config import Config
from utils.git_operations import GitOperations
from utils.logging import logger


class SimpleProjectManager:
    """Simplified project manager focused on core workflow"""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.date_prefix = datetime.now().strftime("%Y-%m-%d")

    @property
    def project_directory(self) -> Path:
        """Project assets directory: assets/images/YYYY-MM-DD-project-name/"""
        return Path(f"assets/images/{self.date_prefix}-{self.project_name}")

    @property
    def blog_post_path(self) -> Path:
        """Blog post path: _posts/YYYY-MM-DD-project-name.md"""
        return Path(f"_posts/{self.date_prefix}-{self.project_name.replace('_', '-')}.md")

    @property
    def feature_branch(self) -> str:
        """Feature branch: project/YYYY-MM-DD-project-name"""
        return f"project/{self.date_prefix}-{self.project_name}"

    def create_project_branch(self) -> bool:
        """Create and switch to project feature branch"""
        return GitOperations.create_or_switch_branch(self.feature_branch)

    def sync_photos_from_cloudinary(self) -> int:
        """
        Sync photos from Cloudinary folder to project directory.
        Returns number of new photos downloaded.
        Uses Cloudinary tags to track download state.
        """
        if not Config.is_photo_monitoring_enabled():
            logger.info("Photo monitoring disabled")
            return 0

        try:
            client = CloudinaryClient()

            # Cloudinary folder name becomes the project name
            folder_name = self.project_name

            logger.info(f"Syncing photos from Cloudinary folder: {folder_name}")

            # Download photos, marking them as downloaded with tags
            downloaded_files = client.download_folder_photos(
                folder_name,
                str(self.project_directory),
                tag_downloaded=True,  # Tag photos as downloaded in Cloudinary
            )

            new_photo_count = len(downloaded_files)

            if new_photo_count > 0:
                logger.info(f"Downloaded {new_photo_count} new photos")

                # Create simple project metadata
                self._update_project_metadata(new_photo_count)

                # Commit new photos
                commit_msg = f"Sync {new_photo_count} new photos: {self.project_name}"
                if not GitOperations.commit_changes(self.project_directory, commit_msg):
                    logger.error("Failed to commit new photos")
                    return 0

                logger.success(f"Committed {new_photo_count} new photos to {self.feature_branch}")
            else:
                logger.info("No new photos to sync")

            return new_photo_count

        except Exception as e:
            logger.error(f"Photo sync failed: {e}")
            return 0

    def _update_project_metadata(self, new_photo_count: int):
        """Update simple project metadata"""
        self.project_directory.mkdir(parents=True, exist_ok=True)

        metadata_file = self.project_directory / "project.json"

        # Load existing or create new metadata
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
        else:
            metadata = {"project_name": self.project_name, "created_date": self.date_prefix, "total_photos": 0}

        # Update with sync info
        metadata["total_photos"] = metadata.get("total_photos", 0) + new_photo_count
        metadata["last_sync"] = datetime.now().isoformat()

        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def generate_blog_post(self) -> Optional[Path]:
        """Generate blog post from project photos"""
        if not self.project_directory.exists():
            logger.error(f"Project directory not found: {self.project_directory}")
            return None

        # Count photos
        photo_files = self._get_photo_files()
        if not photo_files:
            logger.warning("No photos found for blog post")

        # Generate blog post content
        blog_content = self._create_blog_content(photo_files)

        # Write blog post
        self.blog_post_path.parent.mkdir(exist_ok=True)
        with open(self.blog_post_path, "w") as f:
            f.write(blog_content)

        logger.success(f"Generated blog post: {self.blog_post_path}")
        return self.blog_post_path

    def _get_photo_files(self) -> List[Path]:
        """Get all photo files in project directory"""
        photo_files = []
        if self.project_directory.exists():
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
                photo_files.extend(list(self.project_directory.glob(ext)))
        return sorted(photo_files)

    def _create_blog_content(self, photo_files: List[Path]) -> str:
        """Create blog post content"""
        title = self.project_name.replace("-", " ").replace("_", " ").title()

        content = f"""---
title: "{title}"
date: {self.date_prefix}
categories: [construction, projects]
---

# {title}

Construction project documented with {len(photo_files)} photos.

## Photos

"""

        # Add photo references
        for photo in photo_files:
            content += f"![{photo.stem}](/{self.project_directory}/{photo.name})\n\n"

        content += """## Summary

Project documentation generated automatically from field photos.

*Generated by Simple Project Manager*
"""

        return content


# Legacy API for backward compatibility
def get_project_dir(project_name: str) -> Path:
    """Legacy function - get project directory"""
    return SimpleProjectManager(project_name).project_directory


def get_project_branch(project_name: str) -> str:
    """Legacy function - get project branch"""
    return SimpleProjectManager(project_name).feature_branch


def create_project_branch(project_name: str) -> str:
    """Legacy function - create project branch"""
    manager = SimpleProjectManager(project_name)
    if manager.create_project_branch():
        return manager.feature_branch
    return None


def setup_project_directory(project_name: str) -> Path:
    """Legacy function - setup project directory"""
    manager = SimpleProjectManager(project_name)
    manager.project_directory.mkdir(parents=True, exist_ok=True)
    manager._update_project_metadata(0)
    return manager.project_directory


def start_project(project_name: str) -> bool:
    """Start new project with feature branch and directory setup"""
    if not re.match(r"^[a-zA-Z0-9-_]+$", project_name):
        logger.error("Project name can only contain letters, numbers, hyphens, and underscores")
        return False

    manager = SimpleProjectManager(project_name)

    # Create feature branch
    if not manager.create_project_branch():
        logger.error("Failed to create project branch")
        return False

    # Create project directory with initial metadata
    manager.project_directory.mkdir(parents=True, exist_ok=True)
    manager._update_project_metadata(0)

    # Initial commit
    commit_msg = f"Start project: {project_name}"
    if not GitOperations.commit_changes(manager.project_directory, commit_msg):
        logger.error("Failed to commit initial project setup")
        return False

    logger.success(f"Project started: {project_name}")
    logger.info(f"Branch: {manager.feature_branch}")
    logger.info(f"Directory: {manager.project_directory}")
    logger.info(f"Add photos to Cloudinary folder: {project_name}")

    return True


def add_photos(project_name: str) -> bool:
    """Sync photos from Cloudinary for existing project"""
    manager = SimpleProjectManager(project_name)

    if not manager.project_directory.exists():
        logger.error(f"Project {project_name} not found. Run 'make start-project PROJECT={project_name}' first.")
        return False

    # Switch to project branch
    if not GitOperations.checkout_branch(manager.feature_branch):
        logger.error(f"Could not switch to branch {manager.feature_branch}")
        return False

    # Sync photos
    new_count = manager.sync_photos_from_cloudinary()

    if new_count > 0:
        logger.success(f"Synced {new_count} new photos for {project_name}")
    else:
        logger.info(f"No new photos found for {project_name}")

    return True


def finish_project(project_name: str) -> bool:
    """Generate blog post and prepare for PR"""
    manager = SimpleProjectManager(project_name)

    if not manager.project_directory.exists():
        logger.error(f"Project {project_name} not found")
        return False

    # Switch to project branch
    if not GitOperations.checkout_branch(manager.feature_branch):
        logger.error(f"Could not switch to branch {manager.feature_branch}")
        return False

    # Generate blog post
    blog_post = manager.generate_blog_post()
    if not blog_post:
        logger.error("Failed to generate blog post")
        return False

    # Commit blog post
    commit_msg = f"Complete project: {project_name} - add blog post"
    files_to_commit = [blog_post, manager.project_directory]

    if not GitOperations.add_and_commit_files(files_to_commit, commit_msg):
        logger.error("Failed to commit blog post")
        return False

    logger.success("Project completed! Blog post generated and committed.")
    logger.info(f"Create PR to merge {manager.feature_branch} to main")

    return True


def main():
    """CLI entry point"""
    if len(sys.argv) < 3:
        print("Usage: python3 project_manager.py {start|add-photos|finish} <project-name>")
        sys.exit(1)

    command = sys.argv[1]
    project_name = sys.argv[2]

    if command == "start":
        success = start_project(project_name)
    elif command == "add-photos":
        success = add_photos(project_name)
    elif command == "finish":
        success = finish_project(project_name)
    else:
        print(f"Unknown command: {command}")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
