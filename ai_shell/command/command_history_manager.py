import asyncio
import json
from datetime import datetime
from typing import List, Optional

import aiofiles

from ..datatypes import CommandHistoryEntry


class CommandHistoryManager:
    def __init__(self, max_history_size: int = 100) -> None:
        self.history: List[CommandHistoryEntry] = []
        self.max_history_size = max_history_size

    def append_to_history(
        self,
        command: str,
        output: str,
        ai_response: str,
        status: str,
        error_message: Optional[str],
        used_cache: bool,
        tokens_used: Optional[int],
        model_used: Optional[str],
    ) -> None:
        entry = CommandHistoryEntry(
            command=command,
            output=output,
            ai_response=ai_response,
            status=status,
            error_message=error_message,
            used_cache=used_cache,
            tokens_used=tokens_used,
            model_used=model_used,
            timestamp=datetime.now(),
        )
        self.history.append(entry)
        if len(self.history) > self.max_history_size:
            self.history.pop(0)
        asyncio.create_task(self.save_history())

    async def save_history(self) -> None:
        async with aiofiles.open("ai_command_history.json", "w") as f:
            await f.write(
                json.dumps(
                    [entry.__dict__ for entry in self.history], indent=2, default=str
                )
            )

    def get_recent_commands(self, limit: int = 10) -> List[str]:
        return [entry.command for entry in self.history[-limit:]]

    def clear_history(self) -> None:
        self.history.clear()
        asyncio.create_task(self.save_history())
