import asyncio
import json
import os
import time
from typing import List, Optional

import aiofiles

from ..datatypes import CommandHistoryEntry


class CommandHistoryManager:
    def __init__(self) -> None:
        self.history: List[CommandHistoryEntry] = []

    def append_to_history(
        self,
        user_command: str,
        output: str,
        ai_response: Optional[str],
        status: str,
        error_message: Optional[str],
        used_cache: bool,
        tokens_used: Optional[int],
        model_used: Optional[str],
    ) -> None:
        self.history.append(
            CommandHistoryEntry(
                command=user_command,
                output=output,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                working_directory=os.getcwd(),
                ai_response=ai_response,
                status=status,
                error_message=error_message,
                used_cache=used_cache,
                tokens_used=tokens_used,
                model_used=model_used,
            )
        )
        asyncio.create_task(self.save_history())

    async def save_history(self) -> None:
        async with aiofiles.open("ai_command_history.json", "w") as f:
            await f.write(
                json.dumps([entry.__dict__ for entry in self.history], indent=2)
            )

    def get_recent_commands(self, limit: int = 10) -> List[str]:
        return [entry.command for entry in self.history[-limit:]]

    def clear_history(self) -> None:
        self.history.clear()
