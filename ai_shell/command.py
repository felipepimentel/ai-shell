# command_processor.py
import asyncio
import shlex
import time
from dataclasses import dataclass
from typing import List

from rich.console import Console
from shellescape import quote

from .llm import ai, build_contextual_prompt
from .utils.cache import check_cache, save_cache
from .utils.console import (
    print_error_message,
    print_success_message,
    print_verbose_message,
)
from .utils.os_api import get_system_info

console = Console()


@dataclass
class CommandHistoryEntry:
    command: str
    output: str
    timestamp: str
    working_directory: str


class CommandProcessor:
    def __init__(self):
        self.history: List[CommandHistoryEntry] = []

    async def execute_command(self, command: str, simulation_mode: bool = False):
        command = quote(command)
        if simulation_mode:
            return f"[Simulation] Would execute: {command}", None

        command = shlex.split(command)
        try:
            process = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return stdout.decode("utf-8").strip(), None
            return None, stderr.decode("utf-8").strip()
        except Exception as e:
            return None, f"Command failed: {str(e)}"

    async def process_command(self, command: str, simulation_mode: bool):
        print_verbose_message(f"Processing command: {command}")
        system_info = get_system_info()

        cached_output = await check_cache(command)
        if cached_output:
            print_success_message(f"Using cached result: {cached_output}")
            return cached_output

        full_prompt = (
            await build_contextual_prompt(self.history) + f"Instruction: {command}"
        )
        ai_response = await ai.generate_command(full_prompt, system_info)

        if not ai_response:
            print_error_message("Error generating command.")
            return

        output, error = await self.execute_command(ai_response, simulation_mode)
        if error:
            print_error_message(f"Command error: {error}")
            self.append_to_history(ai_response, error)
            return

        print_success_message(f"Command output: {output}")
        self.append_to_history(ai_response, output)
        await save_cache(command, output)
        return f"Next step based on output: {output}"

    def append_to_history(self, command: str, output: str):
        self.history.append(
            CommandHistoryEntry(
                command=command,
                output=output,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                working_directory="current_working_directory_here",
            )
        )

    async def save_history(self):
        # Implement saving history to a file asynchronously here
        pass
