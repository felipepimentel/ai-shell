# logger.py
import logging
from functools import wraps
from typing import Callable

import structlog
from rich.console import Console


class LoggerManager:
    def __init__(self):
        pass

    def setup_logging(self, console: Console):
        self.console = console
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                self.friendly_console_output,
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        logging.basicConfig(
            format="%(message)s",
            level=logging.INFO,
            handlers=[logging.StreamHandler(), logging.FileHandler("ai_shell.log")],
        )

    def friendly_console_output(self, logger, method_name, event_dict):
        level = event_dict.get("level", "INFO").upper()
        timestamp = event_dict.get("timestamp", "N/A")
        event = event_dict.get("event", "No message")
        logger_name = event_dict.get("logger", "unknown")

        formatted_message = f"[{timestamp}] {level} - {event} ({logger_name})"
        self.console.print(formatted_message, style=level.lower())

        return event_dict

    def get_logger(self, name: str):
        return structlog.get_logger(name)


logger_manager = LoggerManager()


def setup_logging(console: Console):
    logger_manager.setup_logging(console)


def get_logger(name: str):
    return logger_manager.get_logger(name)


def exception_handler(func: Callable):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger = get_logger(func.__name__)
            logger.exception(f"Exception in {func.__name__}: {str(e)}")
            return None, f"An error occurred: {str(e)}"

    return wrapper
