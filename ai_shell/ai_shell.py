import asyncio
import json
import os
import re
from datetime import datetime
from typing import Callable, Dict, List, Tuple

import aiofiles

from .config import config
from .llm import ai
from .models import AIShellResult, HistoryEntry
from .ui_handler import UIHandler
from .utils.logger import class_logger, get_logger

logger = get_logger("ai_shell")


def load_prompt(prompt_name: str) -> str:
    prompt_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "assets", "prompts", prompt_name
    )
    try:
        with open(prompt_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {prompt_name}")
        return ""
    except IOError as e:
        logger.error(f"Error reading prompt file {prompt_name}: {str(e)}")
        return ""


@class_logger
class AIShell:
    def __init__(self, ui_handler: UIHandler, max_history_size: int = 100):
        self.ui_handler = ui_handler
        self.max_history_size = max_history_size
        self.history = []
        self.config = config
        self.ai = ai
        self.command_generation_prompt = load_prompt("command_generation.md")
        self.error_resolution_prompt = load_prompt("error_resolution.md")

    async def initialize(self):
        await self._load_history()

    async def process_command(self, command: str) -> AIShellResult:
        if command.lower() in self._get_internal_commands():
            return await self._handle_internal_command(command.lower())

        try:
            logger.info("Starting command processing")
            await self._show_progress_with_timeout(
                "Generating AI response...", timeout=5
            )

            logger.info(f"Generating AI response for command: {command}")
            ai_response = await self._get_ai_response(command)
            logger.info("AI response received")

            self.ui_handler.display_ai_response(ai_response)
            logger.info("AI response displayed")

            extracted_commands = self._extract_commands(ai_response)
            logger.info(f"Extracted commands: {extracted_commands}")

            if not extracted_commands:
                return AIShellResult(
                    success=False,
                    message="No executable commands found in AI response.",
                )

            results = await self._execute_commands(extracted_commands)

            combined_output = self._format_results(results)
            overall_success = all(return_code == 0 for _, _, return_code in results)

            self._append_to_history(
                command, combined_output, ai_response, 0 if overall_success else 1
            )
            return AIShellResult(success=overall_success, message=combined_output)

        except asyncio.TimeoutError:
            error_message = f"Timeout occurred while processing the command: {command}"
            logger.error(error_message, exc_info=True)
            self.ui_handler.display_error_message(error_message)
            return AIShellResult(success=False, message=error_message)

        except asyncio.CancelledError:
            error_message = f"The operation was cancelled: {command}"
            logger.error(error_message, exc_info=True)
            self.ui_handler.display_error_message(error_message)
            return AIShellResult(success=False, message=error_message)

        except Exception as e:
            error_message = f"An unexpected error occurred while processing the command: {command}\nError: {str(e)}"
            logger.error(error_message, exc_info=True)
            self.ui_handler.display_error_message(error_message)
            return AIShellResult(success=False, message=error_message)

    async def _get_ai_response(self, command: str) -> str:
        logger.info(f"Sending command to LLM: {command}")
        full_prompt = f"{self.command_generation_prompt}\n\nUser Command: {command}"
        ai_response = await self.ai.generate(full_prompt)
        logger.info(f"Full LLM response: {ai_response}")
        return ai_response

    async def _execute_commands(
        self, commands: List[str]
    ) -> List[Tuple[str, str, int]]:
        results = []
        for cmd in commands:
            await self._show_progress_with_timeout(f"Executing: {cmd}", timeout=5)
            output, return_code = await self._execute_command(cmd)
            logger.info(
                f"Command execution result - Command: {cmd}, Output: {output}, Return code: {return_code}"
            )
            results.append((cmd, output, return_code))
        return results

    def _format_results(self, results: List[Tuple[str, str, int]]) -> str:
        return "\n".join(
            [f"Command: {cmd}\nOutput: {output}" for cmd, output, _ in results]
        )

    def _extract_commands(self, ai_response: str) -> List[str]:
        commands = re.findall(r"```(?:bash)?\n(.*?)\n```", ai_response, re.DOTALL)

        if not commands:
            commands = re.findall(
                r"^[\$\s]*(git\s+\S.*|mkdir\s+.*|cd\s+.*|touch\s+.*|rm\s+.*|mv\s+.*|cp\s+.*|ls\s+.*|cat\s+.*|echo\s+.*|python\s+.*|pip\s+.*|npm\s+.*|yarn\s+.*)",
                ai_response,
                re.MULTILINE,
            )

        commands = [cmd.strip() for cmd in commands if cmd.strip()]

        if not commands:
            logger.error("No executable commands found in AI response.")

        return commands

    async def _execute_command(
        self, command: str, timeout: int = 60
    ) -> Tuple[str, int]:
        try:
            logger.info(f"Starting execution of command: {command}")
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            output = stdout.decode().strip() or stderr.decode().strip()
            logger.info(
                f"Command execution completed. Return code: {process.returncode}"
            )
            return output, process.returncode
        except asyncio.TimeoutError:
            logger.error(
                f"Command execution timed out after {timeout} seconds: {command}"
            )
            return f"Command execution timed out after {timeout} seconds", 124

    async def _show_progress_with_timeout(self, message: str, timeout: int):
        try:
            await asyncio.wait_for(
                self.ui_handler.show_progress(message), timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout showing progress: {message}")

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
                json.dumps(
                    [
                        {
                            "command": entry.command,
                            "output": entry.output,
                            "ai_response": entry.ai_response,
                            "status": entry.status,
                            "timestamp": entry.timestamp,
                        }
                        for entry in self.history
                    ],
                    indent=2,
                )
            )

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
        self.ui_handler.display_success_message("History cleared successfully.")

    async def _load_history(self):
        history_file = "ai_command_history.json"

        if not os.path.exists(history_file):
            logger.info("No history file found. Creating a new one.")
            self.history = []
            await self._save_history()
            return

        try:
            async with aiofiles.open(history_file, "r") as f:
                content = await f.read()
                if not content:
                    logger.info(
                        "Empty history file found. Starting with an empty history."
                    )
                    self.history = []
                    return

                history_data = json.loads(content)
                self.history = []
                for entry in history_data:
                    history_entry = HistoryEntry(
                        command=entry.get("command", "Unknown command"),
                        output=entry.get("output", "No output"),
                        ai_response=entry.get("ai_response", "No AI response"),
                        status=entry.get("status", "Unknown"),
                        timestamp=entry.get("timestamp", datetime.now().isoformat()),
                    )
                    self.history.append(history_entry)
                if len(self.history) > self.max_history_size:
                    self.history = self.history[-self.max_history_size :]
        except json.JSONDecodeError:
            logger.error("Error decoding history file. Starting with an empty history.")
            self.history = []
            await self._save_history()
        except Exception as e:
            logger.error(
                f"Error loading history: {str(e)}. Starting with an empty history."
            )
            self.history = []
