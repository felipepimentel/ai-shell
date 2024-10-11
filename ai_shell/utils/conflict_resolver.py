from enum import Enum
from typing import Optional
import os
import shutil
import asyncio

class ConflictResolution(Enum):
    REMOVE_AND_CLONE = "Remove existing directory and clone"
    CLONE_DIFFERENT_LOCATION = "Clone to a different location"

async def detect_conflict(command: str) -> Optional[str]:
    if command.startswith("git clone"):
        path = command.split()[-1]
        if os.path.exists(path):
            return f"Path already exists: {path}"
    elif command.startswith(("mkdir", "touch")):
        path = command.split()[-1]
        if os.path.exists(path):
            return f"Path already exists: {path}"
    elif command.startswith(("mv", "cp")):
        dest = command.split()[-1]
        if os.path.exists(dest):
            return f"Destination already exists: {dest}"
    return None

async def resolve_conflict(conflict: str, resolution: ConflictResolution, original_command: str) -> str:
    if resolution == ConflictResolution.REMOVE_AND_CLONE:
        path = original_command.split()[-1]
        await asyncio.to_thread(shutil.rmtree, path, ignore_errors=True)
        return original_command
    elif resolution == ConflictResolution.CLONE_DIFFERENT_LOCATION:
        path = original_command.split()[-1]
        new_path = await clone_different_location(path)
        return original_command.replace(path, new_path)
    else:
        raise ValueError(f"Invalid resolution option: {resolution}")

async def clone_different_location(path: str) -> str:
    base, name = os.path.split(path)
    new_name = f"{name}_new"
    new_path = os.path.join(base, new_name)
    return new_path