import functools
import inspect
import logging
import traceback
from contextlib import asynccontextmanager
from functools import wraps
from logging.handlers import RotatingFileHandler
from typing import Any, Callable

import structlog
from rich.console import Console

from ..config import config


class ErrorHandler:
    def __init__(self, console: Console):
        self.console = console

    @asynccontextmanager
    async def catch_errors(self):
        try:
            yield
        except (KeyboardInterrupt, SystemExit):
            self.console.print("[red]Execution interrupted.[/red]")
        except Exception as e:
            self.console.print(f"[red]Unexpected error: {str(e)}[/red]")
            traceback.print_exc()


class LoggerManager:
    def __init__(self):
        self.console: Console | None = None
        self.logger = self._configure_logger()

    def _configure_logger(self) -> structlog.BoundLogger:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        log_file = config.log_file_path
        max_bytes = config.log_max_bytes
        backup_count = config.log_backup_count

        handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )

        logging.basicConfig(
            format="%(message)s",
            level=logging.DEBUG if config.verbose_mode else logging.INFO,
            handlers=[handler],
        )

        return structlog.get_logger()

    def setup_logging(self, console: Console | None = None) -> None:
        self.console = console

    def get_logger(self, name: str) -> structlog.BoundLogger:
        return self.logger.bind(module=name, host=config.hostname)


logger_manager = LoggerManager()


def setup_logging(console: Console | None = None) -> None:
    logger_manager.setup_logging(console)


def get_logger(name: str) -> structlog.BoundLogger:
    return logger_manager.get_logger(name)


def log_error(message: str) -> None:
    logger = get_logger("error")
    logger.error(message)


def log_info(message: str) -> None:
    logger = get_logger("info")
    logger.info(message)


def class_logger(cls: Any) -> Any:
    logger = get_logger(cls.__name__)

    for name, method in inspect.getmembers(cls, inspect.isfunction):
        if name.startswith("__"):
            continue

        @functools.wraps(method)
        def wrapper(original_method: Callable) -> Callable:
            if inspect.iscoroutinefunction(original_method):

                async def async_wrapped(*args: Any, **kwargs: Any) -> Any:
                    logger.debug(f"Entering {cls.__name__}.{original_method.__name__}")
                    try:
                        result = await original_method(*args, **kwargs)
                        logger.debug(
                            f"Exiting {cls.__name__}.{original_method.__name__}"
                        )
                        return result
                    except Exception as e:
                        logger.exception(
                            f"Exception in {cls.__name__}.{original_method.__name__}: {str(e)}"
                        )
                        raise

                return async_wrapped
            else:

                def sync_wrapped(*args: Any, **kwargs: Any) -> Any:
                    logger.debug(f"Entering {cls.__name__}.{original_method.__name__}")
                    try:
                        result = original_method(*args, **kwargs)
                        logger.debug(
                            f"Exiting {cls.__name__}.{original_method.__name__}"
                        )
                        return result
                    except Exception as e:
                        logger.exception(
                            f"Exception in {cls.__name__}.{original_method.__name__}: {str(e)}"
                        )
                        raise

                return sync_wrapped

        setattr(cls, name, wrapper(method))

    return cls


def function_logger(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__name__)
        logger.info(f"Entering {func.__name__}", args=args, kwargs=kwargs)
        result = await func(*args, **kwargs)
        logger.info(f"Exiting {func.__name__}", result=result)
        return result

    return wrapper
