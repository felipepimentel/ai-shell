import asyncio
import os
import sys
import traceback
from typing import Any, Dict, List
import shlex

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.theme import Theme

from ai_shell.command.command_executor import CommandExecutor
from ai_shell.command.command_generator import CommandGenerator
from ai_shell.command.command_processor import CommandProcessor
from ai_shell.command.command_cache_manager import CommandCacheManager
from ai_shell.command.context_builder import ContextBuilder
from ai_shell.config import config
from ai_shell.datatypes import AIShellResult
from ai_shell.llm.prompts import (
    generate_command_from_prompt,
    generate_conflict_resolution_options,
)
from ai_shell.ui_handler import UIHandler
from ai_shell.utils.cache import init_cache
from ai_shell.utils.command_executor import execute_command
from ai_shell.utils.conflict_resolver import detect_conflict, resolve_conflict
from ai_shell.utils.dependency_manager import install_dependency
from ai_shell.utils.error_analyzer import analyze_error, suggest_fix
from ai_shell.utils.logger import get_logger, log_info, setup_logging
import socket
import aiohttp
import pwd

setup_logging()
logger = get_logger("ai_shell.ai_shell")


class AIShell:
    def __init__(
        self,
        command_generator: CommandGenerator,
        command_executor: CommandExecutor,
        ui_handler: UIHandler,
    ):
        self.command_generator = command_generator
        self.command_executor = command_executor
        self.ui_handler = ui_handler
        self.cache_manager = CommandCacheManager()
        self.context_builder = ContextBuilder()
        self.processor = CommandProcessor()
        self.logger = logger
        
        # Initialize the processor with required components
        self.processor.command_generator = self.command_generator
        self.processor.command_executor = self.command_executor
        self.processor.cache_manager = self.cache_manager
        self.processor.context_builder = self.context_builder

    @classmethod
    async def create(cls, non_interactive: bool = False, dry_run: bool = False):
        command_generator = CommandGenerator()
        command_executor = CommandExecutor()
        ui_handler = UIHandler()
        return cls(command_generator, command_executor, ui_handler)

    async def initialize(self):
        # Perform any necessary initialization here
        await init_cache()
        # Add any other initialization tasks as needed

    async def _initialize_context(self) -> Dict[str, Any]:
        """
        Initialize and return the context for AI processing.
        """
        try:
            user = os.getlogin()
        except OSError:
            user = pwd.getpwuid(os.getuid())[0]

        return {
            "current_directory": os.getcwd(),
            "user": user,
            "os": sys.platform,
        }

    async def process_command(self, user_input: str) -> AIShellResult:
        try:
            self.logger.info(f"Processing command: {user_input}")

            try:
                context = await self._initialize_context()
                self.logger.debug(f"Initialized context: {context}")
            except Exception as e:
                self.logger.error(f"Error initializing context: {str(e)}")
                self.logger.error(traceback.format_exc())
                return AIShellResult(
                    success=False, message=f"Failed to initialize context: {str(e)}"
                )

            self.logger.info("Generating AI response")
            try:
                (
                    ai_response,
                    tokens_used,
                    model_used,
                ) = await self.command_generator.generate_command(user_input, context)
                self.logger.debug(f"AI response generated: {ai_response}")
                self.logger.debug(f"Tokens used: {tokens_used}, Model used: {model_used}")
            except Exception as e:
                self.logger.error(f"Error generating AI response: {str(e)}")
                self.logger.error(traceback.format_exc())
                return AIShellResult(
                    success=False, message=f"Failed to generate AI response: {str(e)}"
                )

            if ai_response is None:
                self.logger.error("AI response is None")
                return AIShellResult(
                    success=False, message="Failed to generate AI response."
                )

            self.logger.info("Displaying AI response to user")
            self.ui_handler.display_ai_response(ai_response)

            self.logger.info("Waiting for user confirmation")
            user_choice = await self.ui_handler.confirm_execution()
            self.logger.debug(f"User choice: {user_choice}")

            if user_choice == "":
                shell_command = ai_response
            elif user_choice == "e":
                shell_command = await self.ui_handler.edit_command(ai_response)
            else:
                self.logger.info("Command execution cancelled by user")
                return AIShellResult(
                    success=False, message="Command execution cancelled by user."
                )

            # Modificar esta parte para formatar corretamente o comando Git
            if shell_command.startswith("clone "):
                parts = shlex.split(shell_command)
                if len(parts) >= 3:
                    repo_url = parts[1]
                    dest_path = os.path.expanduser(parts[2])  # Expande o ~ para o caminho completo
                    shell_command = f"git clone {repo_url} {dest_path}"
                else:
                    shell_command = "git " + shell_command

            self.logger.info(f"Executing shell command: {shell_command}")
            try:
                output, exit_code = await self.command_executor.execute_command(
                    shell_command
                )
                self.logger.debug(f"Command output: {output}")
                self.logger.debug(f"Command exit code: {exit_code}")

                if exit_code != 0:
                    self.logger.error(f"Command failed with exit code {exit_code}")
                    self.logger.error(f"Error output: {output}")
                    return AIShellResult(
                        success=False,
                        message=f"Command failed with exit code {exit_code}. Error: {output}"
                    )

                success = exit_code == 0
                message = output

                return AIShellResult(success=success, message=message)
            except Exception as e:
                self.logger.error(f"Error executing command: {str(e)}")
                self.logger.error(traceback.format_exc())
                return AIShellResult(
                    success=False,
                    message=f"Error executing command: {str(e)}"
                )
        except Exception as e:
            self.logger.error(f"Unexpected error in process_command: {str(e)}")
            self.logger.error(traceback.format_exc())
            return AIShellResult(success=False, message=f"An unexpected error occurred: {str(e)}")

    async def _handle_conflict(
        self, user_input: str, shell_command: str, conflict: str
    ) -> str:
        context = await self._initialize_context()
        options = await generate_conflict_resolution_options(
            user_input, conflict, context
        )

        if not options:
            return shell_command  # Return original command if no options are generated

        choice = await self.ui_handler.get_conflict_resolution_choice(conflict, options)

        if choice is None:
            return shell_command  # Return original command if user cancels

        return await resolve_conflict(conflict, choice, shell_command)

    async def _handle_command_error(
        self, user_input: str, shell_command: str, error_output: str, exit_code: int
    ) -> AIShellResult:
        self.logger.error(f"Command failed with exit code {exit_code}: {error_output}")

        context = await self._initialize_context()
        options = await generate_conflict_resolution_options(
            user_input, error_output, context
        )

        if not options:
            return AIShellResult(
                success=False, message=f"Command failed: {error_output}"
            )

        choice = await self.ui_handler.get_error_resolution_choice(
            error_output, options
        )

        if choice is None:
            return AIShellResult(success=False, message="Operation cancelled by user.")

        if "retry" in choice.lower():
            return await self.process_command(user_input)
        elif "modify" in choice.lower():
            modified_command = await self.ui_handler.edit_command(shell_command)
            return await self.process_command(modified_command)
        else:
            action_result = await self._execute_resolution_action(choice, shell_command)
            return AIShellResult(
                success=True, message=f"Action taken: {choice}\nResult: {action_result}"
            )

    async def _execute_resolution_action(self, choice: str, shell_command: str) -> str:
        if "remove" in choice.lower():
            dir_path = shell_command.split()[-1]
            result, exit_code = await self.command_executor.execute_command(
                f"rm -rf {dir_path}"
            )
            return (
                f"Removed existing directory: {dir_path}"
                if exit_code == 0
                else f"Failed to remove directory: {result}"
            )
        elif "rename" in choice.lower():
            dir_path = shell_command.split()[-1]
            new_path = f"{dir_path}_old"
            result, exit_code = await self.command_executor.execute_command(
                f"mv {dir_path} {new_path}"
            )
            return (
                f"Renamed existing directory to: {new_path}"
                if exit_code == 0
                else f"Failed to rename directory: {result}"
            )
        elif "sync" in choice.lower():
            dir_path = shell_command.split()[-1]
            result, exit_code = await self.command_executor.execute_command(
                f"git -C {dir_path} pull"
            )
            return (
                f"Synced existing directory: {dir_path}"
                if exit_code == 0
                else f"Failed to sync directory: {result}"
            )
        else:
            return "No action taken"

    def _parse_chained_commands(self, user_input: str) -> List[str]:
        # Simple implementation: split by semicolon
        return [cmd.strip() for cmd in user_input.split(";") if cmd.strip()]

    def _handle_missing_dependencies(self, missing_deps: List[str]) -> None:
        if self.interactive_mode:
            for dep in missing_deps:
                if self.ui_handler.confirm_installation(dep):
                    install_dependency(dep)
                else:
                    log_info(f"Skipped installation of {dep}")
        else:
            for dep in missing_deps:
                log_info(f"Auto-installing missing dependency: {dep}")
                install_dependency(dep)
            log_info("All missing dependencies have been installed.")

    async def _generate_shell_command(self, user_input: str) -> str:
        context = await self._initialize_context()
        generated_command, _, _ = await generate_command_from_prompt(
            user_input, context
        )
        return generated_command if generated_command else ""

    def _execute_command(self, shell_command: str) -> str:
        conflict = detect_conflict(shell_command)
        if conflict:
            resolution = self._get_conflict_resolution(conflict)
            return resolve_conflict(conflict, resolution)

        return execute_command(shell_command, self.logger)

    def _format_output(self, output: str) -> str:
        # Simple implementation: just return the output as is
        return output

    def _suggest_fix(self, error: Exception) -> str:
        error_analysis = analyze_error(error)
        suggested_fix = suggest_fix(error_analysis, self.context)
        return suggested_fix

    def _create_theme(self):
        return Theme(
            {
                "info": "cyan",
                "warning": "yellow",
                "error": "bold red",
                "critical": "bold white on red",
                "success": "bold green",
                "command": "bold magenta",
                "output": "green",
            }
        )

    def _create_style(self):
        return Style.from_dict(
            {
                "prompt": "ansicyan bold",
                "command": "ansigreen",
            }
        )

    def handle_interrupt_signal(self, sig, frame):
        self.console.print("\n[error]Execution interrupted by user (Ctrl + C).[/error]")
        sys.exit(0)

    async def process_command_v2(
        self, command: str, use_cache: bool = True
    ) -> AIShellResult:
        try:
            async with self.error_handler.catch_errors():
                ai_response = await self.processor.generate_ai_response(command)
                if ai_response is None:
                    return AIShellResult(
                        success=False, message="Failed to generate AI response."
                    )

                simplified_script = self.processor.simplify_script(ai_response)
                self.console.print(
                    "[bold cyan]AI generated the following plan:[/bold cyan]"
                )
                self.ui_handler.display_ai_response(simplified_script)

                user_choice = await self.ui_handler.confirm_execution()
                if user_choice == "":
                    output = await self.processor.process_command(
                        command,
                        ai_response,
                        simulation_mode=self.config.simulation_mode,
                        verbose_mode=self.config.verbose_mode,
                        interactive_mode=True,
                        use_cache=use_cache,
                    )
                    if output is not None:
                        self.ui_handler.display_command_output(command, output)
                        return AIShellResult(success=True, message=output)
                    else:
                        return AIShellResult(
                            success=False, message="Failed to process command."
                        )
                elif user_choice == "e":
                    edited_script = await self.ui_handler.edit_multiline(
                        simplified_script
                    )
                    output = await self.processor.execute_script_interactively(
                        edited_script,
                        simulation_mode=self.config.simulation_mode,
                        verbose_mode=self.config.verbose_mode,
                    )
                    self.ui_handler.display_command_output(command, output)
                    return AIShellResult(success=True, message=output)
                else:
                    return AIShellResult(
                        success=False, message="Command execution cancelled by user."
                    )
        except Exception as e:
            self.logger.error(f"Error in process_command: {str(e)}")
            return AIShellResult(success=False, message=f"An error occurred: {str(e)}")

    async def prompt_edit_command(self, ai_response: str) -> str:
        self.console.print(
            "[bold yellow]Expert mode: You can edit the generated script.[/bold yellow]"
        )
        edited = await self.ui_handler.edit_multiline(ai_response)
        return edited

    async def handle_initial_command(self, args):
        if len(args) > 1:
            initial_command = " ".join(args[1:])
            output = await self.process_command_v2(initial_command, use_cache=False)
            self.ui_handler.display_command_output(initial_command, output)
            return True
        return False

    async def handle_user_input(self, session, completer):
        try:
            return await asyncio.wait_for(
                session.prompt_async(
                    HTML('<prompt>AI Shell</prompt> <style fg="ansiyellow">></style> '),
                    completer=completer,
                    style=self.style,
                ),
                timeout=30,
            )
        except asyncio.TimeoutError:
            self.console.print("[yellow]Timeout: No input received.[/yellow]")
            return config.exit_command
        except (EOFError, KeyboardInterrupt):
            return config.exit_command

    async def run_shell(self):
        session = PromptSession(history=FileHistory(config.history_file))

        if len(sys.argv) > 1:
            await self.handle_initial_command(sys.argv)
            return

        def get_dynamic_completer():
            return WordCompleter(
                list(config.aliases.keys())
                + list(self.processor.history_manager.get_recent_commands(10))
                + [
                    config.exit_command,
                    config.help_command,
                    config.history_command,
                    config.simulate_command,
                    config.clear_cache_command,
                    config.clear_history_command,
                ]
            )

        self.ui_handler.display_welcome_message()

        while True:
            async with self.error_handler.catch_errors():
                prompt_text = await self.handle_user_input(
                    session, get_dynamic_completer()
                )

                if prompt_text.lower() == config.exit_command:
                    break
                elif prompt_text.lower() == config.help_command:
                    self.ui_handler.display_help()
                elif prompt_text.lower() == config.history_command:
                    self.ui_handler.display_history(
                        self.processor.history_manager.history
                    )
                elif prompt_text.lower() == config.simulate_command:
                    config.toggle_simulation_mode()
                    self.ui_handler.display_simulation_mode(config.simulation_mode)
                elif prompt_text.lower() == config.clear_cache_command:
                    await self.processor.cache_manager.clear_cache()
                elif prompt_text.lower() == config.clear_history_command:
                    self.processor.history_manager.clear_history()
                else:
                    await self.process_command_v2(prompt_text)

        await self.processor.cache_manager.clean_expired_cache()
        self.ui_handler.display_farewell_message()

    async def simulate_command(self, command: str) -> str:
        shell_command = await self._generate_shell_command(command)
        return self._simulate_command_execution(shell_command)

    def _simulate_command_execution(self, shell_command: str) -> str:
        return f"Simulated execution of: {shell_command}"

    def _get_conflict_resolution(self, conflict: str) -> str:
        if self.interactive_mode:
            return self.ui_handler.prompt_conflict_resolution(conflict)
        else:
            return self.config.get("default_conflict_resolution", "skip")

    async def clone_repository(self, repo_url: str, destination: str) -> Dict[str, Any]:
        """
        Clone a Git repository to the specified destination using shell commands.
        """
        try:
            command = f"git clone {repo_url} {destination}"
            output, return_code = await self.command_executor.execute_command(command)

            if return_code == 0:
                self.logger.info(f"Successfully cloned {repo_url} to {destination}")
                return {
                    "success": True,
                    "message": f"Repository cloned successfully to {destination}",
                }
            else:
                self.logger.error(f"Failed to clone repository: {output}")
                return {
                    "success": False,
                    "message": f"Failed to clone repository: {output}",
                }
        except Exception as e:
            return self.error_handler.handle_error(
                f"An error occurred while cloning the repository: {str(e)}"
            )