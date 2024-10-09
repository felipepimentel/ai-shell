from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


@dataclass
class CommandResult:
    commands: List[str]
    results: List[str]


@dataclass
class CommandHistoryEntry:
    command: str
    output: str
    timestamp: str
    working_directory: str
    ai_response: Optional[str]
    status: str
    error_message: Optional[str]
    used_cache: bool
    tokens_used: Optional[int]
    model_used: Optional[str]


class ErrorType(Enum):
    FATAL = "FATAL"
    USER_INPUT = "USER_INPUT"
    WARNING = "WARNING"
    INFO = "INFO"
