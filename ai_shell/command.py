# command_processor.py
import asyncio
import shlex
import time
import re
from dataclasses import dataclass
from typing import List, Tuple

from rich.console import Console

from .llm import ai, build_contextual_prompt
from .utils.cache import check_cache, save_cache
from .utils.console import (
    print_error_message,
    print_success_message,
    print_verbose_message,
)
from .utils.os_api import get_system_info
from .utils.ai_history import save_ai_response

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

    async def execute_command(self, command: str, simulation_mode: bool = False) -> Tuple[str | None, str | None]:
        if simulation_mode:
            return f"[Simulation] Would execute: {command}", None

        try:
            # Use shlex.split to properly handle quoted arguments
            command_parts = shlex.split(command)
            
            print_verbose_message(f"Executing command: {command_parts}")
            
            process = await asyncio.create_subprocess_exec(
                *command_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode("utf-8").strip(), None
            else:
                return None, stderr.decode("utf-8").strip()
        except Exception as e:
            return None, f"Command execution failed: {str(e)}"

    def extract_command(self, ai_response: str) -> str:
        # Remove qualquer bloco de código markdown
        code_block_pattern = r'```[\w\s]*\n(.*?)\n```'
        code_block_match = re.search(code_block_pattern, ai_response, re.DOTALL)
        if code_block_match:
            ai_response = code_block_match.group(1).strip()
        
        # Remove qualquer prefixo de shell (como $, #, ou qualquer outro caractere não alfanumérico no início da linha)
        ai_response = re.sub(r'^[^\w\s]+', '', ai_response.strip(), flags=re.MULTILINE)
        
        # Pega a primeira linha não vazia
        command = next((line.strip() for line in ai_response.split('\n') if line.strip()), '')
        
        return command

    async def process_command(self, command: str, simulation_mode: bool):
        print_verbose_message(f"Processing command: {command}")
        system_info = get_system_info()

        cached_output = await check_cache(command)
        if cached_output:
            print_success_message(f"Using cached result: {cached_output}")
            return cached_output

        full_prompt = (
            await build_contextual_prompt(self.history)
            + f"\nSystem Info: {system_info}\n"
            + f"User Request: {command}\n"
            + "Generate a single shell command to fulfill the user's request. "
            + "Provide only the command without any explanation or additional steps. "
            + "Do not include 'cd' commands or any navigation unless explicitly requested. "
            + "The command should be executable as-is in the current directory."
        )
        ai_response = await ai.generate_command(full_prompt)

        if not ai_response:
            print_error_message("Error generating command.")
            return

        extracted_command = self.extract_command(ai_response)
        print_verbose_message(f"Generated command: {extracted_command}")

        # Save AI response to history with both full response and extracted command
        await save_ai_response(command, f"Full AI response: {ai_response}\nExtracted command: {extracted_command}")

        output, error = await self.execute_command(extracted_command, simulation_mode)
        if error:
            print_error_message(f"Command error: {error}")
            self.append_to_history(extracted_command, error)
            return

        print_success_message(f"Command output: {output}")
        self.append_to_history(extracted_command, output)
        await save_cache(command, output)
        return output  # Return only the output, not a "Next step" message

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

    def clear_history(self):
        self.history.clear()

