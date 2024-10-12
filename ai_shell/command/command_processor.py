from __future__ import annotations

from typing import Optional, Tuple, TypedDict

from ..config import config
from ..context_manager import ContextManager
from ..utils.logger import class_logger, get_logger
from .command_cache_manager import CommandCacheManager
from .command_executor import CommandExecutor
from .command_generator import CommandGenerationError, CommandGenerator
from .command_history_manager import CommandHistoryManager

logger = get_logger(__name__)

RECENT_COMMANDS_COUNT = 5
ERROR_EXIT_CODE = 1


class CommandContext(TypedDict):
    recent_commands: list[str]


class CommandProcessingError(Exception):
    pass


@class_logger
class CommandProcessor:
    def __init__(
        self,
        command_generator: CommandGenerator,
        command_executor: CommandExecutor,
        cache_manager: CommandCacheManager,
        context_builder: ContextManager,
    ):
        self.history_manager = CommandHistoryManager()
        self.command_generator = command_generator
        self.command_executor = command_executor
        self.cache_manager = cache_manager
        self.context_builder = context_builder

    async def process_command(
        self,
        command: str,
        interactive_mode: bool,
        use_cache: bool = True,
    ) -> Tuple[Optional[str], int]:
        try:
            if use_cache:
                cached_result = await self._check_cache(command)
                if cached_result:
                    return cached_result

            ai_response, tokens_used, model_used = await self._generate_ai_response(
                command
            )
            if ai_response is None:
                raise CommandProcessingError("Failed to generate AI response")

            output, return_code = await self._execute_command(
                ai_response, interactive_mode
            )

            if output is not None:
                await self._cache_command(
                    command, ai_response, output, return_code, tokens_used, model_used
                )

            return output, return_code
        except CommandProcessingError as e:
            logger.error(f"Error processing command: {str(e)}")
            return str(e), ERROR_EXIT_CODE

    async def _generate_ai_response(
        self, command: str
    ) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        context = self._build_context()
        try:
            return await self.command_generator.generate_command(command, context)
        except CommandGenerationError as e:
            raise CommandProcessingError(f"Failed to generate command: {str(e)}")

    def _build_context(self) -> CommandContext:
        return CommandContext(
            recent_commands=self.history_manager.get_recent_commands(
                RECENT_COMMANDS_COUNT
            )
        )

    async def _check_cache(self, command: str) -> Optional[Tuple[str, int]]:
        cached_command, cached_output = await self.cache_manager.check_cache(command)
        if cached_command and cached_output:
            self._log_cache_hit(command, cached_command, cached_output)
            return cached_output, 0
        return None

    async def _execute_command(
        self, ai_response: str, interactive_mode: bool
    ) -> Tuple[str, int]:
        timeout = (
            config.long_running_timeout
            if config.expert_mode
            else config.default_timeout
        )
        return await self.command_executor.execute_command(ai_response, timeout=timeout)

    async def _cache_command(
        self,
        command: str,
        ai_response: str,
        output: str,
        return_code: int,
        tokens_used: Optional[int],
        model_used: Optional[str],
    ):
        await self.cache_manager.cache_command(command, ai_response, output)
        self._append_to_history(
            command,
            output,
            ai_response,
            return_code,
            tokens_used,
            model_used,
            used_cache=False,
        )

    def _log_cache_hit(self, command: str, cached_command: str, cached_output: str):
        logger.info(f"Using cached output for command: {command}")
        self._append_to_history(
            command, cached_output, cached_command, 0, None, None, used_cache=True
        )

    def _append_to_history(
        self,
        command: str,
        output: str,
        ai_response: str,
        return_code: int,
        tokens_used: Optional[int],
        model_used: Optional[str],
        used_cache: bool,
    ):
        status = "Success" if return_code == 0 else "Failed"
        error_message = output if return_code != 0 else None
        self.history_manager.append_to_history(
            command=command,
            output=output,
            ai_response=ai_response,
            status=status,
            error_message=error_message,
            used_cache=used_cache,
            tokens_used=tokens_used,
            model_used=model_used,
        )

    async def execute_script_interactively(
        self, script: str, verbose_mode: bool
    ) -> Tuple[str, int]:
        timeout = (
            config.long_running_timeout
            if config.expert_mode
            else config.default_timeout
        )
        return await self.command_executor.execute_command(script, timeout=timeout)

    def simplify_script(self, script: str) -> str:
        simplified_script = []
        lines = script.split("\n")
        for line in lines:
            stripped_line = line.strip()
            if stripped_line and not stripped_line.startswith("#"):
                simplified_script.append(stripped_line)
        return "\n".join(simplified_script)
