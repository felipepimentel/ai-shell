from dataclasses import dataclass
from datetime import datetime
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
    ai_response: str
    status: str
    error_message: Optional[str]
    used_cache: bool
    tokens_used: Optional[int]
    model_used: Optional[str]
    timestamp: datetime = datetime.now()


class ErrorType(Enum):
    FATAL = "FATAL"
    USER_INPUT = "USER_INPUT"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class AIShellResult:
    success: bool
    message: str


class CommandGenerationError(Exception):
    pass


class ConflictResolution(Enum):
    REMOVE = "Remove existing and continue"
    RENAME = "Rename and continue"
    ABORT = "Abort operation"


@dataclass
class HistoryEntry:
    command: str
    output: str
    ai_response: str
    status: str
    timestamp: str
