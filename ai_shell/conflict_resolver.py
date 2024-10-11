import asyncio
import os
from enum import Enum
from typing import Optional


class ConflictResolution(Enum):
    REMOVE_AND_CONTINUE = "Remove existing and continue"
    RENAME_AND_CONTINUE = "Rename and continue"
    ABORT = "Abort operation"


async def detect_conflict(command: str) -> Optional[str]:
    if command.startswith(("mkdir", "touch", "cp", "mv")):
        path = command.split()[-1]
        if os.path.exists(path):
            return f"Path already exists: {path}"
    return None


async def resolve_conflict(
    conflict: str, resolution: ConflictResolution, original_command: str
) -> str:
    if resolution == ConflictResolution.REMOVE_AND_CONTINUE:
        path = original_command.split()[-1]
        await asyncio.to_thread(os.remove, path)
        return original_command
    elif resolution == ConflictResolution.RENAME_AND_CONTINUE:
        path = original_command.split()[-1]
        new_path = await _generate_unique_name(path)
        return original_command.replace(path, new_path)
    else:
        return "Operation aborted due to conflict."


async def _generate_unique_name(path: str) -> str:
    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(f"{base}_{counter}{ext}"):
        counter += 1
    return f"{base}_{counter}{ext}"
