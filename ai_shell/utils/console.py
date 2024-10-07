from collections import deque
from typing import TYPE_CHECKING

import structlog
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from ..command import CommandHistoryEntry

logger = structlog.get_logger()


console = Console()

MAX_HISTORY = 100
history_deque = deque(maxlen=MAX_HISTORY)


def display_help():
    help_table = Table(title="AI Shell Help", box="ROUNDED")
    help_table.add_column("Command", style="cyan", justify="left")
    help_table.add_column("Description", style="magenta", justify="left")
    help_table.add_row("exit", "Exit the AI Shell")
    help_table.add_row("help", "Display this help message")
    help_table.add_row("history", "Show command history")
    help_table.add_row("simulate", "Toggle simulation mode")
    help_table.add_row("<any text>", "Ask AI to generate and execute a command")

    console.print(help_table)


def display_history(history: list["CommandHistoryEntry"]):
    history_table = Table(title="Command History", box="ROUNDED")
    history_table.add_column("Timestamp", style="yellow")
    history_table.add_column("Working Directory", style="blue")
    history_table.add_column("Command", style="cyan")
    history_table.add_column("Output", style="green")

    for entry in list(history)[-10:]:  # Mostra as últimas 10 entradas
        history_table.add_row(
            entry.timestamp,
            entry.working_directory,
            entry.command,
            entry.output[:50] + "..." if len(entry.output) > 50 else entry.output,
        )

    console.print(history_table)


def print_verbose_message(message: str):
    console.print(f"[blue][VERBOSE] {message}[/blue]")


def print_error_message(message: str):
    console.print(f"[red][ERROR] {message}[/red]")


def print_success_message(message: str):
    console.print(f"[green][SUCCESS] {message}[/green]")
