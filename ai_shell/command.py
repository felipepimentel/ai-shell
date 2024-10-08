import json
import os
import subprocess
import time
from dataclasses import dataclass
from typing import List, Tuple

from ai_shell.utils.logger import get_logger

from .utils.cache import check_cache, save_cache

logger = get_logger("ai_shell.command")


@dataclass
class CommandHistoryEntry:
    command: str
    output: str
    timestamp: str
    working_directory: str
    ai_response: str


class CommandProcessor:
    def __init__(self):
        self.history: List[CommandHistoryEntry] = []
        self.last_generated_command: str = ""

    async def process_command(
        self, command: str, simulation_mode: bool, verbose_mode: bool
    ):
        if verbose_mode:
            logger.debug(f"Processing command: {command}")

        cached_output = await check_cache(command)
        if cached_output:
            logger.info(f"Using cached result for command: {command}")
            return cached_output

        from .llm.prompts import generate_command_from_prompt

        ai_response = await generate_command_from_prompt(command, self.history)

        if not ai_response:
            logger.error("Error generating command")
            return

        extracted_command = self.extract_command(ai_response)
        self.last_generated_command = extracted_command

        if verbose_mode:
            logger.debug(f"Generated command: {extracted_command}")

        output, error = await self.execute_command(
            extracted_command, simulation_mode, verbose_mode
        )

        if error:
            logger.error(f"Command error: {error}")
        else:
            logger.info(f"Command executed successfully: {extracted_command}")
            self.append_to_history(extracted_command, output, ai_response)
            await save_cache(command, output)

        return output or error

    def get_last_generated_command(self) -> str:
        return self.last_generated_command

    async def execute_command(
        self, command: str, simulation_mode: bool = False, verbose_mode: bool = False
    ) -> Tuple[str | None, str | None]:
        if simulation_mode:
            return f"[Simulation] Would execute: {command}", None

        try:
            if verbose_mode:
                logger.debug(f"Executing command: {command}")

            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                return result.stdout.strip(), None
            else:
                return None, result.stderr.strip()

        except subprocess.TimeoutExpired:
            return None, "Command execution timed out."
        except FileNotFoundError:
            return None, "Command not found."
        except PermissionError:
            return None, "Permission denied."
        except Exception as e:
            return None, f"Command execution failed: {str(e)}"

    def append_to_history(self, command: str, output: str, ai_response: str = None):
        self.history.append(
            CommandHistoryEntry(
                command=command,
                output=output,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                working_directory=os.getcwd(),
                ai_response=ai_response,
            )
        )

    def extract_command(self, ai_response: str) -> str:
        return ai_response.strip()

    def clear_history(self):
        self.history.clear()

    def get_recent_commands(self, limit: int = 10) -> List[str]:
        return [entry.command for entry in self.history[-limit:]]

    async def save_history(self):
        with open("ai_command_history.json", "w") as f:
            json.dump([entry.__dict__ for entry in self.history], f)
