from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table


class UIHandler:
    def __init__(self, console: Console):
        self.console = console

    def display_command_output(self, command: str, output: str):
        syntax = Syntax(output, "bash", theme="monokai", line_numbers=True)
        panel = Panel(syntax, title="Command Output", border_style="green")
        self.console.print(panel)

    def display_help(self):
        help_table = Table(title="AI Shell Help", box="ROUNDED")
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description", style="green")
        help_table.add_row("exit", "Exit the AI Shell")
        help_table.add_row("help", "Show this help message")
        help_table.add_row("history", "Show command history")
        help_table.add_row("simulate", "Toggle simulation mode")
        help_table.add_row("clear_cache", "Clear cache")
        help_table.add_row("clear_history", "Clear history")

        self.console.print(Panel(help_table, title="Help", border_style="magenta"))

    def display_history(self, history):
        history_table = Table(title="Command History", box="ROUNDED")
        history_table.add_column("Timestamp", style="yellow")
        history_table.add_column("Command", style="cyan")
        history_table.add_column("Output", style="green")
        for entry in history:
            history_table.add_row(entry.timestamp, entry.command, entry.output)

        self.console.print(Panel(history_table, title="History", border_style="blue"))

    def display_welcome_message(self):
        welcome_panel = Panel(
            Markdown("# Welcome to AI Shell\n- Type `help` for assistance."),
            title="Welcome",
            border_style="green",
        )
        self.console.print(welcome_panel)

    def display_farewell_message(self):
        self.console.print(
            Panel(
                "[bold green]Thank you for using AI Shell![/bold green]",
                title="Farewell",
            )
        )

    def display_simulation_mode(self, enabled: bool):
        self.console.print(
            Panel(
                f"[cyan]Simulation mode {'enabled' if enabled else 'disabled'}[/cyan]",
                title="Simulation Mode",
                border_style="cyan",
            )
        )
