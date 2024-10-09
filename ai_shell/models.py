from dataclasses import dataclass
from typing import Optional

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
