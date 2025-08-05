#!/usr/bin/env python3
"""
Mobile Construction Project Manager
Handles photo organization, branch creation, and blog post generation for
construction projects.
"""

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from clients.cloudinary_client import CloudinaryClient
from utils.config import Config
from utils.git_operations import GitOperations
from utils.logging import logger


class ProjectManager:
    """Domain object for managing construction project lifecycle and paths"""

    def __init__(self, project_name: str, date_prefix: Optional[str] = None):
        self.project_name = project_name
        self.date_prefix = date_prefix or datetime.now().strftime("%Y-%m-%d")

    @property
    def project_directory(self) -> Path:
        """Project domain: Where project images and metadata live"""
        return Path(f"assets/images/{self.date_prefix}-{self.project_name}")

    @property
    def metadata_file(self) -> Path:
        """Project domain: Project metadata location"""
        return self.project_directory / "project.json"

    @property
    def blog_post_path(self) -> Path:
        """Project domain: Generated blog post location"""
        return Path(f"_posts/{self.date_prefix}-{self.project_name.replace('_', '-')}.md")

    @property
    def git_branch(self) -> str:
        """Delegate to git domain for branch naming"""
        return GitOperations.get_project_branch(self.project_name, self.date_prefix)


# Legacy functions for backward compatibility
def get_project_dir(project_name):
    """Legacy function - use ProjectManager.project_directory instead"""
    return ProjectManager(project_name).project_directory


def get_project_branch(project_name):
    """Legacy function - use ProjectManager.git_branch instead"""
    return ProjectManager(project_name).git_branch


def create_project_branch(project_name):
    """Create and switch to project branch"""
    project = ProjectManager(project_name)
    if GitOperations.create_or_switch_branch(project.git_branch):
        return project.git_branch
    return None


def setup_project_directory(project_name):
    """Create project directory structure"""
    project = ProjectManager(project_name)
    project.project_directory.mkdir(parents=True, exist_ok=True)

    # Create project metadata file
    metadata = {
        "project_name": project_name,
        "start_date": datetime.now().isoformat(),
        "photos": [],
        "status": "active",
    }

    with open(project.metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Created project directory: {project.project_directory}")
    return project.project_directory


def start_project(project_name):
    """Start a new construction project"""
    logger.info(f"Starting project: {project_name}")

    # Validate project name
    if not re.match(r"^[a-zA-Z0-9-_]+$", project_name):
        logger.error("Project name can only contain letters, numbers, hyphens, and underscores")
        return False

    # Create branch
    branch = create_project_branch(project_name)
    if not branch:
        return False

    # Setup directory
    project_dir = setup_project_directory(project_name)

    # Create photo album (if enabled)
    if Config.is_photo_monitoring_enabled():
        formatted_name = project_name.replace("-", " ").replace("_", " ").title()
        album_title = f"Construction: {formatted_name}"
        try:
            photos_client = CloudinaryClient()
            album = photos_client.create_album(album_title)

            if album:
                # Save album info to project metadata
                metadata_file = project_dir / "project.json"
                with open(metadata_file) as f:
                    metadata = json.load(f)

                album_url = album.get("productUrl", "")
                metadata["cloudinary_album"] = {
                    "id": album["id"],
                    "title": album["title"],
                    "url": album_url,
                }

                with open(metadata_file, "w") as f:
                    json.dump(metadata, f, indent=2)

                logger.info(f"Created cloud photo album: {album_title}")
                if album.get("productUrl"):
                    logger.info(f"Album URL: {album['productUrl']}")
            else:
                logger.warning("Could not create cloud photo album. You can create it manually.")

        except Exception as e:
            logger.handle_exception(e, "cloud photo integration")
            logger.info("You can still use the project without cloud photo integration.")
    else:
        logger.info("Photo album integration is disabled (ENABLE_PHOTO_MONITORING = false)")
        logger.info("Project created without photo album integration")

    # Create initial commit
    if not GitOperations.commit_changes(project_dir, f"Start project: {project_name}"):
        return False

    logger.success("Project setup complete!")
    logger.info(f"""
Next steps:
1. Take photos on your mobile device
2. Add them to cloud photo album: {album_title}
3. When ready to sync photos, run: make add-photos PROJECT={project_name}
4. When project is complete, run: make finish-project PROJECT={project_name}

Note: Photos will be downloaded from cloud service and organized locally.
""")
    return True


def add_photos(project_name):
    """Add photos to existing project from cloud photo service or local sources"""
    project = ProjectManager(project_name)

    if not project.project_directory.exists():
        logger.error(f"Project {project_name} not found. Run 'make start-project PROJECT={project_name}' first.")
        return False

    # Switch to project branch
    if not GitOperations.checkout_branch(project.git_branch):
        logger.error(f"Could not switch to branch {project.git_branch}")
        return False

    # Try cloud photo service first, fall back to local if needed
    if _try_cloud_photo_sync(project_name, project.project_directory):
        return True

    # Cloud sync failed or unavailable, use local photo discovery
    logger.info("Falling back to local photo discovery...")
    return _add_photos_from_local_sources(project_name, project.project_directory)


def _try_cloud_photo_sync(project_name, project_dir):
    """Attempt to sync photos from cloud photo service. Returns True if successful, False to fall back."""
    # Get project metadata to find cloud photo album
    metadata_file = project_dir / "project.json"
    metadata = {}
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)

    # Check for legacy google_photos_album or cloudinary album info
    album_info = metadata.get("google_photos_album") or metadata.get("cloudinary_album")
    if not album_info:
        print("No cloud photo album found for this project.")
        return False

    # Download photos from cloud photo service
    try:
        photos_client = CloudinaryClient()
        album_title = album_info["title"]

        print(f"Downloading photos from cloud album: {album_title}")
        downloaded_files = photos_client.download_album_photos(album_title, str(project_dir))

        if downloaded_files:
            print(f"Downloaded {len(downloaded_files)} photos from cloud service")

            # Update project metadata
            existing_photos = set(metadata.get("photos", []))
            new_photos = [f.name for f in downloaded_files if f.name not in existing_photos]

            metadata["photos"] = list(existing_photos) + new_photos
            metadata["last_updated"] = datetime.now().isoformat()
            metadata["last_sync"] = {
                "date": datetime.now().isoformat(),
                "photos_downloaded": len(downloaded_files),
                "new_photos": len(new_photos),
            }

            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

            # Commit changes
            if new_photos:
                commit_message = f"Sync {len(new_photos)} new photos from cloud service: {project_name}"
                if GitOperations.commit_changes(project_dir, commit_message, ensure_config=False):
                    print("New photos committed to git")
                else:
                    print("Warning: Could not commit photos")
            else:
                print("No new photos to commit")
            return True
        else:
            print("No photos found in cloud album")
            return False

    except Exception as e:
        print(f"Error downloading from cloud service: {e}")
        return False


def _find_local_photos():
    """Find photos in common local directories"""
    photo_sources = [
        Path.home() / "Downloads",
        Path.home() / "Pictures",
        Path("/tmp"),
        Path.cwd() / "tmp",
    ]

    photos_found = []
    photo_extensions = ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]

    for source in photo_sources:
        if source.exists():
            for ext in photo_extensions:
                photos_found.extend(list(source.glob(ext)))

    return photos_found


def _display_photos_preview(photos_found):
    """Display a preview of found photos"""
    logger.info(f"Found {len(photos_found)} potential photos:")
    for i, photo in enumerate(photos_found[:10]):
        size_kb = photo.stat().st_size // 1024
        logger.info(f"  {i + 1}. {photo.name} ({size_kb}KB)")

    if len(photos_found) > 10:
        logger.info(f"  ... and {len(photos_found) - 10} more")


def _copy_photos_to_project(photos_found, project_dir):
    """Copy photos to project directory and return count"""
    copied_count = 0
    for photo in photos_found:
        try:
            dest = project_dir / photo.name
            if not dest.exists():
                shutil.copy2(photo, dest)
                copied_count += 1
        except Exception as e:
            logger.warning(f"Could not copy {photo.name}: {e}")

    return copied_count


def _commit_copied_photos(project_dir, project_name, copied_count):
    """Commit copied photos to git"""
    if copied_count > 0:
        logger.info(f"Copied {copied_count} photos to project directory")

        commit_message = f"Add {copied_count} photos to {project_name}"
        if GitOperations.commit_changes(project_dir, commit_message, ensure_config=False):
            logger.info("Photos committed to git")
        else:
            logger.warning("Could not commit photos")


def _add_photos_from_local_sources(project_name, project_dir):
    """Add photos from local file system sources"""
    photos_found = _find_local_photos()

    if not photos_found:
        logger.info("No photos found in common locations.")
        logger.info(f"Manual option: Copy photos directly to {project_dir}/")
        return True

    _display_photos_preview(photos_found)

    response = input(f"Copy all photos to {project_name}? (y/n): ")
    if response.lower() != "y":
        return True

    copied_count = _copy_photos_to_project(photos_found, project_dir)
    _commit_copied_photos(project_dir, project_name, copied_count)

    return True


def generate_blog_post(project_name):
    """Generate blog post using Claude analysis"""
    project_dir = get_project_dir(project_name)

    if not project_dir.exists():
        print(f"Error: Project {project_name} not found")
        return None

    # Get project metadata
    metadata_file = project_dir / "project.json"
    metadata = {}
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)

    # Count photos
    photo_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
        photo_files.extend(list(project_dir.glob(ext)))

    # Create blog post filename
    today = datetime.now()
    post_filename = f"{today.strftime('%Y-%m-%d')}-{project_name.replace('_', '-')}.md"
    post_path = Path("_posts") / post_filename

    # Generate blog post content using Claude
    claude_prompt = f"""


Create a blog post for a construction project documentation.

Project: {project_name}
Photos: {len(photo_files)} images in {project_dir}
Start date: {metadata.get("start_date", "Unknown")}

Write a Jekyll blog post with:
1. Proper front matter (title, date, categories)
2. Introduction explaining the project
3. Photo gallery section with markdown image references
4. Conclusion with lessons learned or next steps

Use this format for images: ![Description](/{project_dir}/filename.jpg)

Make it personal and conversational, as this is for a personal blog.
Focus on the project process, challenges, and outcomes.
"""

    try:
        # Use Claude CLI to generate blog post
        result = subprocess.run(["claude", claude_prompt], capture_output=True, text=True, check=True)
        blog_content = result.stdout

        # Write blog post
        with open(post_path, "w") as f:
            f.write(blog_content)

        print(f"Generated blog post: {post_path}")
        return post_path

    except subprocess.CalledProcessError as e:
        print(f"Error generating blog post with Claude: {e}")
        # Fallback: create basic blog post template
        fallback_content = f"""---
title: "{project_name.replace("-", " ").replace("_", " ").title()}"
date: {today.strftime("%Y-%m-%d")}
categories: [construction, projects]
---

# {project_name.replace("-", " ").replace("_", " ").title()}

Project started on {metadata.get("start_date", "recently")} with {len(photo_files)} photos documented.

## Photos

"""

        # Add photo references
        for photo in sorted(photo_files):
            fallback_content += f"![{photo.stem}](/{project_dir}/{photo.name})\n\n"

        fallback_content += """
## Summary

Project documentation and photos captured above.

*Blog post generated automatically by project management system.*
"""

        with open(post_path, "w") as f:
            f.write(fallback_content)

        print(f"Generated basic blog post: {post_path}")
        return post_path


def finish_project(project_name):
    """Finish project and create PR"""
    project_dir = get_project_dir(project_name)

    if not project_dir.exists():
        print(f"Error: Project {project_name} not found")
        return False

    # Switch to project branch
    branch = get_project_branch(project_name)
    if not GitOperations.checkout_branch(branch):
        print(f"Error: Could not switch to branch {branch}")
        return False

    # Generate blog post
    blog_post = generate_blog_post(project_name)
    if not blog_post:
        return False

    # Update project metadata
    metadata_file = project_dir / "project.json"
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)

        metadata["status"] = "completed"
        metadata["completion_date"] = datetime.now().isoformat()
        metadata["blog_post"] = str(blog_post)

        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    # Commit blog post
    commit_message = f"Complete project: {project_name} - add blog post"
    if not GitOperations.add_and_commit_files([blog_post, project_dir], commit_message, ensure_config=False):
        print("Error committing blog post")
        return False
    print("Blog post committed")

    # Generate and create PR
    print("Creating pull request...")
    try:
        subprocess.run(["make", "generate-pr-content"], check=True)
        subprocess.run(["make", "create-pr"], check=True)
        print("Pull request created successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error creating PR: {e}")
        print("You can manually create a PR with:")
        print(f"  git push origin {branch}")
        print(f"  gh pr create --title 'Project: {project_name}' --body 'Construction project documentation'")

    return True


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 project-manager.py {start|add-photos|finish} <project-name>")
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
