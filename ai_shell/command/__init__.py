from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ..utils.logger import get_logger
from .command_cache_manager import CommandCacheManager
from .command_executor import CommandExecutor
from .command_generator import CommandGenerator
from .command_history_manager import CommandHistoryManager
from .command_processor import CommandProcessor
from .context_builder import ContextBuilder

if TYPE_CHECKING:
    pass

logger = get_logger("ai_shell.command")

MAX_RETRIES = 3

command_processor = CommandProcessor(
    CommandExecutor(max_workers=os.cpu_count()),
    CommandCacheManager(),
    CommandGenerator(),
    CommandHistoryManager(),
    ContextBuilder(),
)

__all__ = ["command_processor"]
