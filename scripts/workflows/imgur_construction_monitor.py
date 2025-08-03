#!/usr/bin/env python3
"""
Imgur Construction Project Monitor for GitHub Actions
Monitors Imgur albums for construction projects and
    manages git branches/issues automatically.
"""

import os
import sys
from pathlib import Path

from clients.imgur_client import ImgurClient
from clients.imgur_client import ImgurHasher
from workflows.construction_workflow import ConstructionWorkflow


def main():
    """Main entry point for Imgur construction monitoring"""
    # Check feature flag
    photo_monitoring_enabled = os.environ.get("ENABLE_PHOTO_MONITORING", "false").lower() == "true"
    if not photo_monitoring_enabled:
        print("Photo monitoring is disabled via ENABLE_PHOTO_MONITORING environment variable")
        print("Set ENABLE_PHOTO_MONITORING = true to enable photo album integration")
        return

    # Get environment variables
    github_token = os.environ.get("GITHUB_TOKEN")
    imgur_client_id = os.environ.get("IMGUR_CLIENT_ID")
    imgur_client_secret = os.environ.get("IMGUR_CLIENT_SECRET")
    imgur_access_token = os.environ.get("IMGUR_ACCESS_TOKEN")

    # Validate required environment variables
    if not github_token:
        raise Exception("GITHUB_TOKEN environment variable required")
    if not imgur_client_id:
        raise Exception("IMGUR_CLIENT_ID environment variable required")

    # Configuration
    repo_owner = "jayljohnson"  # Update with your GitHub username
    repo_name = "nordhus.site"
    state_file = Path(".github/imgur-project-state.json")

    # Initialize clients
    photo_client = ImgurClient(
        client_id=imgur_client_id,
        client_secret=imgur_client_secret,
        access_token=imgur_access_token,
    )

    project_hasher = ImgurHasher()

    # Initialize workflow
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
