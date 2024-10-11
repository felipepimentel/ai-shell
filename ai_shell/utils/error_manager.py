import os
import subprocess
from typing import Any, Dict, Optional, Tuple

from ..utils.logger import get_logger

logger = get_logger(__name__)


def analyze_and_handle_error(
    error: Exception, context: Dict[str, Any] = None
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Analyze and handle the given error, returning error message, suggestion, and analysis.
    """
    error_analysis = analyze_error(error)
    error_message, suggestion = handle_error(error)
    log_error(error, context)

    return error_message, suggestion, error_analysis


def analyze_error(error: Exception) -> Dict[str, Any]:
    """
    Analyze the given error and return a dictionary with error details.
    """
    error_analysis = {
        "type": type(error).__name__,
        "message": str(error),
        "details": {},
    }

    if isinstance(error, ImportError):
        error_analysis["details"]["missing_module"] = str(error).split("'")[1]
    elif isinstance(error, FileNotFoundError):
        error_analysis["details"]["file_path"] = error.filename
    elif isinstance(error, PermissionError):
        error_analysis["details"]["file_path"] = error.filename
    elif isinstance(error, subprocess.CalledProcessError):
        error_analysis["details"]["command"] = error.cmd
        error_analysis["details"]["return_code"] = error.returncode
    elif isinstance(error, TimeoutError):
        error_analysis["details"]["operation"] = "Timed out"
    elif isinstance(error, MemoryError):
        error_analysis["details"]["resource"] = "Memory"
    elif isinstance(error, OSError):
        error_analysis["details"]["errno"] = error.errno
        error_analysis["details"]["strerror"] = os.strerror(error.errno)

    return error_analysis


def handle_error(error: Exception) -> Tuple[str, str]:
    """
    Handle the error and return an error message and suggestion.
    """
    error_message = str(error)
    suggestion = suggest_fix(error)

    return error_message, suggestion


def suggest_fix(error: Exception) -> str:
    """
    Suggest a fix based on the error type and details.
    """
    if isinstance(error, FileNotFoundError):
        return f"File not found: {error.filename}. Check if the file exists and you have the necessary permissions."
    elif isinstance(error, PermissionError):
        return f"Permission denied: {error.filename}. Try running the command with 'sudo' or check file permissions."
    elif isinstance(error, ImportError):
        module = str(error).split("'")[1]
        return f"Module '{module}' is missing. Try installing it using 'pip install {module}'."
    elif isinstance(error, subprocess.CalledProcessError):
        return f"Command '{error.cmd}' failed with exit code {error.returncode}. Check the command syntax and try again."
    elif isinstance(error, TimeoutError):
        return "The operation timed out. Check your network connection or increase the timeout limit."
    elif isinstance(error, KeyboardInterrupt):
        return "Operation was interrupted by the user. You can restart the command if needed."
    elif isinstance(error, MemoryError):
        return "The system ran out of memory. Try closing other applications or increasing available memory."
    elif isinstance(error, OSError):
        return f"OS error: {os.strerror(error.errno)}. Check system resources and permissions."
    else:
        return (
            "An unexpected error occurred. Please check the logs for more information."
        )


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
    """
    Log the error with additional context if provided.
    """
    error_analysis = analyze_error(error)
    log_message = (
        f"Error occurred: {error_analysis['type']} - {error_analysis['message']}"
    )

    if context:
        log_message += f"\nContext: {context}"

    logger.error(log_message, extra={"error_analysis": error_analysis})
