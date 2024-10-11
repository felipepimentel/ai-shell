from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from datetime import datetime


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
    timestamp: datetime = datetime.now()  # Adicionamos o campo timestamp com um valor padrão


class ErrorType(Enum):
    FATAL = "FATAL"
    USER_INPUT = "USER_INPUT"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class AIShellResult:
    success: bool
    message: str
