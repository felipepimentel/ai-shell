import asyncio
import os
import sys
import traceback
from typing import List

import aiohttp
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.table import Table
from rich.theme import Theme

from .command import CommandHistoryEntry, CommandProcessor
from .config import config
from .utils.cache import clean_expired_cache, clear_cache, init_cache
from .utils.logger import get_logger, setup_logging

logger = get_logger("ai_shell.cli")


class AIShell:
    def __init__(self):
        self.processor = CommandProcessor()
        self.simulation_mode = config.simulation_mode
        self.verbose_mode = config.verbose_mode

        theme = Theme(
            {
                "info": "cyan",
                "warning": "yellow",
                "error": "bold red",
                "critical": "bold white on red",
            }
        )
        self.console = Console(theme=theme)
        setup_logging(self.console)
        self.logger = get_logger("ai_shell.cli")

    async def handle_initial_command(self, args):
        if len(args) > 1:
            initial_command = " ".join(args[1:])
            output = await self.processor.process_command(
                initial_command, self.simulation_mode, self.verbose_mode
            )
            if output:
                generated_command = self.processor.get_last_generated_command()
                self.display_command_output_inline(
                    initial_command, output, generated_command
                )
            return True
        return False

    async def handle_user_input(self, session, completer):
        try:
            return await session.prompt_async(f"{os.getcwd()} > ", completer=completer)
        except (EOFError, KeyboardInterrupt):
            return config.exit_command
        except asyncio.TimeoutError:
            logger.warning("Timeout: No input provided.")
            return config.exit_command

    def display_command_output_inline(
        self, command: str, output: str, generated_command: str
    ):
        self.console.print(f"[bold cyan]{generated_command}[/bold cyan]")
        self.console.print(f"[green]{output}[/green]")

    def display_command_output_cli(self, command: str, output: str):
        self.console.print(f"[bold green]Executed Command:[/bold green] {command}")
        self.console.print("[bold blue]--- Command Output ---[/bold blue]")
        self.console.print(output)

    def display_help(self):
        help_table = Table(title="AI Shell Help", box="ROUNDED")
        help_table.add_column("Command", style="cyan", justify="left")
        help_table.add_column("Description", style="magenta", justify="left")
        help_table.add_row("exit", "Exit the AI Shell")
        help_table.add_row("help", "Display this help message")
        help_table.add_row("history", "Show command history")
        help_table.add_row("simulate", "Toggle simulation mode")
        help_table.add_row("clear_cache", "Clear the command cache")
        help_table.add_row("clear_history", "Clear the command history")
        help_table.add_row("<any text>", "Ask AI to generate and execute a command")

        self.console.print(help_table)

    def display_history(self, history: List[CommandHistoryEntry]):
        history_table = Table(title="Command History", box="ROUNDED", show_lines=True)
        history_table.add_column("Timestamp", style="yellow")
        history_table.add_column("Working Directory", style="blue")
        history_table.add_column("Command", style="cyan")
        history_table.add_column("Output", style="green", max_width=40)

        for entry in list(history)[-10:]:
            truncated_output = (
                (entry.output[:50] + "...") if len(entry.output) > 50 else entry.output
            )
            history_table.add_row(
                entry.timestamp,
                entry.working_directory,
                f"[bold cyan]{entry.command}[/bold cyan]",
                truncated_output,
            )

        self.console.print(history_table)

    async def run_shell(self):
        await init_cache()
        session = PromptSession(history=FileHistory(config.history_file))

        def get_dynamic_completer():
            return WordCompleter(
                list(config.aliases.keys())
                + list(self.processor.get_recent_commands())
                + [
                    config.exit_command,
                    config.help_command,
                    config.history_command,
                    config.simulate_command,
                    config.clear_cache_command,
                    config.clear_history_command,
                ]
            )

        self.console.print("[bold green]Welcome to AI Shell![/bold green]")
        self.console.print(
            f"Type '{config.exit_command}' to quit, '{config.help_command}' for assistance, "
            f"'{config.simulate_command}' to toggle simulation mode, or start with your command."
        )

        self.logger.info("Welcome to AI Shell!")
        self.logger.info(
            f"Type '{config.exit_command}' to quit, '{config.help_command}' for assistance, "
            f"'{config.simulate_command}' to toggle simulation mode, or start with your command."
        )

        while True:
            prompt_text = await self.handle_user_input(session, get_dynamic_completer())

            if prompt_text.lower() == config.exit_command:
                break
            elif prompt_text.lower() == config.help_command:
                self.display_help()
            elif prompt_text.lower() == config.history_command:
                self.display_history(self.processor.history)
            elif prompt_text.lower() == config.simulate_command:
                self.simulation_mode = not self.simulation_mode
                logger.info(
                    f"Simulation mode {'enabled' if self.simulation_mode else 'disabled'}"
                )
                self.console.print(
                    f"[cyan]Simulation mode {'enabled' if self.simulation_mode else 'disabled'}[/cyan]"
                )
            elif prompt_text.lower() == config.clear_cache_command:
                await clear_cache()
                logger.info("Cache cleared successfully")
                self.console.print("[green]Cache cleared successfully.[/green]")
            elif prompt_text.lower() == config.clear_history_command:
                self.processor.clear_history()
                logger.info("Command history cleared successfully")
                self.console.print(
                    "[green]Command history cleared successfully.[/green]"
                )
            elif prompt_text.startswith("cd "):
                try:
                    os.chdir(prompt_text.split(" ", 1)[1])
                except FileNotFoundError:
                    logger.error("Directory not found")
                    self.console.print("[red]Directory not found.[/red]")
                except PermissionError:
                    logger.error("Permission denied")
                    self.console.print("[red]Permission denied.[/red]")
            else:
                output = await self.processor.process_command(
                    prompt_text, self.simulation_mode, self.verbose_mode
                )
                if output:
                    self.display_command_output_cli(prompt_text, output)

        await self.processor.save_history()
        await clean_expired_cache()
        self.console.print(
            "[bold green]Thank you for using AI Shell. Goodbye![/bold green]"
        )


async def main():
    shell = AIShell()
    try:
        initial_command_processed = await shell.handle_initial_command(sys.argv)
        if not initial_command_processed:
            await shell.run_shell()
    except KeyboardInterrupt:
        logger.warning("Program interrupted by user")
        shell.console.print("[yellow]Program interrupted by user.[/yellow]")
    except aiohttp.ClientError as e:
        logger.error(f"API connection error: {str(e)}")
        shell.console.print(f"[red]Error connecting to AI service: {str(e)}[/red]")
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb = traceback.extract_tb(exc_traceback)
        filename, line_number, func_name, text = tb[-1]
        error_message = f"Unexpected error in file {filename}, line {line_number}, in {func_name}: {text}\n{str(e)}"
        logger.error(
            "Unexpected error", error=error_message, traceback=traceback.format_exc()
        )
        shell.console.print(f"[red]{error_message}[/red]")


if __name__ == "__main__":
    asyncio.run(main())
