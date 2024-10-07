import logging
import sys
import traceback
from functools import wraps
from typing import Callable, Dict, Optional

import structlog

logger = structlog.get_logger()


def exception_handler(func: Callable):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = traceback.extract_tb(exc_traceback)
            filename, line_number, _, _ = tb[-1]
            error_message = f"Exception in {filename}, line {line_number}: {str(e)}"
            logger.error(error_message)
            return handle_error(error_message)

    return wrapper


class ErrorHandler:
    def __init__(
        self, config: Dict[str, str], llm_assistant: Optional[Callable] = None
    ):
        self.pattern_handlers = config.get("pattern_handlers", {})
        self.use_llm = config.get("use_llm", False)
        self.fallback_message = config.get(
            "fallback_message",
            "An error occurred. Please check your command and try again.",
        )
        self.llm_assistant = llm_assistant

    def handle(self, error_message: str, context: Optional[Dict] = None) -> str:
        # Check pattern-based handlers
        for pattern, solution in self.pattern_handlers.items():
            if pattern.lower() in error_message.lower():
                return solution

        if self.use_llm and self.llm_assistant:
            return self.llm_assistant.generate_command(
                f"Error: {error_message}. Suggest a solution.", context or {}
            )

        return self.fallback_message


class CriticalErrorHandler(ErrorHandler):
    def __init__(
        self, config: Dict[str, str], llm_assistant: Optional[Callable] = None
    ):
        super().__init__(config, llm_assistant)

    def handle_critical(
        self, error_message: str, context: Optional[Dict] = None
    ) -> str:
        logger.critical(f"Critical error occurred: {error_message}")
        return self.handle(error_message, context)


def create_error_handler(
    config: Dict[str, str], llm_assistant: Optional[Callable] = None
) -> ErrorHandler:
    return CriticalErrorHandler(config, llm_assistant)


def handle_error(error_message: str):
    """
    Simplified error handler that logs the error message and provides a default response.
    """
    logger.error(error_message)
    return None, f"An error occurred: {error_message}"


def setup_logging():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )
