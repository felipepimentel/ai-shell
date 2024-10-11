from typing import Any, Dict


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

    return error_analysis


def suggest_fix(error_analysis: Dict[str, Any], context: Dict[str, Any]) -> str:
    """
    Suggest a fix based on the error analysis and context.
    """
    error_type = error_analysis["type"]

    if error_type == "ImportError":
        missing_module = error_analysis["details"].get("missing_module")
        return f"Try installing the missing module: pip install {missing_module}"
    elif error_type == "FileNotFoundError":
        file_path = error_analysis["details"].get("file_path")
        return f"Check if the file exists and the path is correct: {file_path}"
    elif error_type == "PermissionError":
        file_path = error_analysis["details"].get("file_path")
        return f"Check the permissions of the file or directory: {file_path}"
    else:
        return "Unable to suggest a specific fix. Please check the error message and your code."
