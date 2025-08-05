#!/usr/bin/env python3
"""
Construction project workflow manager.
Handles project state, GitHub integration, and git operations.
Decoupled from specific photo service clients.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import requests
from interfaces.photo_client_interface import PhotoClient
from interfaces.photo_client_interface import ProjectExtractor
from interfaces.photo_client_interface import ProjectHasher
from utils.git_operations import GitOperations

# Note: GitManager class functionality has been consolidated into GitOperations utility


class GitHubManager:
    """Handles GitHub API operations"""

    def __init__(self, github_token: str, repo_owner: str, repo_name: str):
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name

    def _api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated GitHub API request"""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/{endpoint}"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        response = requests.request(method, url, json=data, headers=headers)

        if response.status_code not in [200, 201]:
            error_msg = f"GitHub API error: {response.status_code} - {response.text}"
            print(error_msg)
            # For 403 errors, raise a more specific exception
            if response.status_code == 403:
                raise PermissionError(error_msg)
            raise Exception(error_msg)

        return response.json()

    def create_issue(self, project_name: str, project_title: str, project_url: str = "") -> Optional[Dict]:
        """Create GitHub issue for new construction project"""
        formatted_name = project_name.replace("-", " ").title()
        title = f"Construction Project: {formatted_name}"

        branch_name = ProjectExtractor.get_branch_name(project_name)

        body = f"""# Construction Project: {project_title}

**Status**: 🚧 Active
**Photo Album**: [{project_title}]({project_url})
**Project Branch**: `{branch_name}`
**Tag**: `project:{project_name.replace("-", "_")}`

## Project Timeline
- **Started**: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}
- **Photos**: Will be synced automatically every hour
- **Status**: Add `ready` label when project is complete

## Automated Actions
- ✅ Project branch created
- ✅ Photo sync enabled (hourly)
- 🔄 Waiting for photos...

## Next Steps
1. Add photos to the album as you work
2. Ensure album has correct project tag
3. Photos will sync automatically to the project branch
4. When complete, add the `ready` label to generate blog post

---
*This issue was created automatically by Construction Project Monitor*
"""

        data = {
            "title": title,
            "body": body,
            "labels": ["construction", "auto-generated"],
        }

        result = self._api_request("POST", "issues", data)
        print(f"Created GitHub issue #{result['number']}: {title}")
        return result

    def find_existing_issue(self, project_name: str) -> Optional[Dict]:
        """Find existing GitHub issue for project"""
        formatted_name = project_name.replace("-", " ").title()
        search_title = f"Construction Project: {formatted_name}"

        try:
            # Search for issues with matching title
            result = self._api_request("GET", "issues?state=open&labels=construction")

            if result:
                for issue in result:
                    if issue.get("title") == search_title:
                        print(f"Found existing issue #{issue['number']}: {search_title}")
                        return issue

            return None
        except Exception as e:
            print(f"Error searching for existing issue: {e}")
            return None

    def add_issue_comment(
        self,
        issue_number: int,
        project_name: str,
        photo_count: int,
        new_photos_count: int,
    ):
        """Add comment to issue with sync update"""
        branch_name = ProjectExtractor.get_branch_name(project_name)

        if new_photos_count > 0:
            body = f"""## Photo Sync Update - {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}

✅ **{new_photos_count} new photos** synced to branch `{branch_name}`
📸 **Total photos**: {photo_count}
🔄 **Next sync**: In ~1 hour

Photos have been committed and are ready for review.
"""
        else:
            body = f"""## Photo Sync - {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}

ℹ️ No new photos found
📸 **Total photos**: {photo_count}
🔄 **Next sync**: In ~1 hour
"""

        data = {"body": body}
        self._api_request("POST", f"issues/{issue_number}/comments", data)
        print(f"Updated issue #{issue_number} with sync status")


class ProjectStateManager:
    """Manages persistent project state"""

    def __init__(self, state_file: Path):
        self.state_file = state_file

    def load_state(self) -> Dict[str, Any]:
        """Load existing project state from file"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {"projects": {}, "last_scan": None}

    def save_state(self, state: Dict[str, Any]):
        """Save project state to file"""
        os.makedirs(self.state_file.parent, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)


class ConstructionWorkflow:
    """Main workflow orchestrator for construction projects"""

    def __init__(
        self,
        photo_client: PhotoClient,
        project_hasher: ProjectHasher,
        github_token: str,
        repo_owner: str,
        repo_name: str,
        state_file: Path,
    ):
        self.photo_client = photo_client
        self.project_hasher = project_hasher
        self.github = GitHubManager(github_token, repo_owner, repo_name)
        self.state_manager = ProjectStateManager(state_file)

    def sync_project_photos(self, project: Dict[str, Any], existing_images: Dict[str, Any]) -> tuple[List[Dict], int]:
        """Sync photos for a specific project"""
        project_id = project["id"]
        project_name = project["project_name"]

        print(f"Syncing photos for project: {project_name} (ID: {project_id})")
        print(f"Existing tracked images: {len(existing_images)}")

        # Get current images from photo service
        current_images = self.photo_client.get_project_images(project_id)
        print(f"Current images from photo service: {len(current_images)}")

        if not current_images:
            print(f"No images found in photo service for project: {project_name}")
            return [], 0

        # Add hashes to images for change detection
        for image in current_images:
            image["hash"] = self.project_hasher.generate_image_hash(image)

        # Find new images (not in existing_images)
        existing_hashes = set(existing_images.keys())
        new_images = [img for img in current_images if img["hash"] not in existing_hashes]

        print(f"Image comparison - Existing hashes: {len(existing_hashes)}, New images: {len(new_images)}")

        if not new_images:
            print(f"No new photos for project: {project_name}")
            return [], len(current_images)

        print(f"Found {len(new_images)} new photos for project: {project_name}")
        for i, img in enumerate(new_images[:3]):  # Show first 3
            print(f"  New photo {i+1}: {img.get('filename', 'unknown')} (hash: {img['hash'][:8]}...)")
        if len(new_images) > 3:
            print(f"  ... and {len(new_images) - 3} more photos")

        # Switch to project branch
        branch_name = ProjectExtractor.get_branch_name(project_name)
        if not GitOperations.create_or_switch_branch(branch_name):
            return [], len(current_images)

        # Create project directory
        project_dir = Path(f"assets/images/{datetime.now().strftime('%Y-%m-%d')}-{project_name}")
        project_dir.mkdir(parents=True, exist_ok=True)

        # Download new images
        downloaded_files = []
        for image in new_images:
            if not image["url"]:
                continue

            file_path = self.photo_client.download_image(image["url"], str(project_dir), image["filename"])
            if file_path:
                downloaded_files.append(file_path)

        if downloaded_files:
            # Update project metadata
            metadata_file = project_dir / "project.json"
            metadata = {
                "project_name": project_name,
                "project_id": project_id,
                "project_title": project["title"],
                "total_photos": len(current_images),
                "last_sync": datetime.now().isoformat(),
                "project_url": project.get("url", ""),
                "images": [
                    {
                        "id": img["id"],
                        "title": img["title"],
                        "filename": img["filename"],
                        "metadata": img["metadata"],
                    }
                    for img in current_images
                ],
            }

            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

            # Commit changes
            commit_msg = f"Sync {len(downloaded_files)} new photos: {project_name}"
            if not GitOperations.commit_changes(project_dir, commit_msg):
                raise Exception(f"Failed to commit changes for project: {project_name}")

        return new_images, len(current_images)

    def _setup_project_issue(self, project_name: str, project_title: str, project_url: str) -> Optional[int]:
        """Setup GitHub issue for project (find existing or create new)"""
        # Check for existing GitHub issue first
        existing_issue = None
        issue_number = None
        try:
            existing_issue = self.github.find_existing_issue(project_name)
            if existing_issue:
                issue_number = existing_issue["number"]
                print(f"Using existing GitHub issue #{issue_number}")
        except PermissionError as e:
            print(f"⚠️  Warning: Could not search for GitHub issues due to permissions: {e}")

        # Create new issue only if none exists
        if not existing_issue:
            try:
                issue = self.github.create_issue(project_name, project_title, project_url)
                issue_number = issue["number"]
            except PermissionError as e:
                print(f"⚠️  Warning: Could not create GitHub issue due to permissions: {e}")
                print("This may happen when running on non-default branches. Project will be tracked without issue.")

        return issue_number

    def _process_project(self, project: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single project and return updated project state"""
        project_name = project["project_name"]
        project_id = project["id"]
        project_title = project["title"]

        print(f"Processing project: {project_name} ({project_title})")

        # Check if this is a new project or needs issue creation
        if project_name not in state["projects"]:
            print(f"🆕 New project detected: {project_name}")

            issue_number = self._setup_project_issue(project_name, project_title, project.get("url", ""))

            # Initialize project state
            state["projects"][project_name] = {
                "project_id": project_id,
                "project_title": project_title,
                "issue_number": issue_number,
                "branch_name": ProjectExtractor.get_branch_name(project_name),
                "created_at": datetime.now().isoformat(),
                "images": {},
            }
        elif not state["projects"][project_name].get("issue_number"):
            # For existing projects, ensure we have an issue_number if one exists on GitHub
            try:
                existing_issue = self.github.find_existing_issue(project_name)
                if existing_issue:
                    state["projects"][project_name]["issue_number"] = existing_issue["number"]
                    print(f"Linked existing GitHub issue #{existing_issue['number']} to project")
            except PermissionError:
                pass  # Skip if no permissions

        # Sync photos for this project
        existing_images = state["projects"][project_name].get("images", {})
        new_images, total_count = self.sync_project_photos(project, existing_images)

        # Update state with new images
        for image in new_images:
            state["projects"][project_name]["images"][image["hash"]] = {
                "image_id": image["id"],
                "title": image["title"],
                "filename": image["filename"],
                "added_at": datetime.now().isoformat(),
            }

        # Update GitHub issue if there were changes
        if new_images and state["projects"][project_name].get("issue_number"):
            try:
                self.github.add_issue_comment(
                    state["projects"][project_name]["issue_number"],
                    project_name,
                    total_count,
                    len(new_images),
                )
            except PermissionError as e:
                print(f"⚠️  Warning: Could not update GitHub issue comment due to permissions: {e}")
                print("Photo sync completed but issue was not updated.")

        return state["projects"][project_name]

    def run(self) -> bool:
        """Main monitoring loop"""
        print("🔍 Starting construction project monitoring...")

        # Test photo client authentication
        if not self.photo_client.authenticate():
            print("❌ Photo service authentication failed.")
            return False

        # Load existing state
        state = self.state_manager.load_state()

        # Get all construction projects from photo service
        try:
            construction_projects = self.photo_client.get_construction_projects()
            print(f"Found {len(construction_projects)} construction projects")
        except Exception as e:
            print(f"Error getting construction projects: {e}")
            return False

        current_projects = {}

        # Process each project
        for project in construction_projects:
            project_name = project["project_name"]
            current_projects[project_name] = self._process_project(project, state)

        # Update state
        state["projects"] = current_projects
        state["last_scan"] = datetime.now().isoformat()
        self.state_manager.save_state(state)

        print(f"✅ Monitoring complete. Processed {len(current_projects)} active projects.")
        return True
