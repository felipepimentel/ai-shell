from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..utils.logger import get_logger
from .command_history_manager import CommandHistoryManager  # Add this import

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class CommandProcessor:
    def __init__(self):
        self.history_manager = CommandHistoryManager()
        self.command_generator = None
        self.command_executor = None
        self.cache_manager = None
        self.context_builder = None

    async def generate_ai_response(self, command: str) -> Optional[str]:
        context = self.context_builder.build_enhanced_context(
            self.history_manager.get_recent_commands(5)
        )
        ai_response, _, _ = await self.command_generator.generate_command(
            command, context
        )
        return ai_response

    async def process_command(
        self,
        command: str,
        ai_response: str,
        simulation_mode: bool,
        verbose_mode: bool,
        interactive_mode: bool,
        use_cache: bool = True,
    ) -> Optional[str]:
        if use_cache:
            cached_command, cached_output = await self.cache_manager.check_cache(
                command
            )
            if cached_command and cached_output:
                return self._handle_cached_output(
                    command, cached_command, cached_output
                )

        output = await self.command_executor.execute_command(
            ai_response, simulation_mode, verbose_mode
        )

        if output is not None:
            output_str = str(output)
            await self.cache_manager.cache_command(command, ai_response, output_str)
            self.history_manager.append_to_history(
                command=command,
                output=output_str,
                ai_response=ai_response,
                status="Success",
                error_message=None,
                used_cache=False,
                tokens_used=None,
                model_used=None,
            )

        return output

    def simplify_script(self, script: str) -> str:
        # Implement logic to simplify the script
        return script

    async def execute_script_interactively(
        self, script: str, simulation_mode: bool, verbose_mode: bool
    ) -> str:
        # Implement logic for interactive script execution
        return await self.command_executor.execute_command(
            script, simulation_mode, verbose_mode
        )

    def _handle_cached_output(
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
