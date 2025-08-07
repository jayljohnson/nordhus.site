#!/usr/bin/env python3
"""
Simplified Construction Project Monitor for GitHub Actions
Scans Cloudinary folders and syncs photos to project branches.
"""

import os
import sys

from clients.cloudinary_client import CloudinaryClient
from project.project_manager import SimpleProjectManager
from utils.logging import logger
from workflows.construction_workflow import GitHubManager


def get_photo_client():
    """Legacy function for backward compatibility"""
    from clients.cloudinary_client import CloudinaryClient
    from clients.cloudinary_client import CloudinaryHasher

    return CloudinaryClient(), CloudinaryHasher()


def _setup_github_manager():
    """Initialize GitHub manager if token is available"""
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        return None

    try:
        return GitHubManager(github_token, "jayljohnson", "nordhus.site")
    except Exception as e:
        logger.warning(f"GitHub integration disabled: {e}")
        return None


def _handle_project_issue(github_manager, project_name: str, project_title: str, project_url: str):
    """Create or find GitHub issue for project"""
    if not github_manager:
        return 0

    try:
        # Try to find existing issue first
        existing_issue = github_manager.find_existing_issue(project_name)
        if existing_issue:
            issue_number = existing_issue["number"]
            logger.info(f"Found existing issue #{issue_number}: Construction Project: {project_title}")
            return issue_number

        # Create new issue
        new_issue = github_manager.create_issue(project_name, project_title, project_url)
        if new_issue:
            issue_number = new_issue["number"]
            logger.info(f"Created GitHub issue #{issue_number}")
            return issue_number
    except Exception as e:
        logger.error(f"GitHub issue management failed: {e}")

    return 0


def _sync_project_photos(manager, github_manager, project_name: str, issue_number: int):
    """Sync photos and update GitHub issue"""
    new_photos = manager.sync_photos_from_cloudinary()

    if new_photos > 0:
        logger.success(f"Synced {new_photos} new photos for project: {project_name}")

        # Add issue comment for sync update
        if github_manager and issue_number > 0:
            try:
                github_manager.add_issue_comment(issue_number, project_name, 0, new_photos)
            except Exception as e:
                logger.warning(f"Failed to update GitHub issue: {e}")
        return True
    else:
        logger.info(f"No new photos for project: {project_name}")
        return False


def scan_and_sync_projects() -> bool:
    """Scan all Cloudinary folders for construction projects and sync photos"""
    try:
        client = CloudinaryClient()

        # Test authentication
        if not client.authenticate():
            logger.error("Cloudinary authentication failed")
            return False

        # Get all construction projects (folders with project patterns)
        projects = client.get_construction_projects()
        logger.info(f"Found {len(projects)} construction projects")

        if not projects:
            logger.info("No construction project folders found")
            return True

        # Initialize GitHub manager
        github_manager = _setup_github_manager()

        active_projects = 0
        synced_projects = 0

        # Process each project
        for project in projects:
            project_name = project["project_name"]
            project_title = project.get("title", project_name)
            project_url = project.get("url", "")

            logger.info(f"Processing project: {project_name} ({project_title})")

            # Create project manager
            manager = SimpleProjectManager(project_name)

            # Auto-create project if it doesn't exist yet
            if not manager.project_directory.exists():
                logger.info(f"🆕 New project detected: {project_name}")

            # Handle GitHub issue creation/finding
            issue_number = _handle_project_issue(github_manager, project_name, project_title, project_url)

            # Switch to project branch
            if not manager.create_project_branch():
                logger.error(f"Could not access project branch for {project_name}")
                continue

            active_projects += 1

            # Sync photos and update issue
            if _sync_project_photos(manager, github_manager, project_name, issue_number):
                synced_projects += 1

        logger.info(f"✅ Monitoring complete. Processed {active_projects} active projects.")
        if synced_projects > 0:
            logger.info(f"Updated {synced_projects} projects with new photos.")
        return True

    except Exception as e:
        logger.error(f"Project monitoring failed: {e}")
        return False


def main():
    """Main entry point for simplified construction project monitoring"""
    # Check feature flag
    photo_monitoring_enabled = os.environ.get("ENABLE_PHOTO_MONITORING", "false").lower() == "true"
    if not photo_monitoring_enabled:
        logger.info("Photo monitoring is disabled via ENABLE_PHOTO_MONITORING environment variable")
        logger.info("Set ENABLE_PHOTO_MONITORING=true to enable photo monitoring")
        return True  # Exit successfully when disabled

    logger.info("🔍 Starting simplified construction project monitoring...")

    return scan_and_sync_projects()


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Monitor error: {e}")
        sys.exit(1)
