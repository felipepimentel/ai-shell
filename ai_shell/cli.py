from __future__ import annotations

import asyncio
import os
import signal
import sys
import traceback
from contextlib import asynccontextmanager
from typing import List

import aiohttp
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.theme import Theme

from .CommandProcessor import CommandProcessor
from .config import config
from .datatypes import CommandHistoryEntry
from .utils.cache import clean_expired_cache, clear_cache, init_cache
from .utils.logger import get_logger, setup_logging

logger = get_logger("ai_shell.cli")


class AIShell:
    def __init__(self):
        theme = Theme(
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
        self.console = Console(theme=theme)
        setup_logging(self.console)
        self.logger = get_logger("ai_shell.cli")

        self.processor = CommandProcessor(self.console)
        self.simulation_mode = config.simulation_mode
        self.verbose_mode = config.verbose_mode

        signal.signal(signal.SIGINT, self.handle_interrupt_signal)

        self.style = Style.from_dict(
            {
                "prompt": "ansicyan bold",
                "command": "ansigreen",
            }
        )

    def handle_interrupt_signal(self, sig, frame):
        self.console.print("\n[error]Execution interrupted by user (Ctrl + C).[/error]")
        sys.exit(0)

    def display_command_output_inline(
        self, command: str, output: str, generated_command: str
    ):
        command_syntax = Syntax(
            generated_command, "bash", theme="monokai", line_numbers=True
        )
        command_panel = Panel(
            command_syntax,
            title="AI Generated Command",
            border_style="cyan",
            expand=False,
        )

        # Tenta renderizar a saída como markdown, se falhar, exibe como texto simples
        try:
            output_content = Markdown(output)
        except Exception as e:
            output_content = output
            print(f"Error converting to Markdown: {e}")

        output_panel = Panel(
            output_content, title="Command Output", border_style="green", expand=False
        )
        self.console.print(Columns([command_panel, output_panel]))

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
            if hasattr(self.processor, "save_history") and callable(
                self.processor.save_history
            ):
                await self.processor.save_history()
            return True
        return False

    async def handle_user_input(self, session, completer):
        try:
            return await session.prompt_async(
                HTML('<prompt>AI Shell</prompt> <style fg="ansiyellow">></style> '),
                completer=completer,
                style=self.style,
            )
        except (EOFError, KeyboardInterrupt):
            return config.exit_command
        except asyncio.TimeoutError:
            logger.warning("Timeout: No input provided.")
            return config.exit_command

    @asynccontextmanager
    async def error_handler(self):
        try:
            yield
        except aiohttp.ClientError as e:
            logger.error(f"API connection error: {str(e)}")
            self.console.print(f"[red]Error connecting to AI service: {str(e)}[/red]")
        except asyncio.TimeoutError:
            logger.error("Operation timed out")
            self.console.print("[red]Operation timed out. Please try again.[/red]")
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = traceback.extract_tb(exc_traceback)
            filename, line_number, func_name, text = tb[-1]
            error_message = f"Unexpected error in file {filename}, line {line_number}, in {func_name}: {text}\n{str(e)}"
            logger.error(
                "Unexpected error",
                error=error_message,
                traceback=traceback.format_exc(),
            )
            self.console.print(f"[red]{error_message}[/red]")

    async def process_command(self, command: str):
        async with self.error_handler():
            self.console.print("[cyan]Processing command...[/cyan]")

            output = await self.processor.process_command(
                command, self.simulation_mode, self.verbose_mode
            )

            if output:
                self.console.print("[green]Command executed successfully[/green]")
                generated_command = self.processor.get_last_generated_command()
                self.display_command_output_inline(command, output, generated_command)
            else:
                self.console.print("[red]Command execution failed[/red]")

            await (
                self.processor.save_history()
            )  # Aguarda explicitamente o salvamento do histórico

        return output

    def display_command_status(self, command: str):
        status_panel = Panel(
            f"[bold]Command executed:[/bold]\n{command}",
            title="Execution Status",
            border_style="cyan",
            expand=False,
        )
        self.console.print(status_panel)

    def display_help(self):
        help_table = Table(
            title="AI Shell Help",
            box="ROUNDED",
            show_header=True,
            header_style="bold magenta",
        )
        help_table.add_column("Command", style="cyan", justify="left")
        help_table.add_column("Description", style="green", justify="left")
        help_table.add_row("exit", "Exit the AI Shell")
        help_table.add_row("help", "Display this help message")
        help_table.add_row("history", "Show command history")
        help_table.add_row("simulate", "Toggle simulation mode")
        help_table.add_row("clear_cache", "Clear the command cache")
        help_table.add_row("clear_history", "Clear the command history")
        help_table.add_row("<any text>", "Ask AI to generate and execute a command")

        self.console.print(
            Panel(
                help_table, title="AI Shell Help", border_style="magenta", expand=False
            )
        )

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

        self.console.print(
            Panel(
                history_table,
                title="Command History",
                border_style="blue",
                expand=False,
            )
        )

    async def run_shell(self):
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

        welcome_message = Panel(
            Markdown(
                "# Welcome to AI Shell!\n\n"
                f"- Type `{config.exit_command}` to quit\n"
                f"- Type `{config.help_command}` for assistance\n"
                f"- Type `{config.simulate_command}` to toggle simulation mode\n"
                "- Or start with your command"
            ),
            title="AI Shell",
            border_style="green",
            expand=False,
        )
        self.console.print(welcome_message)

        self.logger.info("Welcome to AI Shell!")

        while True:
            async with self.error_handler():
                prompt_text = await self.handle_user_input(
                    session, get_dynamic_completer()
                )

                if prompt_text.lower() == config.exit_command:
                    break
                elif prompt_text.lower() == config.help_command:
                    self.display_help()
                elif prompt_text.lower() == config.history_command:
                    self.display_history(self.processor.history)
                elif prompt_text.lower() == config.simulate_command:
                    self.toggle_simulation_mode()
                elif prompt_text.lower() == config.clear_cache_command:
                    await self.clear_cache()
                elif prompt_text.lower() == config.clear_history_command:
                    self.clear_history()
                elif prompt_text.lower() == "clear-all":  # Nova opção
                    await self.clear_all()
                elif prompt_text.startswith("cd "):
                    self.change_directory(prompt_text)
                elif prompt_text.lower().startswith("alias "):
                    self.set_alias(prompt_text)
                elif prompt_text.lower() == "aliases":
                    self.display_aliases()
                else:
                    with Live(self.console.render_live(), refresh_per_second=4) as live:
                        await self.process_command(prompt_text)
                        live.update(self.console.render_live())
                    await self.processor.save_history()

        await clean_expired_cache()
        self.console.print(
            Panel(
                "[bold green]Thank you for using AI Shell. Goodbye![/bold green]",
                title="Farewell",
                border_style="green",
                expand=False,
            )
        )

    def toggle_simulation_mode(self):
        self.simulation_mode = not self.simulation_mode
        logger.info(
            f"Simulation mode {'enabled' if self.simulation_mode else 'disabled'}"
        )
        self.console.print(
            Panel(
                f"[cyan]Simulation mode {'enabled' if self.simulation_mode else 'disabled'}[/cyan]",
                title="Mode Change",
                border_style="cyan",
                expand=False,
            )
        )

    async def clear_cache(self):
        await clear_cache()
        logger.info("Cache cleared successfully")
        self.console.print(
            Panel(
                "[success]Cache cleared successfully.[/success]",
                title="Cache Info",
                border_style="green",
                expand=False,
            )
        )

    def clear_history(self):
        self.processor.clear_history()
        logger.info("Command history cleared successfully")
        self.console.print(
            Panel(
                "[success]Command history cleared successfully.[/success]",
                title="History Info",
                border_style="green",
                expand=False,
            )
        )

    def change_directory(self, command: str):
        try:
            new_dir = command.split(" ", 1)[1]
            os.chdir(new_dir)
            logger.info(f"Changed directory to: {new_dir}")
            self.console.print(f"[green]Changed directory to: {new_dir}[/green]")
        except FileNotFoundError:
            logger.error("Directory not found")
            self.console.print(
                Panel(
                    "[error]Directory not found.[/error]",
                    title="Error",
                    border_style="red",
                    expand=False,
                )
            )
        except PermissionError:
            logger.error("Permission denied")
            self.console.print(
                Panel(
                    "[error]Permission denied.[/error]",
                    title="Error",
                    border_style="red",
                    expand=False,
                )
            )

    def set_alias(self, command: str):
        parts = command.split(" ", 2)
        if len(parts) == 3:
            alias, value = parts[1], parts[2]
            config.aliases[alias] = value
            logger.info(f"Alias set: {alias} = {value}")
            self.console.print(f"[green]Alias set: {alias} = {value}[/green]")
        else:
            logger.warning("Invalid alias command")
            self.console.print(
                "[yellow]Invalid alias command. Use: alias name value[/yellow]"
            )

    def display_aliases(self):
        if config.aliases:
            aliases_table = Table(
                title="Aliases",
                box="ROUNDED",
                show_header=True,
                header_style="bold magenta",
            )
            aliases_table.add_column("Alias", style="cyan")
            aliases_table.add_column("Command", style="green")
            for alias, command in config.aliases.items():
                aliases_table.add_row(alias, command)
            self.console.print(aliases_table)
        else:
            self.console.print("[yellow]No aliases defined.[/yellow]")

    async def clear_all(self):
        try:
            # Limpar cache
            await clear_cache()

            # Limpar histórico
            if os.path.exists("ai_command_history.json"):
                os.remove("ai_command_history.json")

            # Limpar logs
            if os.path.exists("ai_shell.log"):
                os.remove("ai_shell.log")

            # Limpar último prompt usado
            if os.path.exists("last_prompt_used.json"):
                os.remove("last_prompt_used.json")

            self.console.print(
                "[green]All cache, history, logs, and last prompt data have been cleared.[/green]"
            )
        except Exception as e:
            self.console.print(f"[red]Error while clearing data: {str(e)}[/red]")


async def main():
    shell = AIShell()
    await init_cache()
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
