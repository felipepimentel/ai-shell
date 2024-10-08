import logging

import structlog

from ..config import config


class LoggerManager:
    def __init__(self):
        self.console = None

    def setup_logging(self, console=None):
        self.console = console
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

    def get_logger(self, name: str):
        logger = structlog.get_logger(name)
        if config.verbose_mode:
            logger = logger.bind(verbose=True)
        return logger


logger_manager = LoggerManager()


def setup_logging(console=None):
    logger_manager.setup_logging(console)


def get_logger(name: str):
    return logger_manager.get_logger(name)
