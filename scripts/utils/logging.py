"""
Centralized logging utility that combines Python standard logging with CLI-friendly emoji output.
Provides consistent messaging across all components while maintaining user-friendly experience.
"""

import logging
import sys
from typing import ClassVar
from typing import Optional


class EmojiFormatter(logging.Formatter):
    """Custom formatter that adds emojis to log messages based on level"""

    EMOJI_MAP: ClassVar[dict[int, str]] = {
        logging.INFO: "",  # Clean info messages
        logging.WARNING: "⚠️  ",
        logging.ERROR: "❌ ",
        logging.CRITICAL: "❌ ",
    }

    def format(self, record):
        # Add emoji prefix based on log level
        emoji = self.EMOJI_MAP.get(record.levelno, "")
        record.msg = f"{emoji}{record.msg}"
        return super().format(record)


class ProjectLogger:
    """Centralized logging utility that combines standard logging with CLI-friendly output"""

    def __init__(self, name: str = "nordhus-site"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Avoid duplicate handlers if logger already exists
        if not self.logger.handlers:
            # Console handler with emoji formatter for info/debug
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(EmojiFormatter("%(message)s"))
            self.logger.addHandler(console_handler)

            # Error handler for stderr with warnings and errors
            error_handler = logging.StreamHandler(sys.stderr)
            error_handler.setLevel(logging.WARNING)
            error_handler.setFormatter(EmojiFormatter("%(message)s"))
            self.logger.addHandler(error_handler)

    def success(self, message: str):
        """Green checkmark for significant milestones and completion"""
        print(f"✅ {message}")  # Direct print for success to maintain immediate feedback

    def info(self, message: str):
        """Clean informational messages without emojis"""
        self.logger.info(message)

    def warning(self, message: str):
        """Warning messages with ⚠️ emoji"""
        self.logger.warning(message)

    def error(self, message: str, exit_code: Optional[int] = None):
        """Error messages with ❌ emoji"""
        self.logger.error(message)
        if exit_code is not None:
            sys.exit(exit_code)

    def handle_exception(self, e: Exception, context: str, fatal: bool = False):
        """Standardized exception handling with context-aware messaging"""
        if isinstance(e, PermissionError):
            self.warning(f"Permission denied for {context}: {e}")
        elif isinstance(e, FileNotFoundError):
            self.error(f"File not found during {context}: {e}")
        elif isinstance(e, ConnectionError):
            self.error(f"Connection failed during {context}: {e}")
        else:
            self.error(f"Error in {context}: {e}")

        if fatal:
            sys.exit(1)


# Global logger instance for easy importing
logger = ProjectLogger()
