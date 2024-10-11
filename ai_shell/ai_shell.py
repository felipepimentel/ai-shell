from typing import Callable, Dict

from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style

from .command.command_cache_manager import CommandCacheManager
from .command.command_executor import CommandExecutor
from .command.command_generator import CommandGenerator
from .command.command_processor import CommandProcessor
from .config import config
from .context_manager import ContextManager
from .datatypes import AIShellResult
from .error_manager import ErrorHandler
from .ui_handler import UIHandler
from .utils.cache import init_cache
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
        self.context_builder = ContextManager()
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
        self.internal_commands = self._create_internal_commands()

    @classmethod
    async def create(cls, non_interactive: bool = False, dry_run: bool = False):
        command_generator = CommandGenerator()
        command_executor = CommandExecutor(dry_run=dry_run)
        ui_handler = UIHandler()
        return cls(command_generator, command_executor, ui_handler)

    async def initialize(self):
        await init_cache()
        self.ui_handler.display_welcome_message()

    async def run_shell(self):
        try:
            while True:
                command = await self._get_user_input()
                if command.lower() == self.config.exit_command:
                    break
                await self._process_shell_command(command)
        except Exception as e:
            self.logger.error(f"An error occurred: {str(e)}")
        finally:
            await self.cleanup()

    async def _get_user_input(self) -> str:
        return await self.ui_handler.session.prompt_async(
            HTML(f"<ansigreen>{self.config.prompt}</ansigreen>"),
            style=self.style,
            completer=self._get_dynamic_completer(),
        )

    async def _process_shell_command(self, command: str):
        command_lower = command.lower()
        if command_lower in self.internal_commands:
            await self.internal_commands[command_lower]()
        else:
            await self.process_command(command)

    @staticmethod
    def _create_style() -> Style:
        return Style.from_dict(
            {
                "prompt": "ansicyan bold",
                "command": "ansigreen",
            }
        )

    def _create_internal_commands(self) -> Dict[str, Callable]:
        return {
            self.config.help_command: self.ui_handler.display_help,
            self.config.history_command: lambda: self.ui_handler.display_history(
                self.processor.history_manager.history
            ),
            self.config.clear_cache_command: self.processor.cache_manager.clear_cache,
            self.config.clear_history_command: self.processor.history_manager.clear_history,
        }

    async def cleanup(self):
        self.logger.info("Starting AIShell cleanup")
        await self.command_executor.shutdown()
        await self.processor.cache_manager.clean_expired_cache()
        self.ui_handler.display_farewell_message()
        self.logger.info("AIShell cleanup completed.")

    async def process_command(self, command: str) -> AIShellResult:
        output, return_code = await self.processor.process_command(
            command, interactive_mode=True
        )
        return AIShellResult(success=return_code == 0, message=output)

    def _get_dynamic_completer(self):
        commands = list(self.internal_commands.keys()) + [self.config.exit_command]
        return WordCompleter(commands)
