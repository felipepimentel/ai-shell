import os
import subprocess
from typing import Optional, Tuple

from ai_shell.utils.logger import get_logger

logger = get_logger("ai_shell.error_handler")


def handle_error(error: Exception) -> Tuple[str, Optional[str]]:
    error_message = str(error)
    suggestion = None

    if isinstance(error, FileNotFoundError):
        suggestion = f"File not found: {error.filename}. Check if the file exists and you have the necessary permissions."
    elif isinstance(error, PermissionError):
        suggestion = f"Permission denied: {error.filename}. Try running the command with 'sudo' or check file permissions."
    elif isinstance(error, ImportError):
        module = str(error).split("'")[1]
        suggestion = f"Module '{module}' is missing. Try installing it using 'pip install {module}'."
    elif isinstance(error, subprocess.CalledProcessError):
        suggestion = f"Command '{error.cmd}' failed with exit code {error.returncode}. Check the command syntax and try again."
    elif isinstance(error, TimeoutError):
        suggestion = "The operation timed out. Check your network connection or increase the timeout limit."
    elif isinstance(error, KeyboardInterrupt):
        suggestion = "Operation was interrupted by the user. You can restart the command if needed."
    elif isinstance(error, MemoryError):
        suggestion = "The system ran out of memory. Try closing other applications or increasing available memory."
    elif isinstance(error, OSError):
        suggestion = f"OS error: {os.strerror(error.errno)}. Check system resources and permissions."
    else:
        logger.error(f"Unhandled error: {error_message}")
        suggestion = (
            "An unexpected error occurred. Please check the logs for more information."
        )

    return error_message, suggestion


def log_error(error: Exception, context: dict = None):
    logger.error(f"Error occurred: {str(error)}", extra=context)


def suggest_fix(error: Exception) -> str:
    _, suggestion = handle_error(error)
    return suggestion or "No specific suggestion available for this error."
