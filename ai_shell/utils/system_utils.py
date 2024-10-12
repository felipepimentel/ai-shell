import asyncio
import os
import platform
import pwd
import shutil
from typing import Optional, Tuple


async def get_system_info():
    try:
        user = os.getlogin()
    except OSError:
        user = pwd.getpwuid(os.getuid())[0]

    await asyncio.sleep(0)

    return {
        "os": platform.system(),
        "os_version": platform.release(),
        "user": user,
        "current_directory": os.getcwd(),
        "shell": os.getenv("SHELL", "unknown"),
        "python_version": platform.python_version(),
    }


async def run_process(command: str) -> Tuple[int, str, str]:
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return process.returncode, stdout.decode(), stderr.decode()


async def check_system_dependency(dep: str) -> bool:
    return await asyncio.to_thread(shutil.which, dep) is not None


async def create_directory(path: str) -> bool:
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError as e:
        print(f"Error creating directory {path}: {e}")
        return False


async def remove_file(path: str) -> bool:
    try:
        os.remove(path)
        return True
    except OSError as e:
        print(f"Error removing file {path}: {e}")
        return False


async def rename_file(old_path: str, new_path: str) -> bool:
    try:
        os.rename(old_path, new_path)
        return True
    except OSError as e:
        print(f"Error renaming file from {old_path} to {new_path}: {e}")
        return False


async def get_file_content(file_path: str) -> Optional[str]:
    try:
        with open(file_path, "r") as file:
            return await asyncio.to_thread(file.read)
    except IOError as e:
        print(f"Error reading file {file_path}: {e}")
        return None


async def write_file_content(file_path: str, content: str) -> bool:
    try:
        with open(file_path, "w") as file:
            await asyncio.to_thread(file.write, content)
        return True
    except IOError as e:
        print(f"Error writing to file {file_path}: {e}")
        return False
