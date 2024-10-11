import asyncio
import shlex
from typing import Tuple

from ..config import config
from .logger import get_logger

logger = get_logger(__name__)


async def execute_command(command: str) -> Tuple[str, int]:
    """
    Execute a shell command asynchronously.

    Args:
        command (str): The command to execute.

    Returns:
        Tuple[str, int]: A tuple containing the command output and return code.
    """
    try:
        # Split the command into arguments
        args = shlex.split(command)

        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        # Wait for the subprocess to finish
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=config.default_timeout
        )

        # Decode the output
        output = stdout.decode().strip() if stdout else stderr.decode().strip()

        logger.info(f"Command executed: {command}")
        logger.debug(f"Command output: {output}")

        return output, process.returncode

    except asyncio.TimeoutError:
        logger.error(f"Command execution timed out: {command}")
        return (
            f"Error: Command execution timed out after {config.default_timeout} seconds.",
            1,
        )
    except Exception as e:
        logger.error(f"Error executing command: {command}. Error: {str(e)}")
        return f"Error: {str(e)}", 1
