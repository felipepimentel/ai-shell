import asyncio
import json
import os
import re
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

import aiofiles

from .config import config
from .llm import ai
from .models import AIShellResult, ConflictResolution, HistoryEntry
from .ui_handler import UIHandler
from .utils.logger import class_logger, get_logger

logger = get_logger("ai_shell")


@class_logger
class AIShell:
    def __init__(self, ui_handler: UIHandler, max_history_size: int = 100):
        self.ui_handler = ui_handler
        self.max_history_size = max_history_size
        self.history = []
        self.config = config
        self.ai = ai

    async def initialize(self):
        await self._load_history()

    async def process_command(self, command: str) -> AIShellResult:
        if command.lower() in self._get_internal_commands():
            return await self._handle_internal_command(command.lower())

        try:
            logger.info(f"Sending command to LLM: {command}")
            ai_response = await self.ai.generate(command)
            logger.info(f"Full LLM response: {ai_response}")

            extracted_commands = self._extract_commands(ai_response)
            logger.info(f"Extracted commands: {extracted_commands}")

            if not extracted_commands:
                return AIShellResult(
                    success=False,
                    message="No executable commands found in AI response.",
                )

            results = []
            for cmd in extracted_commands:
                output, return_code = await self._execute_command(cmd)
                logger.info(
                    f"Command execution result - Command: {cmd}, Output: {output}, Return code: {return_code}"
                )
                results.append((cmd, output, return_code))

            combined_output = "\n".join(
                [f"Command: {cmd}\nOutput: {output}\n" for cmd, output, _ in results]
            )
            overall_success = all(return_code == 0 for _, _, return_code in results)

            self._append_to_history(
                command, combined_output, ai_response, 0 if overall_success else 1
            )
            return AIShellResult(success=overall_success, message=combined_output)
        except Exception as e:
            logger.error(f"Error processing command: {str(e)}", exc_info=True)
            return AIShellResult(success=False, message=f"An error occurred: {str(e)}")

    def _extract_commands(self, ai_response: str) -> List[str]:
        commands = []
        for block in re.findall(r"```(?:bash)?\n(.*?)\n```", ai_response, re.DOTALL):
            commands.extend(line.strip() for line in block.split("\n") if line.strip())
        if not commands:
            # Fallback to looking for lines starting with common command prefixes
            commands = re.findall(
                r"^[\$\s]*(git\s+\S.*|mkdir\s+.*|cd\s+.*|touch\s+.*|rm\s+.*|mv\s+.*|cp\s+.*|ls\s+.*|cat\s+.*|echo\s+.*|python\s+.*|pip\s+.*|npm\s+.*|yarn\s+.*)",
                ai_response,
                re.MULTILINE,
            )
        return [cmd.strip() for cmd in commands if cmd.strip()]

    async def _execute_command(
        self, command: str, timeout: int = 60
    ) -> Tuple[str, int]:
        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            output = stdout.decode().strip() or stderr.decode().strip()
            return output, process.returncode
        except asyncio.TimeoutError:
            return f"Command execution timed out after {timeout} seconds", 124

    def _append_to_history(
        self, command: str, output: str, ai_response: str, return_code: int
    ):
        entry = HistoryEntry(
            command=command,
            output=output,
            ai_response=ai_response,
            status="Success" if return_code == 0 else "Failed",
            timestamp=datetime.now().isoformat(),
        )
        self.history.append(entry)
        if len(self.history) > self.max_history_size:
            self.history.pop(0)
        asyncio.create_task(self._save_history())

    async def _save_history(self):
        async with aiofiles.open("ai_command_history.json", "w") as f:
            await f.write(
                json.dumps([entry.model_dump() for entry in self.history], indent=2)
            )

    def _detect_conflict(self, command: str) -> Optional[str]:
        if command.startswith(("mkdir", "touch", "cp", "mv")):
            path = command.split()[-1]
            return f"Path already exists: {path}" if os.path.exists(path) else None
        return None

    def _resolve_conflict(
        self, conflict: str, resolution: ConflictResolution, original_command: str
    ) -> str:
        path = original_command.split()[-1]
        if resolution == ConflictResolution.REMOVE:
            os.remove(path)
            return original_command
        elif resolution == ConflictResolution.RENAME:
            base, ext = os.path.splitext(path)
            counter = 1
            while os.path.exists(f"{base}_{counter}{ext}"):
                counter += 1
            return original_command.replace(path, f"{base}_{counter}{ext}")
        else:
            return "Operation aborted due to conflict."

    def _get_internal_commands(self) -> Dict[str, Callable[[], None]]:
        return {
            self.config.help_command: self.ui_handler.display_help,
            self.config.history_command: lambda: self.ui_handler.display_history(
                self.history
            ),
            self.config.clear_history_command: self._clear_history,
        }

    async def _handle_internal_command(self, command: str) -> AIShellResult:
        command_func = self._get_internal_commands().get(command)
        if command_func:
            command_func()
            return AIShellResult(
                success=True, message="Internal command executed successfully."
            )
        return AIShellResult(success=False, message="Unknown internal command.")

    def _clear_history(self):
        self.history.clear()
        asyncio.create_task(self._save_history())

    async def _load_history(self):
        try:
            async with aiofiles.open("ai_command_history.json", "r") as f:
                content = await f.read()
                history_data = json.loads(content)
                self.history = [HistoryEntry(**entry) for entry in history_data]
                if len(self.history) > self.max_history_size:
                    self.history = self.history[-self.max_history_size :]
        except FileNotFoundError:
            logger.info("No history file found. Starting with an empty history.")
        except json.JSONDecodeError:
            logger.error("Error decoding history file. Starting with an empty history.")
        except Exception as e:
            logger.error(
                f"Error loading history: {str(e)}. Starting with an empty history."
            )
