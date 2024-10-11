import asyncio
import os
import shlex
import signal
import traceback
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, List, Optional, Tuple

from ..config import config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CommandExecutor:
    def __init__(self, max_workers: Optional[int] = None) -> None:
        self.executor = ProcessPoolExecutor(max_workers=max_workers or os.cpu_count())

    async def execute_command(
        self, command: str, timeout: Optional[int] = None
    ) -> Tuple[str, int]:
        logger.info(f"Starting execution of command: {command}")
        timeout = timeout or config.default_timeout

        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            logger.debug("Subprocess created, waiting for completion")

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                output = stdout.decode().strip()
                error_output = stderr.decode().strip()

                logger.info(f"Command executed with return code: {process.returncode}")
                logger.debug(f"Command output: {output}")

                if process.returncode != 0:
                    logger.error(
                        f"Command failed with return code: {process.returncode}"
                    )
                    logger.error(f"Error output: {error_output}")
                    return f"Error: {error_output}", process.returncode

                return output, process.returncode

            except asyncio.TimeoutError:
                logger.error(
                    f"Command execution timed out after {timeout} seconds: {command}"
                )
                process.terminate()
                return f"Error: Command execution timed out after {timeout} seconds.", 1

        except Exception as e:
            logger.error(f"Error executing command: {command}. Error: {str(e)}")
            logger.error(traceback.format_exc())
            return f"Error: {str(e)}", 1

    async def execute_command_with_progress(
        self,
        command: str,
        timeout: int,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Tuple[str, int]:
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
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

    async def simulate_command(self, command: str) -> Tuple[str, int]:
        args = shlex.split(command)
        simulated_output = f"[Simulation] Would execute: {command}\n"

        simulation_functions = {
            "rm": self.simulate_rm,
            "git": self.simulate_git,
            "mkdir": self.simulate_mkdir,
            "cp": self.simulate_file_operation,
            "mv": self.simulate_file_operation,
            "chmod": self.simulate_chmod,
            "chown": self.simulate_chown,
            "ls": self.simulate_ls,
            "cat": self.simulate_cat,
            "echo": self.simulate_echo,
            "touch": self.simulate_touch,
        }

        if args[0] in simulation_functions:
            simulated_output += simulation_functions[args[0]](args)
        else:
            simulated_output += f"[Simulation] Would execute unknown command: {args[0]}"

        return simulated_output, 0

    @staticmethod
    def simulate_rm(args: List[str]) -> str:
        if "-rf" in args:
            return f"[Simulation] Would recursively remove: {', '.join(args[2:])}"
        else:
            return f"[Simulation] Would remove: {', '.join(args[1:])}"

    @staticmethod
    def simulate_git(args: List[str]) -> str:
        git_commands = {
            "reset": lambda: f"Would reset Git repository to: {args[2]}",
            "clone": lambda: f"Would clone repository from: {args[2]}",
            "push": lambda: "Would push changes to remote repository",
            "pull": lambda: "Would pull changes from remote repository",
        }
        return f"[Simulation] {git_commands.get(args[1], lambda: f'Would execute Git command: {' '.join(args[1:])}')()}"

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
        return f"[Simulation] Would display contents of file: {args[1]}" if len(args) > 1 else "[Simulation] Error: No file specified for cat command"

    @staticmethod
    def simulate_echo(args: List[str]) -> str:
        return f"[Simulation] Would output: {' '.join(args[1:])}"

    @staticmethod
    def simulate_touch(args: List[str]) -> str:
        return f"[Simulation] Would create or update timestamp of file: {args[1]}" if len(args) > 1 else "[Simulation] Error: No file specified for touch command"

    async def cancel_command(self, process):
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)

    async def shutdown(self):
        self.executor.shutdown(wait=True)
        logger.info("CommandExecutor shutdown completed.")