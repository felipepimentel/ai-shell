import asyncio
import os
from typing import Optional, Tuple, Callable

from ..config import config
from ..utils.logger import get_logger

logger = get_logger(__name__)

TIMEOUT_EXIT_CODE = 124

class CommandExecutionError(Exception):
    pass

class CommandExecutor:
    def __init__(self, max_workers: Optional[int] = None, dry_run: bool = False) -> None:
        self.max_workers = max_workers or os.cpu_count()
        self.dry_run = dry_run

    async def execute_command(
        self, command: str, timeout: Optional[int] = None
    ) -> Tuple[str, int]:
        if self.dry_run:
            return self._dry_run_execution(command)

        logger.info(f"Starting execution of command: {command}")
        timeout = timeout or config.default_timeout

        try:
            return await asyncio.wait_for(self._run_command(command), timeout=timeout)
        except asyncio.TimeoutError:
            return self._handle_timeout_error(command, timeout)
        except Exception as e:
            return self._handle_execution_error(command, e)

    async def _run_command(self, command: str) -> Tuple[str, int]:
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        return self._process_command_output(process.returncode, stdout, stderr)

    def _process_command_output(self, returncode: int, stdout: bytes, stderr: bytes) -> Tuple[str, int]:
        output = stdout.decode().strip()
        error_output = stderr.decode().strip()

        logger.info(f"Command executed with return code: {returncode}")
        logger.debug(f"Command output: {output}")

        if returncode != 0:
            logger.error(f"Command failed with return code: {returncode}")
            logger.error(f"Error output: {error_output}")
            return f"Error: {error_output}", returncode

        return output, returncode

    def _dry_run_execution(self, command: str) -> Tuple[str, int]:
        logger.info(f"Dry run: would execute command: {command}")
        return f"Dry run: {command}", 0

    def _handle_timeout_error(self, command: str, timeout: int) -> Tuple[str, int]:
        error_message = f"Error: Command execution timed out after {timeout} seconds: {command}"
        logger.error(error_message)
        return error_message, TIMEOUT_EXIT_CODE

    def _handle_execution_error(self, command: str, exception: Exception) -> Tuple[str, int]:
        error_message = f"Error executing command: {command}. {str(exception)}"
        logger.exception(error_message)
        raise CommandExecutionError(error_message)

    async def cancel_command(self, process: asyncio.subprocess.Process) -> None:
        process.terminate()

    async def shutdown(self) -> None:
        logger.info("CommandExecutor shutdown completed.")

    async def execute_long_running_command(
        self, command: str, timeout: Optional[int] = None, progress_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[str, int]:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        output = []
        try:
            async for line in process.stdout:
                decoded_line = line.decode().strip()
                output.append(decoded_line)
                if progress_callback:
                    progress_callback(decoded_line)
        except asyncio.TimeoutError:
            process.terminate()
            return "Command timed out", TIMEOUT_EXIT_CODE
        
        await process.wait()
        return "\n".join(output), process.returncode

    def report_progress(self, line: str) -> None:
        logger.info(f"Command progress: {line}")