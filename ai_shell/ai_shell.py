import asyncio
import os
import pwd
import sys
from typing import Any, Dict

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from .command.command_cache_manager import CommandCacheManager
from .command.command_executor import CommandExecutor
from .command.command_generator import CommandGenerator
from .command.command_processor import CommandProcessor
from .config import config
from .context_manager import ContextBuilder
from .datatypes import AIShellResult
from .ui_handler import UIHandler
from .utils.cache import init_cache
from .utils.error_manager import ErrorHandler
from .utils.logger import get_logger, setup_logging

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
        self.processor = CommandProcessor(
            command_generator=self.command_generator,
            command_executor=self.command_executor,
            cache_manager=self.cache_manager,
            context_builder=self.context_builder,
        )
        self.logger = logger
        self.error_handler = ErrorHandler()
        self.config = config

        self.style = self._create_style()
        self.console = self.ui_handler.console

    @classmethod
    async def create(cls, non_interactive: bool = False, dry_run: bool = False):
        command_generator = CommandGenerator()
        command_executor = CommandExecutor()
        ui_handler = UIHandler()
        return cls(command_generator, command_executor, ui_handler)

    async def initialize(self):
        await init_cache()
        await self._initialize_context()

    async def _initialize_context(self) -> Dict[str, Any]:
        try:
            user = os.getlogin()
        except OSError:
            user = pwd.getpwuid(os.getuid())[0]

        context = {
            "current_directory": os.getcwd(),
            "user": user,
            "os": sys.platform,
        }
        self.context_builder.update_context(context)
        return context

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
                self.ui_handler.display_ai_plan(simplified_script)

                user_choice = await self.ui_handler.confirm_execution()
                if user_choice == "":
                    return await self._execute_command(command, ai_response, use_cache)
                elif user_choice == "e":
                    return await self._execute_edited_script(command, simplified_script)
                else:
                    return AIShellResult(
                        success=False, message="Command execution cancelled by user."
                    )
        except Exception as e:
            self.logger.error(f"Error in process_command: {str(e)}")
            return AIShellResult(success=False, message=f"An error occurred: {str(e)}")

    async def _execute_command(
        self, command: str, ai_response: str, use_cache: bool
    ) -> AIShellResult:
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
            return AIShellResult(success=False, message="Failed to process command.")

    async def _execute_edited_script(
        self, command: str, simplified_script: str
    ) -> AIShellResult:
        edited_script = await self.ui_handler.edit_multiline(simplified_script)
        output = await self.processor.execute_script_interactively(
            edited_script,
            simulation_mode=self.config.simulation_mode,
            verbose_mode=self.config.verbose_mode,
        )
        self.ui_handler.display_command_output(command, output)
        return AIShellResult(success=True, message=output)

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

        if await self.handle_initial_command(sys.argv):
            return

        self.ui_handler.display_welcome_message()

        while True:
            async with self.error_handler.catch_errors():
                prompt_text = await self.handle_user_input(
                    session, self._get_dynamic_completer()
                )

                if prompt_text.lower() == config.exit_command:
                    break

                await self._process_shell_command(prompt_text)

        await self.processor.cache_manager.clean_expired_cache()
        self.ui_handler.display_farewell_message()

    def _get_dynamic_completer(self):
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

    async def _process_shell_command(self, command: str):
        command_lower = command.lower()
        if command_lower == config.help_command:
            self.ui_handler.display_help()
        elif command_lower == config.history_command:
            self.ui_handler.display_history(self.processor.history_manager.history)
        elif command_lower == config.simulate_command:
            config.toggle_simulation_mode()
            self.ui_handler.display_simulation_mode(config.simulation_mode)
        elif command_lower == config.clear_cache_command:
            await self.processor.cache_manager.clear_cache()
        elif command_lower == config.clear_history_command:
            self.processor.history_manager.clear_history()
        else:
            await self.process_command_v2(command)

    def _create_style(self):
        return Style.from_dict(
            {
                "prompt": "ansicyan bold",
                "command": "ansigreen",
            }
        )

    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Starting AIShell cleanup")
        await self.command_executor.shutdown()
        logger.info("AIShell cleanup completed.")
