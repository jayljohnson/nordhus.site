#!/usr/bin/env python3
"""
Generic Construction Project Monitor for GitHub Actions
Monitors photo albums/folders for construction projects and
manages git branches/issues automatically.

Supports multiple photo service backends (Imgur, Cloudinary, etc.)
"""

import os
import sys
from pathlib import Path


def get_photo_client():
    """Get Cloudinary photo client"""
    # Check for Cloudinary credentials
    if os.getenv("CLOUDINARY_URL") or all([os.getenv("CLOUDINARY_CLOUD_NAME"), os.getenv("CLOUDINARY_API_KEY"), os.getenv("CLOUDINARY_API_SECRET")]):
        print("🌤️  Using Cloudinary photo service")
        from clients.cloudinary_client import CloudinaryClient
        from clients.cloudinary_client import CloudinaryHasher

        return CloudinaryClient(), CloudinaryHasher()

    else:
        raise ValueError("Cloudinary credentials not found. Set environment variable:\n" "CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name")


def main():
    """Main entry point for construction project monitoring"""
    # Check feature flag
    photo_monitoring_enabled = os.environ.get("ENABLE_PHOTO_MONITORING", "false").lower() == "true"
    if not photo_monitoring_enabled:
        print("Photo monitoring is disabled via ENABLE_PHOTO_MONITORING environment variable")
        print("Set ENABLE_PHOTO_MONITORING=true to enable photo album integration")
        return

    # Get environment variables
    github_token = os.environ.get("GITHUB_TOKEN")

    # Validate required environment variables
    if not github_token:
        raise Exception("GITHUB_TOKEN environment variable required")

    try:
        # Get photo client and hasher based on available credentials
        photo_client, project_hasher = get_photo_client()
    except ValueError as e:
        print(f"❌ Photo service configuration error: {e}")
        return False

    # Configuration
    repo_owner = "jayljohnson"  # Update with your GitHub username
    repo_name = "nordhus.site"
    state_file = Path(".github/construction-project-state.json")

    # Initialize workflow
    from workflows.construction_workflow import ConstructionWorkflow

    workflow = ConstructionWorkflow(
        photo_client=photo_client,
        project_hasher=project_hasher,
        github_token=github_token,
        repo_owner=repo_owner,
        repo_name=repo_name,
        state_file=state_file,
    )

    # Run the workflow
    return workflow.run()


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
