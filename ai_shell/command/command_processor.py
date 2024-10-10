from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING, List, Optional, Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

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

    async def generate_ai_response(self, command: str) -> Optional[str]:
        context = self.context_builder.build_enhanced_context(
            self.history_manager.get_recent_commands(5)
        )
        ai_response, _, _ = await self.command_generator.generate_command(
            command, self.history_manager.history, context
        )
        return ai_response

    async def process_command(
        self,
        original_command: str,
        ai_response: str,
        simulation_mode: bool,
        verbose_mode: bool,
        interactive_mode: bool,
        use_cache: bool = True,
        progress_callback: Callable[[int], None] = None,
    ) -> Optional[str]:
        if verbose_mode:
            logger.debug(f"Processing command: {original_command}")

        if use_cache:
            cached_command, cached_output = await self.cache_manager.check_cache(original_command)
            if cached_output:
                return self.handle_cached_output(original_command, cached_command, cached_output)

        simplified_script = self.simplify_script(ai_response)
        output = await self.execute_script_interactively(simplified_script, simulation_mode, verbose_mode, progress_callback)
        await self.handle_command_output(
            original_command, output, ai_response, None, None
        )
        return output

    def simplify_script(self, script: str) -> str:
        lines = script.split('\n')
        simplified_lines = []
        for line in lines:
            if not line.strip().startswith('#') and line.strip():
                simplified_lines.append(line)
        return '\n'.join(simplified_lines)

    async def execute_script_interactively(
        self,
        script: str,
        simulation_mode: bool,
        verbose_mode: bool,
        progress_callback: Callable[[int], None] = None,
    ) -> str:
        lines = script.split('\n')
        results = []
        total_lines = len(lines)

        for i, line in enumerate(lines):
            if line.startswith("echo "):
                message = line[5:].strip('"')
                if message.startswith("USER_INPUT:"):
                    user_input = await self._get_user_input(message[11:])
                    if user_input.lower() == 'q':
                        return "Operation cancelled by user."
                elif message.startswith("INFO:") or message.startswith("WARNING:"):
                    logger.info(message)
                    results.append(message)
                continue

            if simulation_mode:
                results.append(f"[Simulation] Would execute: {line}")
            else:
                result = await self._execute_single_command(line)
                results.append(result)

            if progress_callback:
                progress_callback(int((i + 1) / total_lines * 100))

        return "\n".join(results)

    def resolve_alias(self, command: str) -> Optional[str]:
        parts = command.split()
        if parts and parts[0] in config.aliases:
            aliased_command = f"{config.aliases[parts[0]]} {' '.join(parts[1:])}"
            logger.info(f"Using alias: {command} -> {aliased_command}")
            return aliased_command
        return None

    async def prompt_edit_command(self, command: str) -> str:
        session = PromptSession()
        with patch_stdout():
            response = await session.prompt_async(
                f"Generated command:\n{command}\nDo you want to edit it? [y/N]: "
            )
            if response.lower() == "y":
                return await session.prompt_async("Edit the command: ")
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

    async def _execute_single_command(self, command: str) -> str:
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE
            )

            async def read_stream(stream):
                output = []
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    line = line.decode().strip()
                    output.append(line)
                    if line.startswith("USER_INPUT:"):
                        user_input = await self._get_user_input(line[11:])
                        await process.stdin.write(f"{user_input}\n".encode())
                    logger.info(f"Command output: {line}")  # Adicione esta linha para log em tempo real
                return "\n".join(output)

            stdout_task = asyncio.create_task(read_stream(process.stdout))
            stderr_task = asyncio.create_task(read_stream(process.stderr))

            try:
                await asyncio.wait_for(process.wait(), timeout=config.long_running_timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Command is taking longer than expected. Timeout set to {config.long_running_timeout} seconds.")
                await process.wait()
                return f"Error: Command execution timed out after {config.long_running_timeout} seconds."

            stdout_output = await stdout_task
            stderr_output = await stderr_task

            if process.returncode != 0:
                logger.warning(f"Command exited with non-zero status: {process.returncode}")
            
            return stdout_output + ("\n" + stderr_output if stderr_output else "")
        except Exception as e:
            logger.error(f"Command execution failed: {str(e)}")
            return str(e)

    async def _get_user_input(self, prompt: str) -> str:
        session = PromptSession()
        with patch_stdout():
            return await session.prompt_async(f"{prompt}: ")

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