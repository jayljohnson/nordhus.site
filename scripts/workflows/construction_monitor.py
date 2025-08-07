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


def get_photo_client():
    """Legacy function for backward compatibility"""
    from clients.cloudinary_client import CloudinaryClient
    from clients.cloudinary_client import CloudinaryHasher

    return CloudinaryClient(), CloudinaryHasher()


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
        logger.info(f"Found {len(projects)} potential construction projects")

        if not projects:
            logger.info("No construction project folders found")
            return True

        synced_projects = 0

        # Process each project
        for project in projects:
            project_name = project["project_name"]
            logger.info(f"Processing project: {project_name}")

            # Create project manager
            manager = SimpleProjectManager(project_name)

            # Check if project directory exists (project was started)
            if not manager.project_directory.exists():
                logger.info(f"Project {project_name} not started yet - skipping")
                continue

            # Switch to project branch
            if not manager.create_project_branch():  # This also switches if exists
                logger.error(f"Could not access project branch for {project_name}")
                continue

            # Sync photos from Cloudinary
            new_photos = manager.sync_photos_from_cloudinary()

            if new_photos > 0:
                logger.success(f"Synced {new_photos} new photos for project: {project_name}")
                synced_projects += 1
            else:
                logger.info(f"No new photos for project: {project_name}")

        logger.info(f"Completed scan. Updated {synced_projects} projects with new photos.")
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
