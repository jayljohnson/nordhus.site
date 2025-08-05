#!/usr/bin/env python3
"""
Git Operations Utility
Centralized git operations for construction project workflows.
Consolidates duplicated git functionality from project_manager and construction_workflow.
"""

import subprocess
from pathlib import Path
from typing import Optional

from .logging import logger


class GitOperations:
    """Centralized git operations for project management"""

    @staticmethod
    def ensure_git_config():
        """Ensure git user is configured for this repository"""
        try:
            subprocess.run(["git", "config", "user.name", "Construction Bot"], check=True)
            subprocess.run(["git", "config", "user.email", "noreply@nordhus.site"], check=True)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Could not set git config: {e}")

    @staticmethod
    def branch_exists_locally(branch_name: str) -> bool:
        """Check if branch exists locally"""
        try:
            result = subprocess.run(
                ["git", "branch", "--list", branch_name],
                check=False,
                capture_output=True,
                text=True,
            )
            return branch_name in result.stdout
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def branch_exists_remotely(branch_name: str) -> bool:
        """Check if branch exists on remote origin"""
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--heads", "origin", branch_name],
                check=False,
                capture_output=True,
                text=True,
            )
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def checkout_branch(branch_name: str) -> bool:
        """Switch to existing branch"""
        try:
            subprocess.run(["git", "checkout", branch_name], check=True)
            logger.info(f"Switched to existing branch: {branch_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error switching to branch {branch_name}: {e}")
            return False

    @staticmethod
    def fetch_and_checkout_remote_branch(branch_name: str) -> bool:
        """Fetch and checkout remote branch"""
        try:
            subprocess.run(["git", "fetch", "origin", branch_name], check=True)
            subprocess.run(
                ["git", "checkout", "-b", branch_name, f"origin/{branch_name}"],
                check=True,
            )
            logger.info(f"Checked out remote branch: {branch_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error checking out remote branch {branch_name}: {e}")
            return False

    @staticmethod
    def ensure_main_branch():
        """Ensure main branch exists locally and is up to date"""
        try:
            # Try to checkout main locally first
            subprocess.run(["git", "checkout", "main"], check=True)
        except subprocess.CalledProcessError:
            # If main doesn't exist locally, fetch it from origin
            subprocess.run(["git", "fetch", "origin", "main"], check=True)
            subprocess.run(["git", "checkout", "-b", "main", "origin/main"], check=True)

        # Update main branch
        subprocess.run(["git", "pull", "origin", "main"], check=True)

    @staticmethod
    def create_branch_from_main(branch_name: str) -> bool:
        """Create new branch from updated main"""
        try:
            GitOperations.ensure_main_branch()
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
            print(f"Created new branch: {branch_name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating branch {branch_name} from main: {e}")
            return False

    @staticmethod
    def create_or_switch_branch(branch_name: str) -> bool:
        """Create or switch to project branch with comprehensive logic"""
        try:
            if GitOperations.branch_exists_locally(branch_name):
                return GitOperations.checkout_branch(branch_name)
            elif GitOperations.branch_exists_remotely(branch_name):
                return GitOperations.fetch_and_checkout_remote_branch(branch_name)
            else:
                return GitOperations.create_branch_from_main(branch_name)
        except subprocess.CalledProcessError as e:
            print(f"Error managing branch {branch_name}: {e}")
            return False

    @staticmethod
    def commit_changes(project_dir: Path, commit_message: str, ensure_config: bool = True) -> bool:
        """Commit changes in project directory"""
        try:
            if ensure_config:
                GitOperations.ensure_git_config()

            subprocess.run(["git", "add", str(project_dir)], check=True)
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            print(f"Committed changes: {commit_message}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error committing changes: {e}")
            raise  # Re-raise to fail the workflow properly

    @staticmethod
    def add_and_commit_files(files: list, commit_message: str, ensure_config: bool = True) -> bool:
        """Add specific files and commit with message"""
        try:
            if ensure_config:
                GitOperations.ensure_git_config()

            # Convert all file paths to strings
            file_paths = [str(f) for f in files]
            subprocess.run(["git", "add", *file_paths], check=True)
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            print(f"Committed files: {commit_message}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error committing files: {e}")
            return False

    @staticmethod
    def get_project_branch(project_name: str, date_prefix: Optional[str] = None) -> str:
        """Generate project branch name with optional date prefix"""
        if date_prefix is None:
            from datetime import datetime

            date_prefix = datetime.now().strftime("%Y-%m-%d")
        return f"project/{date_prefix}-{project_name}"
