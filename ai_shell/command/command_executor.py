import asyncio
import os
import signal
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, Tuple, Callable, List
import shlex

from ..utils.logger import get_logger

logger = get_logger(__name__)

class CommandExecutor:
    def __init__(self, max_workers: Optional[int] = None) -> None:
        self.executor = ProcessPoolExecutor(max_workers=max_workers or os.cpu_count())

    async def execute_command(self, command: str, simulation_mode: bool, verbose_mode: bool) -> str:
        if simulation_mode:
            return await self.simulate_command(command)
        else:
            return await self.execute_command_with_timeout(command, timeout=300)  # 5 minutes timeout

    async def simulate_command(self, command: str) -> Tuple[str, int]:
        args = shlex.split(command)
        simulated_output = f"[Simulation] Would execute: {command}\n"

        if args[0] == "rm":
            simulated_output += self.simulate_rm(args)
        elif args[0] == "git":
            simulated_output += self.simulate_git(args)
        elif args[0] == "mkdir":
            simulated_output += self.simulate_mkdir(args)
        elif args[0] == "cp" or args[0] == "mv":
            simulated_output += self.simulate_file_operation(args)
        elif args[0] == "chmod":
            simulated_output += self.simulate_chmod(args)
        elif args[0] == "chown":
            simulated_output += self.simulate_chown(args)
        elif args[0] == "ls":
            simulated_output += self.simulate_ls(args)
        elif args[0] == "cat":
            simulated_output += self.simulate_cat(args)
        elif args[0] == "echo":
            simulated_output += self.simulate_echo(args)
        elif args[0] == "touch":
            simulated_output += self.simulate_touch(args)
        else:
            simulated_output += f"[Simulation] Would execute unknown command: {args[0]}"

        return simulated_output, 0

    async def execute_command_with_timeout(self, command: str, timeout: int, progress_callback: Optional[Callable[[int], None]] = None) -> Tuple[str, int]:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            start_time = asyncio.get_event_loop().time()
            output = []
            async for line in process.stdout:
                output.append(line.decode().strip())
                if progress_callback:
                    elapsed_time = asyncio.get_event_loop().time() - start_time
                    progress = min(int((elapsed_time / timeout) * 100), 99)
                    progress_callback(progress)

                if asyncio.get_event_loop().time() - start_time > timeout:
                    process.terminate()
                    return "Error: Command execution timed out", 1

            await process.wait()
            if progress_callback:
                progress_callback(100)

            if process.returncode != 0:
                error_output = await process.stderr.read()
                output.append(error_output.decode().strip())

            return "\n".join(output), process.returncode
        except asyncio.CancelledError:
            process.terminate()
            return "Error: Command execution was cancelled", 1

    async def execute_long_running_command(self, command: str, timeout: int, progress_callback: Callable[[str], None] = None) -> Tuple[str, int]:
        return await self.execute_command(command, timeout, progress_callback)

    async def cancel_command(self, process):
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)

    @staticmethod
    def simulate_rm(args: List[str]) -> str:
        if "-rf" in args:
            return f"[Simulation] Would recursively remove: {', '.join(args[2:])}"
        else:
            return f"[Simulation] Would remove: {', '.join(args[1:])}"

    @staticmethod
    def simulate_git(args: List[str]) -> str:
        if args[1] == "reset":
            return f"[Simulation] Would reset Git repository to: {args[2]}"
        elif args[1] == "clone":
            return f"[Simulation] Would clone repository from: {args[2]}"
        elif args[1] == "push":
            return f"[Simulation] Would push changes to remote repository"
        elif args[1] == "pull":
            return f"[Simulation] Would pull changes from remote repository"
        else:
            return f"[Simulation] Would execute Git command: {' '.join(args[1:])}"

    @staticmethod
    def simulate_mkdir(args: List[str]) -> str:
        return f"[Simulation] Would create directory: {args[1]}"

    @staticmethod
    def simulate_file_operation(args: List[str]) -> str:
        operation = "copy" if args[0] == "cp" else "move"
        return f"[Simulation] Would {operation} {args[1]} to {args[2]}"

    @staticmethod
    def simulate_chmod(args: List[str]) -> str:
        return f"[Simulation] Would change permissions: chmod {' '.join(args[1:])}"

    @staticmethod
    def simulate_chown(args: List[str]) -> str:
        return f"[Simulation] Would change ownership: chown {' '.join(args[1:])}"

    @staticmethod
    def simulate_ls(args: List[str]) -> str:
        return f"[Simulation] Would list contents of directory: {args[-1] if len(args) > 1 else '.'}"

    @staticmethod
    def simulate_cat(args: List[str]) -> str:
        if len(args) < 2:
            return "[Simulation] Error: No file specified for cat command"
        return f"[Simulation] Would display contents of file: {args[1]}"

    @staticmethod
    def simulate_echo(args: List[str]) -> str:
        return f"[Simulation] Would output: {' '.join(args[1:])}"

    @staticmethod
    def simulate_touch(args: List[str]) -> str:
        if len(args) < 2:
            return "[Simulation] Error: No file specified for touch command"
        return f"[Simulation] Would create or update timestamp of file: {args[1]}"