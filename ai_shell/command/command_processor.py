from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, List, Optional

from prompt_toolkit import prompt

from ..config import config
from ..utils.logger import get_logger

if TYPE_CHECKING:
    from .command_cache_manager import CommandCacheManager
    from .command_executor import CommandExecutor
    from .command_generator import CommandGenerator
    from .command_history_manager import CommandHistoryManager
    from .context_builder import ContextBuilder

logger = get_logger("ai_shell.command_processor")


class CommandProcessor:
    def __init__(
        self,
        command_executor: CommandExecutor,
        cache_manager: CommandCacheManager,
        command_generator: CommandGenerator,
        history_manager: CommandHistoryManager,
        context_builder: ContextBuilder,
    ) -> None:
        self.last_generated_command: str = ""
        self._last_command_from_cache: bool = False
        self.command_executor = command_executor
        self.cache_manager = cache_manager
        self.command_generator = command_generator
        self.history_manager = history_manager
        self.context_builder = context_builder

    async def process_command(
        self,
        command: str,
        simulation_mode: bool,
        verbose_mode: bool,
        interactive_mode: bool,
    ) -> Optional[str]:
        if verbose_mode:
            logger.debug(f"Processing command: {command}")

        command = self.resolve_alias(command) or command

        cached_command, cached_output = await self.cache_manager.check_cache(command)
        if cached_output:
            return self.handle_cached_output(command, cached_command, cached_output)

        context = self.context_builder.build_enhanced_context(
            self.history_manager.get_recent_commands(5)
        )
        (
            ai_response,
            tokens_used,
            model_used,
        ) = await self.command_generator.generate_command(
            command, self.history_manager.history, context
        )
        if not ai_response:
            return None

        if interactive_mode:
            ai_response = self.prompt_edit_command(ai_response)

        commands = self.extract_commands(ai_response)
        if not commands:
            return None

        output = await self.execute_commands(commands, simulation_mode, verbose_mode)
        await self.handle_command_output(
            command, output, ai_response, tokens_used, model_used
        )
        return output

    def resolve_alias(self, command: str) -> Optional[str]:
        parts = command.split()
        if parts and parts[0] in config.aliases:
            aliased_command = f"{config.aliases[parts[0]]} {' '.join(parts[1:])}"
            logger.info(f"Using alias: {command} -> {aliased_command}")
            return aliased_command
        return None

    def prompt_edit_command(self, command: str) -> str:
        edited_command = prompt(
            f"Generated command:\n{command}\nDo you want to edit it? [y/N]: "
        )
        if edited_command.lower() == "y":
            return prompt("Edit the command: ")
        return command

    def extract_commands(self, ai_response: str) -> List[str]:
        ai_response = ai_response.strip("`")
        lines = ai_response.split("\n")
        script = "\n".join(lines)

        if not script.strip() or all(line.strip().startswith("#") for line in lines):
            logger.warning(
                "The generated script appears to be empty or contains only comments."
            )
            return []

        return [script]

    async def execute_commands(
        self,
        commands: List[str],
        simulation_mode: bool = False,
        verbose_mode: bool = False,
    ) -> str:
        if simulation_mode:
            return "\n".join(
                [f"[Simulation] Would execute:\n{cmd}" for cmd in commands]
            )

        results = await asyncio.gather(
            *[self._execute_single_command(cmd) for cmd in commands]
        )
        return "\n".join(results)

    async def _execute_single_command(self, command: str) -> str:
        try:
            output, returncode = await self.command_executor.execute_command(
                command, timeout=config.default_timeout
            )
            if returncode != 0:
                logger.warning(f"Command exited with non-zero status: {returncode}")
            return output
        except Exception as e:
            logger.error(f"Command execution failed: {str(e)}")
            return str(e)

    async def handle_command_output(
        self,
        command: str,
        output: str,
        ai_response: str,
        tokens_used: Optional[int],
        model_used: Optional[str],
    ) -> None:
        success = not output.startswith("Error:")
        status = "Success" if success else "Error"
        error_message = output if not success else None

        logger.info(
            "Commands executed successfully" if success else "Command execution failed"
        )
        self.history_manager.append_to_history(
            command,
            output,
            ai_response,
            status,
            error_message,
            used_cache=False,
            tokens_used=tokens_used,
            model_used=model_used,
        )
        await self.cache_manager.cache_command(
            command, self.last_generated_command, output
        )

    def handle_cached_output(
        self, command: str, cached_command: str, cached_output: str
    ) -> str:
        logger.info(f"Using cached output for command: {command}")
        self.history_manager.append_to_history(
            command,
            cached_output,
            cached_command,
            "Success (Cached)",
            None,
            used_cache=True,
            tokens_used=None,
            model_used=None,
        )
        return cached_output
