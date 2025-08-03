#!/usr/bin/env python3
"""
Imgur API client for construction project photo management.
Handles album creation, photo downloads, and tag-based project detection.
"""

import hashlib
import json
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


class ImgurClient(PhotoClient):

    def __init__(self, client_id=None, client_secret=None, access_token=None):
        """Initialize Imgur client with API credentials"""
        self.client_id = client_id or os.environ.get("IMGUR_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("IMGUR_CLIENT_SECRET")
        self.access_token = access_token or os.environ.get("IMGUR_ACCESS_TOKEN")

        self.base_url = "https://api.imgur.com/3"

        if not self.client_id:
            raise Exception("Imgur Client ID is required")

    def _get_headers(self, authenticated=False):
        """Get authentication headers for API requests"""
        if authenticated and self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        else:
            return {"Authorization": f"Client-ID {self.client_id}"}

    def _make_request(
        self, method, endpoint, data=None, files=None, authenticated=False
    ):
        """Make authenticated Imgur API request"""
        url = f"{self.base_url}/{endpoint}"
        headers = self._get_headers(authenticated)

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=data)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, data=data, files=files)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, data=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers)

            response.raise_for_status()

            result = response.json()

            if not result.get("success"):
                error_data = result.get("data", {})
                error_msg = error_data.get("error", "Unknown Imgur API error")
                print(f"Imgur API error: {error_msg}")
                return None

            return result.get("data")

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
        except json.JSONDecodeError:
            print("Invalid JSON response from Imgur API")
            return None

    def upload_image(self, image_path, title=None, description=None, album_id=None):
        """Upload an image to Imgur"""
        if not Path(image_path).exists():
            print(f"Image file not found: {image_path}")
            return None

        with open(image_path, "rb") as image_file:
            files = {"image": image_file}
            data = {}

            if title:
                data["title"] = title
            if description:
                data["description"] = description
            if album_id:
                data["album"] = album_id

            result = self._make_request("POST", "image", data=data, files=files)

            if result:
                print(f"Uploaded image: {result.get('link', 'Unknown URL')}")
                return result
            return None

    def create_album(self, title, description="", privacy="hidden", tags=None):
        """Create a new Imgur album"""
        data = {
            "title": title,
            "description": description,
            "privacy": privacy,  # public, hidden, or secret
        }

        # Add tags as comma-separated string
        if tags:
            if isinstance(tags, list):
                data["tags"] = ",".join(tags)
            else:
                data["tags"] = tags

        result = self._make_request("POST", "album", data=data, authenticated=True)

        if result:
            print(f"Created album: {title} (ID: {result.get('id')})")
            return result
        else:
            print(f"Failed to create album: {title}")
            return None

    def get_album(self, album_id):
        """Get album information and images"""
        result = self._make_request("GET", f"album/{album_id}")

        if result:
            return result
        else:
            print(f"Failed to get album: {album_id}")
            return None

    def get_account_albums(self, username=None):
        """Get albums for authenticated account or specific user"""
        if username:
            endpoint = f"account/{username}/albums"
        else:
            endpoint = "account/me/albums"

        result = self._make_request("GET", endpoint, authenticated=True)

        if result:
            return result
        else:
            print("Failed to get account albums")
            return []

    def search_albums_by_tag(self, tag):
        """Search for albums with specific tag"""
        # Note: Imgur's search might be limited for non-public content
        # This method searches through user's own albums for the tag
        albums = self.get_account_albums()
        tagged_albums = []

        for album in albums:
            album_tags = album.get("tags", [])
            if isinstance(album_tags, str):
                album_tags = [t.strip() for t in album_tags.split(",")]

            if tag in album_tags:
                tagged_albums.append(album)

        return tagged_albums

    def authenticate(self) -> bool:
        """Test authentication and return success status"""
        try:
            if self.access_token:
                # Test authenticated request
                result = self._make_request("GET", "account/me", authenticated=True)
                return result is not None
            else:
                # Test anonymous request
                return self.client_id is not None
        except Exception:
            return False

    def get_construction_projects(self) -> List[Dict[str, Any]]:
        """Get all albums tagged with project: tags"""
        from interfaces.photo_client_interface import ProjectExtractor

        albums = self.get_account_albums()
        project_albums = []

        for album in albums:
            album_tags = album.get("tags", [])
            if isinstance(album_tags, str):
                album_tags = [t.strip() for t in album_tags.split(",")]

            # Look for tags starting with "project:"
            project_name = None
            for tag in album_tags:
                project_name = ProjectExtractor.extract_from_tag(tag)
                if project_name:
                    break

            if project_name:
                project_albums.append(
                    {
                        "id": album["id"],
                        "title": album.get("title", "Untitled Album"),
                        "project_name": project_name,
                        "url": f"https://imgur.com/a/{album['id']}",
                        "tags": album_tags,
                        "image_count": album.get("images_count", 0),
                    }
                )

        return project_albums

    def get_project_images(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all images from a specific project"""
        album = self.get_album(project_id)
        if not album:
            return []

        images = album.get("images", [])
        project_images = []

        for i, image in enumerate(images):
            # Create clean filename
            title = image.get("title", f"image_{i + 1}")
            clean_title = re.sub(r"[^\w\-_\.]", "_", title)

            # Get file extension from URL
            image_url = image.get("link", "")
            if image_url:
                url_ext = image_url.split(".")[-1].lower()
                if url_ext not in ["jpg", "jpeg", "png", "gif"]:
                    url_ext = "jpg"
                filename = f"{i + 1:03d}_{clean_title}.{url_ext}"
            else:
                filename = f"{i + 1:03d}_{clean_title}.jpg"

            project_images.append(
                {
                    "id": image.get("id", f"img_{i}"),
                    "title": title,
                    "url": image_url,
                    "filename": filename,
                    "metadata": {
                        "datetime": image.get("datetime"),
                        "size": image.get("size"),
                        "width": image.get("width"),
                        "height": image.get("height"),
                    },
                }
            )

        return project_images

    def download_image(
        self, image_url: str, download_dir: str, filename: str
    ) -> Optional[Path]:
        """Download an image from Imgur URL"""
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
        """Download all images from a project"""
        images = self.get_project_images(project_id)
        downloaded_files = []

        for image in images:
            if not image["url"]:
                continue

            file_path = self.download_image(
                image["url"], download_dir, image["filename"]
            )
            if file_path:
                downloaded_files.append(file_path)

        print(f"Downloaded {len(downloaded_files)} images to {download_dir}")
        return downloaded_files

    def download_album_images(self, album_id, download_dir, album_title="Unknown"):
        """Legacy method - use download_project_images instead"""
        return self.download_project_images(album_id, download_dir)

    def update_album(
        self, album_id, title=None, description=None, privacy=None, tags=None
    ):
        """Update album properties"""
        data = {}

        if title:
            data["title"] = title
        if description:
            data["description"] = description
        if privacy:
            data["privacy"] = privacy
        if tags:
            if isinstance(tags, list):
                data["tags"] = ",".join(tags)
            else:
                data["tags"] = tags

        if not data:
            print("No update data provided")
            return None

        result = self._make_request(
            "PUT", f"album/{album_id}", data=data, authenticated=True
        )

        if result:
            print(f"Updated album: {album_id}")
            return result
        else:
            print(f"Failed to update album: {album_id}")
            return None

    def delete_album(self, album_id):
        """Delete an album"""
        result = self._make_request("DELETE", f"album/{album_id}", authenticated=True)

        if result:
            print(f"Deleted album: {album_id}")
            return True
        else:
            print(f"Failed to delete album: {album_id}")
            return False


class ImgurHasher(ProjectHasher):
    """Hash generator for Imgur projects and images"""

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


def setup_imgur_auth():
    """Interactive setup for Imgur API credentials"""
    print(
        """


Imgur API Setup
===============

To use Imgur integration, you need to:

1. Go to https://api.imgur.com/oauth2/addclient
2. Register a new application
3. Choose "OAuth 2 authorization without a callback URL"
4. Get your Client ID and Client Secret
5. Complete OAuth flow for access token (optional for anonymous uploads)

"""
    )

    client_id = input("Enter your Imgur Client ID: ").strip()
    client_secret = input("Enter your Imgur Client Secret: ").strip()

    if not client_id:
        print("Client ID is required!")
        return False

    print(f"\nClient ID: {client_id}")
    if client_secret:
        secret_preview = client_secret[:10]
        print(f"Client Secret: {secret_preview}...")
    else:
        print("Client Secret: (not provided)")

    # Save to config file
    setup_date = datetime.now().isoformat()
    config = {
        "client_id": client_id,
        "client_secret": client_secret,
        "setup_date": setup_date,
    }

    config_dir = Path.home() / ".config"
    config_dir.mkdir(exist_ok=True)

    with open(config_dir / "imgur-credentials.json", "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nCredentials saved to {config_dir / 'imgur-credentials.json'}")
    print("\nNext steps:")
    print("1. Set environment variables:")
    print(f"   export IMGUR_CLIENT_ID='{client_id}'")
    if client_secret:
        print(f"   export IMGUR_CLIENT_SECRET='{client_secret}'")
    print("2. For authenticated requests, complete OAuth flow to get access token")
    print("3. Add tokens to your environment or GitHub Secrets")

    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup_imgur_auth()
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test basic functionality
        client = ImgurClient()
        print("Testing Imgur client...")
        print(f"Client ID configured: {'Yes' if client.client_id else 'No'}")

        # Test getting account albums (requires authentication)
        if client.access_token:
            albums = client.get_account_albums()
            print(f"Found {len(albums)} albums in account")

            # Test construction project detection
            project_albums = client.get_construction_projects()
            print(f"Found {len(project_albums)} construction project albums")
        else:
            print("Access token not configured - skipping authenticated tests")
    else:
        print("Usage:")
        print("  python3 imgur_client.py setup  # Setup API credentials")
        print("  python3 imgur_client.py test   # Test client functionality")
