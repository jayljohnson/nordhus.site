"""
Centralized configuration and environment variable management.
Provides consistent access to environment variables and feature flags across all components.
"""

import os
from typing import List
from typing import Optional


class Config:
    """Centralized configuration and environment variable management"""

    @staticmethod
    def is_photo_monitoring_enabled() -> bool:
        """Check if photo monitoring feature is enabled"""
        return os.environ.get("ENABLE_PHOTO_MONITORING", "false").lower() == "true"

    @staticmethod
    def enable_photo_monitoring():
        """Enable photo monitoring for the current session"""
        os.environ["ENABLE_PHOTO_MONITORING"] = "true"

    @staticmethod
    def get_github_token() -> Optional[str]:
        """Get GitHub API token for issue and PR management"""
        return os.environ.get("GITHUB_TOKEN")

    @staticmethod
    def get_cloudinary_url() -> Optional[str]:
        """Get Cloudinary service URL for photo operations"""
        return os.environ.get("CLOUDINARY_URL")

    @staticmethod
    def validate_required_env() -> List[str]:
        """Return list of missing required environment variables"""
        missing = []
        if Config.is_photo_monitoring_enabled():
            if not Config.get_cloudinary_url():
                missing.append("CLOUDINARY_URL")
            if not Config.get_github_token():
                missing.append("GITHUB_TOKEN")
        return missing

    @staticmethod
    def validate_or_exit():
        """Validate required environment variables, exit if missing"""
        from .logging import logger

        missing = Config.validate_required_env()
        if missing:
            logger.error(f"Missing required environment variables: {', '.join(missing)}", exit_code=1)
