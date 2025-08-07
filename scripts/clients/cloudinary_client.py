#!/usr/bin/env python3
"""
Cloudinary API client for construction project photo management.
Handles folder creation, photo downloads, and tag-based project detection.
"""

import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import requests
from interfaces.photo_client_interface import PhotoClient
from interfaces.photo_client_interface import ProjectHasher

try:
    import cloudinary
    import cloudinary.api
    import cloudinary.uploader
except ImportError as e:
    raise ImportError("Cloudinary SDK not installed. Run: pip install -r requirements.txt") from e


class CloudinaryClient(PhotoClient):
    def __init__(self, cloudinary_url=None):
        """Initialize Cloudinary client with API credentials"""
        # Configure from environment or provided URL
        if cloudinary_url:
            os.environ["CLOUDINARY_URL"] = cloudinary_url

        # Force reload of configuration from environment
        cloudinary.config(secure=True)

        # Verify configuration
        config = cloudinary.config()
        if not all([config.cloud_name, config.api_key, config.api_secret]):
            # Try to get directly from environment
            cloudinary_url_env = os.getenv("CLOUDINARY_URL")
            if cloudinary_url_env:
                os.environ["CLOUDINARY_URL"] = cloudinary_url_env
                cloudinary.config(secure=True)
                config = cloudinary.config()

            if not all([config.cloud_name, config.api_key, config.api_secret]):
                raise ValueError(
                    "Missing Cloudinary credentials. Set environment variable:\nCLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name"
                )

        self.cloud_name = config.cloud_name
        print(f"✅ Initialized Cloudinary client for cloud: {self.cloud_name}")

    def authenticate(self) -> bool:
        """Test authentication and return success status"""
        try:
            # Test API access by getting resource count
            result = cloudinary.api.resources(max_results=1)
            return True
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False

    def get_construction_projects(self) -> List[Dict[str, Any]]:
        """Get all folders with construction project naming pattern

        Looks for folders starting with project prefixes or containing 'project' in tags.
        Since Cloudinary doesn't have album tags like Imgur, we'll look for:
        1. Folders with 'project' prefix (e.g., 'project-deck-repair')
        2. Folders with date-project pattern (e.g., '2025-08-02-deck-repair')
        """
        try:
            # Get all folders
            folders_result = cloudinary.api.root_folders()
            folders = folders_result.get("folders", [])

            project_folders = []

            for folder in folders:
                folder_name = folder.get("name", "")
                project_name = self._extract_project_from_folder(folder_name)

                if project_name:
                    # Get resource count for this folder
                    try:
                        resources = cloudinary.api.resources(type="upload", prefix=folder_name, max_results=1)
                        image_count = resources.get("total_count", 0)
                    except Exception:
                        image_count = 0

                    project_folders.append(
                        {
                            "id": folder_name,  # Use folder name as ID
                            "title": folder_name.replace("-", " ").title(),
                            "project_name": project_name,
                            "url": f"https://console.cloudinary.com/console/media_library/folders/{folder_name}",
                            "tags": ["construction", "project"],  # Default tags
                            "image_count": image_count,
                        }
                    )

            return project_folders

        except Exception as e:
            print(f"Failed to get construction projects: {e}")
            return []

    def _extract_project_from_folder(self, folder_name: str) -> Optional[str]:
        """Extract project name from folder name"""

        # Try different patterns:
        # 1. "project-deck-repair" -> "deck-repair"
        if folder_name.startswith("project-"):
            return folder_name[8:]  # Remove "project-" prefix

        # 2. "2025-08-02-deck-repair" -> "deck-repair"
        date_pattern = r"^\d{4}-\d{2}-\d{2}-(.+)$"
        match = re.match(date_pattern, folder_name)
        if match:
            return match.group(1)

        # 3. "test-construction-project" -> "test-construction-project"
        if "project" in folder_name.lower() or "construction" in folder_name.lower():
            return folder_name

        return None

    def get_project_images(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all images from a specific project folder"""
        try:
            # Get all resources in the folder
            result = cloudinary.api.resources(
                type="upload",
                prefix=project_id,
                max_results=500,  # Adjust as needed
            )

            resources = result.get("resources", [])
            project_images = []

            for i, resource in enumerate(resources):
                # Extract filename from public_id
                public_id = resource.get("public_id", "")
                filename_parts = public_id.split("/")[-1]  # Get last part after folder

                # Generate clean filename
                if not filename_parts:
                    filename_parts = f"image_{i + 1}"

                # Get file extension from format
                file_format = resource.get("format", "jpg")
                filename = f"{i + 1:03d}_{filename_parts}.{file_format}"

                # Get creation date
                created_at = resource.get("created_at", "")
                if created_at:
                    try:
                        # Parse ISO date
                        created_datetime = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        datetime_timestamp = int(created_datetime.timestamp())
                    except Exception:
                        datetime_timestamp = None
                else:
                    datetime_timestamp = None

                project_images.append(
                    {
                        "id": resource.get("public_id", f"img_{i}"),
                        "title": filename_parts,
                        "url": resource.get("secure_url", ""),
                        "filename": filename,
                        "metadata": {
                            "datetime": datetime_timestamp,
                            "size": resource.get("bytes"),
                            "width": resource.get("width"),
                            "height": resource.get("height"),
                            "format": resource.get("format"),
                        },
                    }
                )

            return project_images

        except Exception as e:
            print(f"Failed to get project images for {project_id}: {e}")
            return []

    def download_image(self, image_url: str, download_dir: str, filename: str) -> Optional[Path]:
        """Download an image from Cloudinary URL"""
        if not filename:
            # Extract filename from URL
            filename = image_url.split("/")[-1]
            if "." not in filename:
                filename += ".jpg"  # Default extension

        file_path = Path(download_dir) / filename

        try:
            response = requests.get(image_url)
            response.raise_for_status()

            os.makedirs(download_dir, exist_ok=True)

            with open(file_path, "wb") as f:
                f.write(response.content)

            print(f"Downloaded: {filename}")
            return file_path

        except Exception as e:
            print(f"Failed to download {filename}: {e}")
            return None

    def download_project_images(self, project_id: str, download_dir: str) -> List[Path]:
        """Download all images from a project folder"""
        images = self.get_project_images(project_id)
        downloaded_files = []

        for image in images:
            if not image["url"]:
                continue

            file_path = self.download_image(image["url"], download_dir, image["filename"])
            if file_path:
                downloaded_files.append(file_path)

        print(f"Downloaded {len(downloaded_files)} images to {download_dir}")
        return downloaded_files

    def download_folder_photos(self, folder_name: str, download_dir: str, tag_downloaded: bool = False) -> List[Path]:
        """
        Download photos from Cloudinary folder, optionally tagging as downloaded.
        Only downloads photos not already tagged as downloaded.
        """
        try:
            # Get all resources in the folder
            result = cloudinary.api.resources(
                type="upload",
                prefix=folder_name,
                max_results=500,
                tags=False if not tag_downloaded else None,  # Don't filter by tags initially
            )

            resources = result.get("resources", [])
            downloaded_files = []

            os.makedirs(download_dir, exist_ok=True)

            for i, resource in enumerate(resources):
                # Skip if already tagged as downloaded (when tag_downloaded is True)
                resource_tags = resource.get("tags", [])
                if tag_downloaded and "downloaded" in resource_tags:
                    continue

                # Extract filename from public_id
                public_id = resource.get("public_id", "")
                filename_parts = public_id.split("/")[-1]  # Get last part after folder

                # Generate clean filename
                if not filename_parts:
                    filename_parts = f"image_{i + 1}"

                # Get file extension from format
                file_format = resource.get("format", "jpg")
                filename = f"{filename_parts}.{file_format}"

                # Ensure no duplicate filename in download directory
                file_path = Path(download_dir) / filename
                counter = 1
                while file_path.exists():
                    stem = Path(filename).stem
                    ext = Path(filename).suffix
                    filename = f"{stem}_{counter}{ext}"
                    file_path = Path(download_dir) / filename
                    counter += 1

                # Download the image
                secure_url = resource.get("secure_url", "")
                if secure_url:
                    try:
                        response = requests.get(secure_url)
                        response.raise_for_status()

                        with open(file_path, "wb") as f:
                            f.write(response.content)

                        downloaded_files.append(file_path)
                        print(f"Downloaded: {filename}")

                        # Tag as downloaded in Cloudinary if requested
                        if tag_downloaded:
                            try:
                                cloudinary.uploader.add_tag("downloaded", public_id)
                            except Exception as tag_error:
                                print(f"Warning: Could not tag {filename} as downloaded: {tag_error}")

                    except Exception as download_error:
                        print(f"Failed to download {filename}: {download_error}")

            print(f"Downloaded {len(downloaded_files)} new photos from folder '{folder_name}' to {download_dir}")
            return downloaded_files

        except Exception as e:
            print(f"Failed to download photos from folder '{folder_name}': {e}")
            return []

    def upload_image(self, image_path, folder=None, title=None):
        """Upload an image to Cloudinary folder"""
        if not Path(image_path).exists():
            print(f"Image file not found: {image_path}")
            return None

        try:
            upload_options = {"use_filename": True, "unique_filename": False}

            if folder:
                upload_options["folder"] = folder

            if title:
                upload_options["context"] = f"title={title}"

            result = cloudinary.uploader.upload(image_path, **upload_options)

            print(f"Uploaded image: {result.get('secure_url')}")
            return result

        except Exception as e:
            print(f"Upload failed: {e}")
            return None

    def create_folder(self, folder_name, description=""):
        """Create a folder in Cloudinary (implicit via upload)"""
        # Cloudinary creates folders implicitly when uploading to them
        # We'll create a placeholder file to ensure the folder exists
        try:
            # Create a minimal placeholder
            placeholder_result = cloudinary.uploader.upload(
                "data:text/plain;base64,UGxhY2Vob2xkZXI=",  # "Placeholder" in base64
                folder=folder_name,
                public_id=f"{folder_name}/.placeholder",
                resource_type="raw",
            )

            print(f"Created folder: {folder_name}")
            return {"id": folder_name, "name": folder_name}

        except Exception as e:
            print(f"Failed to create folder {folder_name}: {e}")
            return None


class CloudinaryHasher(ProjectHasher):
    """Hash generator for Cloudinary projects and images"""

    def generate_project_hash(self, project: Dict[str, Any]) -> str:
        """Generate hash for project to detect changes"""
        project_id = project.get("id", "")
        image_count = project.get("image_count", 0)
        title = project.get("title", "")
        hash_data = f"{project_id}{image_count}{title}"
        return hashlib.md5(hash_data.encode()).hexdigest()

    def generate_image_hash(self, image: Dict[str, Any]) -> str:
        """Generate hash for image to detect changes"""
        image_id = image.get("id", "")
        url = image.get("url", "")
        datetime_val = image.get("metadata", {}).get("datetime", "")
        hash_data = f"{image_id}{url}{datetime_val}"
        return hashlib.md5(hash_data.encode()).hexdigest()


if __name__ == "__main__":
    import sys

    # Load environment variables from .env file FIRST
    try:
        from dotenv import load_dotenv

        # Try multiple paths
        for env_path in [".env", "../.env", "../../.env"]:
            if Path(env_path).exists():
                print(f"Loading .env from {env_path}")
                load_dotenv(env_path)
                break
    except ImportError:
        print("💡 Tip: Install dependencies to use .env files: pip install -r requirements.txt")

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test basic functionality
        try:
            client = CloudinaryClient()
            print("Testing Cloudinary client...")

            # Test authentication
            if client.authenticate():
                print("✅ Authentication successful")
            else:
                print("❌ Authentication failed")
                sys.exit(1)

            # Test getting construction projects
            projects = client.get_construction_projects()
            print(f"Found {len(projects)} construction projects")

            for project in projects:
                print(f"  - {project['title']} (ID: {project['id']}, Images: {project['image_count']})")

                # Test getting images for first project
                if projects:
                    images = client.get_project_images(project["id"])
                    print(f"    Found {len(images)} images")
                    for img in images[:3]:  # Show first 3
                        print(f"      - {img['filename']}")
        except Exception as e:
            print(f"❌ Test failed: {e}")
            sys.exit(1)
    else:
        print("Usage:")
        print("  python3 cloudinary_client.py test   # Test client functionality")
