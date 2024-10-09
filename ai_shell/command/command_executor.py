import asyncio
import os
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, Tuple


class CommandExecutor:
    def __init__(self, max_workers: Optional[int] = None) -> None:
        self.executor = ProcessPoolExecutor(max_workers=max_workers or os.cpu_count())

    async def execute_command(self, command: str, timeout: int) -> Tuple[str, int]:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            return (
                stdout.decode().strip() or stderr.decode().strip(),
                process.returncode,
            )
        except asyncio.TimeoutError:
            process.terminate()
            await process.wait()
            return "Error: Command timed out", 1
