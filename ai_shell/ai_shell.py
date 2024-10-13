import asyncio
import json
import os
import re
import time
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
        self.context = []

    async def initialize(self):
        await self._load_history()

    async def process_command(self, command: str) -> AIShellResult:
        if command.lower() in self._get_internal_commands():
            return await self._handle_internal_command(command.lower())

        try:
            logger.info("Starting command processing")
            self.ui_handler.display_thinking()

            ai_response = await self.ui_handler.execute_with_progress(
                "Generating AI response...", self._get_ai_response(command)
            )
            self.ui_handler.display_ai_response(ai_response)

            extracted_commands = self._extract_commands(ai_response)
            if not extracted_commands:
                return AIShellResult(
                    success=False,
                    message="No executable commands found in AI response.",
                )

            await self._confirm_and_execute_commands(extracted_commands)

            self._update_context(command, ai_response)
            return AIShellResult(
                success=True, message="Command processed successfully."
            )

        except asyncio.TimeoutError:
            error_message = f"Timeout occurred while processing the command: {command}"
            logger.error(error_message, exc_info=True)
            self.ui_handler.display_error_message(error_message)
            return AIShellResult(success=False, message=error_message)

        except Exception as e:
            error_message = f"An unexpected error occurred while processing the command: {command}\nError: {str(e)}"
            logger.error(error_message, exc_info=True)
            self.ui_handler.display_error_message(error_message)
            return AIShellResult(success=False, message=error_message)
        finally:
            self.ui_handler.clear_thinking()

    async def _get_ai_response(self, command: str) -> str:
        logger.info(f"Sending command to LLM: {command}")
        context_prompt = "\n".join(self.context[-5:])  # Use last 5 context entries
        full_prompt = f"{self.command_generation_prompt}\n\nContext:\n{context_prompt}\n\nUser Command: {command}"

        try:
            ai_response = await asyncio.wait_for(
                self.ai.generate(full_prompt), timeout=30
            )
            logger.info(f"Full LLM response: {ai_response}")
            return ai_response
        except asyncio.TimeoutError:
            logger.error(f"LLM response timed out for command: {command}")
            return "Error: Timeout occurred while waiting for LLM response."
        except Exception as e:
            logger.error(f"Error occurred while getting LLM response: {str(e)}")
            return f"Error: Failed to get response from LLM. Details: {str(e)}"

    async def _confirm_and_execute_commands(self, commands: List[str]):
        for cmd in commands:
            self.ui_handler.display_panel(
                self.ui_handler._create_panel(
                    f"Proposed command: {cmd}",
                    "Confirmation",
                    self.ui_handler.theme["ai_response"],
                )
            )
            choice = await self.ui_handler.confirm_execution()

            if choice.lower() == "q":
                break
            elif choice.lower() == "e":
                cmd = await self.ui_handler.edit_command(cmd)

            if choice.lower() != "q":
                await self._execute_and_display_command(cmd)

    async def _execute_and_display_command(self, cmd: str):
        (
            output,
            return_code,
            execution_time,
        ) = await self.ui_handler.execute_with_progress(
            f"Executing: {cmd}", self._execute_command(cmd)
        )
        self.ui_handler.display_command_output(
            cmd, output, return_code == 0, execution_time
        )
        self._append_to_history(cmd, output, "", return_code)

    def _update_context(self, command: str, ai_response: str):
        self.context.append(f"User: {command}")
        self.context.append(f"AI: {ai_response}")
        if len(self.context) > 20:  # Keep last 20 interactions
            self.context = self.context[-20:]

    async def _execute_command(
        self, command: str, timeout: int = 60
    ) -> Tuple[str, int, float]:
        try:
            logger.info(f"Starting execution of command: {command}")
            start_time = time.time()
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            end_time = time.time()
            execution_time = end_time - start_time
            output = stdout.decode().strip() or stderr.decode().strip()
            logger.info(
                f"Command execution completed. Return code: {process.returncode}"
            )
            return output, process.returncode, execution_time
        except asyncio.TimeoutError:
            logger.error(
                f"Command execution timed out after {timeout} seconds: {command}"
            )
            return f"Command execution timed out after {timeout} seconds", 124, timeout

    async def _show_progress_with_timeout(self, message: str, timeout: int):
        try:
            await asyncio.wait_for(
                self.ui_handler.show_progress(message), timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout showing progress: {message}")

    async def _handle_command_error(self, command: str, error_output: str):
        error_analysis_prompt = f"Analyze the following error and suggest possible corrections:\n\nError:\n{error_output}\n\nCommand:\n{command}\n\nProvide options such as 'Recreate repository', 'Update repository', 'Skip', or others as appropriate, with commands to fix the issue."

        logger.info(f"Generating error analysis for: {command}")

        error_suggestions = await self._get_ai_response(error_analysis_prompt)

        if not error_suggestions.strip():
            self.ui_handler.display_error_message(
                "🚨 No response from AI. Please try again later."
            )
            return

        logger.info(f"Error analysis suggestions: {error_suggestions}")

        options_with_commands = self._extract_options_with_commands(error_suggestions)

        if not options_with_commands:
            self.ui_handler.display_error_message(
                "🚨 No correction options found. Please try again later."
            )
            return

        options = list(options_with_commands.keys())
        choice = await self.ui_handler.get_choice("Choose a correction:", options)

        if choice:
            selected_commands = options_with_commands.get(choice, [])
            if selected_commands:
                for cmd in selected_commands:
                    await self._execute_command(cmd)
            else:
                self.ui_handler.display_success_message("Action skipped successfully.")

    def _extract_options_with_commands(self, ai_response: str) -> Dict[str, List[str]]:
        options_with_commands = {}

        if not ai_response.strip():
            logger.error("LLM response is empty.")
            return options_with_commands

        matches = re.findall(r"Option:\s*(.*?)\nCommands:\s*((?:.+\n?)*)", ai_response)
        if not matches:
            logger.error("No valid options found in LLM response.")
            return options_with_commands

        for option, commands in matches:
            commands_list = [
                cmd.strip() for cmd in commands.splitlines() if cmd.strip()
            ]
            options_with_commands[option] = commands_list

        return options_with_commands

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
        history_file = "ai_command_history.json"
        try:
            async with aiofiles.open(history_file, "w") as f:
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
            logger.info(f"History saved to {history_file}")
        except Exception as e:
            logger.error(f"Error saving history: {str(e)}")

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

    def _format_results(self, results: List[Tuple[str, str, int]]) -> str:
        return "\n".join(
            [f"Command: {cmd}\nOutput: {output}" for cmd, output, _ in results]
        )
