from __future__ import annotations

import asyncio
import aiohttp
import json
import os
import re
import subprocess
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
import tempfile
from enum import Enum

from rich.prompt import Prompt, Confirm

from .config import config
from .llm.prompts import generate_command_from_prompt
from .models import CommandHistoryEntry
from .utils.cache import check_cache, save_cache
from .utils.logger import get_logger

if TYPE_CHECKING:
    from subprocess import CompletedProcess

    from rich.console import Console

logger = get_logger("ai_shell.command")

MAX_RETRIES = 3


class ErrorType(Enum):
    FATAL = "FATAL"
    USER_INPUT = "USER_INPUT"
    WARNING = "WARNING"
    INFO = "INFO"


class CommandProcessor:
    def __init__(self, console: "Console") -> None:
        self.history: List[CommandHistoryEntry] = []
        self.last_generated_command: str = ""
        self._last_command_from_cache: bool = False
        self.command_cache: Dict[str, str] = {}
        self.console: "Console" = console

    async def process_command(
        self, command: str, simulation_mode: bool, verbose_mode: bool
    ) -> Optional[str]:
        if verbose_mode:
            logger.debug(f"Processing command: {command}")

        command = self.resolve_alias(command) or command

        cached_command, cached_output = await self.check_cache(command)
        if cached_output:
            self.console.print("[green]Using cached result[/green]")
            self.append_to_history(
                command, cached_output, cached_command, "Success (Cached)", None,
                used_cache=True, tokens_used=None, model_used=None
            )
            return cached_output

        for retry in range(MAX_RETRIES):
            try:
                logger.debug(f"Attempt {retry + 1}: Generating AI response")
                ai_response, tokens_used, model_used = await self.generate_ai_response(command)
                if not ai_response:
                    error_message = "Failed to generate AI response"
                    self.console.print(f"[red]{error_message}[/red]")
                    logger.error(f"Attempt {retry + 1}: {error_message}")
                    if retry < MAX_RETRIES - 1:
                        self.console.print(f"[yellow]Retrying (Attempt {retry + 2}/{MAX_RETRIES})...[/yellow]")
                        continue
                    self.append_to_history(command, "", None, "Error", error_message,
                                            used_cache=False, tokens_used=tokens_used, model_used=model_used)
                    return None

                logger.debug(f"AI response generated successfully: {ai_response[:100]}...")

                commands = self.extract_commands(ai_response)
                self.last_generated_command = ai_response

                if verbose_mode:
                    logger.debug(f"Generated commands: {commands}")

                output = await self.execute_commands(commands, simulation_mode, verbose_mode)

                if output.startswith("Error:"):
                    logger.error(f"Command execution failed: {output}")
                    if "Command execution timed out" in output:
                        error_message = "Command execution timed out. The operation might be taking longer than expected."
                        self.console.print(f"[yellow]{error_message}[/yellow]")
                        self.append_to_history(command, output, ai_response, "Timeout", error_message,
                                                used_cache=False, tokens_used=tokens_used, model_used=model_used)
                        return output
                    if retry < MAX_RETRIES - 1:
                        self.console.print(f"[yellow]Attempt {retry + 1} failed. Retrying...[/yellow]")
                        command = f"The previous command failed with the following error: {output}\n" \
                                  f"Please provide a corrected version of the command to address this error " \
                                  f"and continue with the original request: {command}"
                        continue
                    else:
                        self.console.print("[red]Max retries reached. Command execution failed.[/red]")

                await self.handle_command_output(command, output, ai_response, tokens_used, model_used)

                return output

            except Exception as e:
                error_message = f"An error occurred: {str(e)}"
                logger.exception(f"Attempt {retry + 1}: {error_message}")
                self.console.print(f"[red]{error_message}[/red]")
                if retry < MAX_RETRIES - 1:
                    self.console.print(f"[yellow]Retrying (Attempt {retry + 2}/{MAX_RETRIES})...[/yellow]")
                else:
                    self.console.print("[red]Max retries reached. Command execution failed.[/red]")
                    self.append_to_history(command, "", None, "Error", error_message,
                                           used_cache=False, tokens_used=None, model_used=None)
                    return None

        return None

    def resolve_alias(self, command: str) -> Optional[str]:
        parts = command.split()
        if parts and parts[0] in config.aliases:
            aliased_command = f"{config.aliases[parts[0]]} {' '.join(parts[1:])}"
            logger.info(f"Using alias: {command} -> {aliased_command}")
            return aliased_command
        return None

    async def check_cache(self, command: str) -> tuple[Optional[str], Optional[str]]:
        cached_command, cached_output = await check_cache(command)
        if cached_output:
            logger.info(f"Using cached result for command: {command}")
            self.last_generated_command = cached_command or command
            self._last_command_from_cache = True
            return cached_command, cached_output
        self._last_command_from_cache = False
        return None, None

    async def generate_ai_response(self, command: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        context = self.build_enhanced_context()
        try:
            ai_response, tokens_used, model_used = await generate_command_from_prompt(command, self.history, context)
            if not ai_response:
                error_message = "AI failed to generate a response."
                self.console.print(f"[red]Error: {error_message}[/red]")
                logger.error(f"AI Response Generation Failed: {error_message}")
            return ai_response, tokens_used, model_used
        except ValueError as e:
            error_message = f"Configuration error: {str(e)}"
            logger.error(error_message)
            self.console.print(f"[red]{error_message}[/red]")
        except aiohttp.ClientError as e:
            error_message = f"Network error: {str(e)}"
            logger.error(error_message)
            self.console.print(f"[red]{error_message}[/red]")
        except Exception as e:
            error_message = f"Unexpected error generating AI response: {str(e)}"
            logger.exception(error_message)
            self.console.print(f"[red]{error_message}[/red]")
        return None, None, None

    def extract_commands(self, ai_response: str) -> List[str]:
        # Remove any markdown code block delimiters if present
        ai_response = ai_response.strip("`")

        # Split the response into lines
        lines = ai_response.split("\n")

        # Join all lines into a single script
        script = "\n".join(lines)

        # Check if the script is complete
        if not script.strip().endswith("}"):
            self.console.print("[yellow]Warning: The generated script appears to be incomplete.[/yellow]")

        # Return the entire script as a single command
        return [script] if script.strip() else []

    def validate_script(self, script: str) -> bool:
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.sh', delete=False) as temp_file:
            temp_file.write(script)
            temp_file_path = temp_file.name

        try:
            result = subprocess.run(
                ['sh', '-n', temp_file_path],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]Script validation error: {e.stderr.strip()}[/red]")
            return False
        finally:
            os.unlink(temp_file_path)

    async def execute_commands(
        self,
        commands: List[str],
        simulation_mode: bool = False,
        verbose_mode: bool = False,
    ) -> str:
        output = []
        
        for i, command in enumerate(commands, 1):
            self.console.print(f"[cyan]Validating and executing command {i}/{len(commands)}[/cyan]")

            if not self.validate_script(command):
                error_message = f"Error: Invalid or incomplete script in command {i}"
                output.append(error_message)
                self.console.print(f"[red]{error_message}[/red]")
                return "\n".join(output)

            if simulation_mode:
                output.append(f"[Simulation] Would execute:\n{command}")
                continue

            try:
                if verbose_mode:
                    logger.debug(f"Executing command:\n{command}")

                with tempfile.NamedTemporaryFile(mode='w+', suffix='.sh', delete=False) as temp_file:
                    temp_file.write(command)
                    temp_file_path = temp_file.name

                result = subprocess.run(
                    ['sh', temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=300  # Aumentado para 5 minutos
                )

                os.unlink(temp_file_path)

                stdout_lines = result.stdout.strip().split('\n')
                stderr_lines = result.stderr.strip().split('\n')

                for line in stdout_lines:
                    output.append(line)

                for line in stderr_lines:
                    error_type, message = self.classify_error(line)
                    if error_type == ErrorType.USER_INPUT:
                        user_choice = self.handle_user_input(message)
                        if user_choice == "cancel":
                            return "\n".join(output + ["Operation cancelled by user."])
                        elif user_choice == "skip":
                            break
                        else:
                            # Handle other user choices here
                            pass
                    elif error_type == ErrorType.FATAL:
                        return "\n".join(output + [f"Fatal error: {message}"])
                    elif error_type == ErrorType.WARNING:
                        self.console.print(f"[yellow]Warning: {message}[/yellow]")
                    elif error_type == ErrorType.INFO:
                        self.console.print(f"[cyan]Info: {message}[/cyan]")
                    output.append(line)

                if result.returncode != 0:
                    error_output = f"Error: Command exited with status {result.returncode}"
                    output.append(error_output)
                    logger.error(error_output)
                    break

            except subprocess.TimeoutExpired:
                error_message = "Error: Command execution timed out."
                output.append(error_message)
                logger.error(error_message)
                break
            except Exception as e:
                error_message = f"Error: Command execution failed: {str(e)}"
                output.append(error_message)
                logger.error(error_message)
                break

        return "\n".join(output)

    def classify_error(self, error_line: str) -> Tuple[ErrorType, str]:
        if error_line.startswith("FATAL:"):
            return ErrorType.FATAL, error_line[6:].strip()
        elif error_line.startswith("USER_INPUT:"):
            return ErrorType.USER_INPUT, error_line[11:].strip()
        elif error_line.startswith("WARNING:"):
            return ErrorType.WARNING, error_line[8:].strip()
        elif error_line.startswith("INFO:"):
            return ErrorType.INFO, error_line[5:].strip()
        else:
            return ErrorType.INFO, error_line

    def handle_user_input(self, message: str) -> str:
        options = message.split('[')[-1].split(']')[0].split('/')
        options = options + ['skip', 'cancel'] if 'skip' not in options or 'cancel' not in options else options
        choice = Prompt.ask(message, choices=options)
        return choice

    def replace_variables(self, command: str, variables: Dict[str, str]) -> str:
        for var, value in variables.items():
            command = command.replace(f"${var}", value).replace(f"${{{var}}}", value)
        return command

    def handle_export(self, command: str, variables: Dict[str, str]) -> None:
        var_match = re.match(r"export\s+(\w+)=(.*)", command)
        if var_match:
            var_name, var_value = var_match.groups()
            variables[var_name] = var_value.strip("\"'")

    def handle_read_prompt(self, command: str, variables: Dict[str, str]) -> str:
        prompt_match = re.search(r'read -p "(.*?)" (\w+)', command)
        if prompt_match:
            prompt, var_name = prompt_match.groups()
            prompt = self.replace_variables(prompt, variables)
            user_input = Prompt.ask(prompt)
            variables[var_name] = user_input
            return user_input
        return ""

    def run_command(self, command: str) -> "CompletedProcess":
        return subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )

    def get_command_context(self, commands: List[str], current_command: str) -> str:
        index = commands.index(current_command)
        context = []
        for i in range(max(0, index - 2), index):
            cmd = commands[i]
            if cmd.startswith("echo "):
                context.append(cmd[5:].strip('"'))
        return "\n".join(context)

    async def handle_command_output(
        self, command: str, output: str, ai_response: str, tokens_used: Optional[int], model_used: Optional[str]
    ) -> None:
        success = not output.startswith("Error:")
        status = "Success" if success else "Error"
        error_message = output if not success else None
        
        logger.info("Commands executed successfully" if success else "Command execution failed")
        self.append_to_history(
            command, output, ai_response, status, error_message,
            used_cache=False, tokens_used=tokens_used, model_used=model_used
        )
        await save_cache(command, self.last_generated_command, output)
        self.command_cache[command] = output

    def append_to_history(
        self,
        user_command: str,
        output: str,
        ai_response: Optional[str],
        status: str,
        error_message: Optional[str],
        used_cache: bool,
        tokens_used: Optional[int],
        model_used: Optional[str],
    ) -> None:
        self.history.append(
            CommandHistoryEntry(
                command=user_command,
                output=output,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                working_directory=os.getcwd(),
                ai_response=ai_response,
                status=status,
                error_message=error_message,
                used_cache=used_cache,
                tokens_used=tokens_used,
                model_used=model_used,
            )
        )
        asyncio.create_task(self.save_history())

    def clear_history(self) -> None:
        self.history.clear()

    def get_recent_commands(self, limit: int = 10) -> List[str]:
        return [entry.command for entry in self.history[-limit:]]

    async def save_history(self) -> None:
        with open("ai_command_history.json", "w") as f:
            json.dump([entry.__dict__ for entry in self.history], f, indent=2)

    def is_last_command_from_cache(self) -> bool:
        return self._last_command_from_cache

    def get_last_generated_command(self) -> str:
        return self.last_generated_command

    def build_enhanced_context(self) -> Dict[str, Any]:
        return {
            "current_directory": os.getcwd(),
            "environment_variables": dict(os.environ),
            "recent_commands": self.get_recent_commands(5),
            "user_preferences": self.get_user_preferences(),
        }

    def get_user_preferences(self) -> Dict[str, Any]:
        return {
            "preferred_shell": "bash",
            "verbose_output": True,
            "safety_level": "high",
        }

    def get_user_feedback(self, command: str, output: List[str]) -> str:
        return Prompt.ask("Was this command helpful? (y/n)")

    def update_command_history(
        self, command: str, output: List[str], feedback: str
    ) -> None:
        # Implement logic to update command history based on feedback
        pass