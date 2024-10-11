import logging
import traceback
from contextlib import asynccontextmanager

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
        self.console = None
        self.logger = self._configure_logger()

    def _configure_logger(self):
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

        # Remove the StreamHandler to prevent duplicate console output
        logging.basicConfig(
            format="%(message)s",
            level=logging.DEBUG if config.verbose_mode else logging.INFO,
            handlers=[logging.FileHandler("ai_shell.log")],  # Apenas log em arquivo
        )

        return structlog.get_logger()

    def setup_logging(self, console=None):
        self.console = console
        # The logger is already configured in __init__, so we don't need to do anything here

    def get_logger(self, name: str):
        return self.logger.bind(module=name)


logger_manager = LoggerManager()


def setup_logging(console=None):
    logger_manager.setup_logging(console)


def get_logger(name: str):
    return logger_manager.get_logger(name)


def log_error(message: str):
    logger = get_logger("error")
    logger.error(message)


def log_info(message: str):
    logger = get_logger("info")
    logger.info(message)
