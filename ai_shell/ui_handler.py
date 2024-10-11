from typing import List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table


class UIHandler:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.session = PromptSession()

    def format_ai_response(self, response: str) -> Panel:
        syntax = Syntax(response, "bash", theme="monokai", line_numbers=True)
        return Panel(syntax, title="AI Response", border_style="blue")

    def display_ai_response(self, response: str) -> None:
        self.console.print(self.format_ai_response(response))

    async def confirm_execution(self) -> str:
        return await self.session.prompt_async(
            HTML(
                "<ansiyellow>Press [Enter] to execute, [e] to edit, or [q] to quit: </ansiyellow>"
            )
        )

    async def get_choice(self, prompt: str, options: List[str]) -> Optional[str]:
        table = Table(show_header=False, box=None)
        for i, option in enumerate(options, 1):
            table.add_row(f"{i}.", option)
        self.console.print(table)

        while True:
            choice = await self.session.prompt_async(HTML(prompt))
            if choice.lower() == "q":
                return None
            try:
                choice_index = int(choice) - 1
                if 0 <= choice_index < len(options):
                    return options[choice_index]
            except ValueError:
                pass
            self.console.print("[bold red]Invalid choice. Please try again.[/bold red]")

    async def get_conflict_resolution_choice(
        self, conflict: str, options: List[str]
    ) -> Optional[str]:
        self.console.print(
            Panel(
                conflict,
                title="[bold yellow]Conflict detected[/bold yellow]",
                border_style="yellow",
            )
        )
        self.console.print(
            "[bold yellow]Please choose a resolution option:[/bold yellow]"
        )
        return await self.get_choice(
            '<ansiyellow>Enter the number of your choice (or "q" to quit): </ansiyellow>',
            options,
        )

    async def get_error_resolution_choice(
        self, error_output: str, options: List[str]
    ) -> Optional[str]:
        self.console.print(
            Panel(
                error_output,
                title="[bold red]Command execution failed[/bold red]",
                border_style="red",
            )
        )
        self.console.print("[bold yellow]Please choose an action:[/bold yellow]")
        return await self.get_choice(
            '<ansiyellow>Enter the number of your choice (or "q" to quit): </ansiyellow>',
            options,
        )

    async def edit_command(self, command: str) -> str:
        self.console.print(
            "[bold yellow]Editing mode. Press [Enter] to keep the current line unchanged.[/bold yellow]"
        )
        return await self.session.prompt_async(
            HTML("<ansiyellow>Edit the command: </ansiyellow>"), default=command
        )

    async def edit_multiline(self, text: str) -> str:
        self.console.print(
            "[bold yellow]Editing mode. Press [Esc] then [Enter] to finish editing.[/bold yellow]"
        )
        return await self.session.prompt_async(
            HTML("<ansiyellow>Edit the text:\n</ansiyellow>"),
            default=text,
            multiline=True,
        )

    def display_command_output(self, command: str, output: str) -> None:
        self.console.print(
            Panel(
                f"{command}\n\n{output}",
                title="[bold green]Command Output[/bold green]",
                border_style="green",
            )
        )

    def display_welcome_message(self) -> None:
        welcome_panel = Panel(
            "Type your commands or questions, and I'll do my best to help.\n"
            "Type 'exit' to quit, 'help' for more information.",
            title="[bold blue]Welcome to AI Shell![/bold blue]",
            border_style="blue",
        )
        self.console.print(welcome_panel)

    def display_help(self) -> None:
        help_items = [
            "Type natural language commands or questions",
            "Use 'exit' to quit the shell",
            "Use 'history' to view command history",
            "Use 'simulate' to toggle simulation mode",
            "Use 'clear cache' to clear the command cache",
            "Use 'clear history' to clear the command history",
        ]
        help_table = Table(
            title="[bold blue]AI Shell Help[/bold blue]", box=None, show_header=False
        )
        for item in help_items:
            help_table.add_row(f"• {item}")
        self.console.print(help_table)

    def display_history(self, history: List[str]) -> None:
        history_table = Table(title="[bold blue]Command History[/bold blue]", box=None)
        history_table.add_column("No.", style="cyan", no_wrap=True)
        history_table.add_column("Command", style="magenta")
        for i, command in enumerate(history, 1):
            history_table.add_row(str(i), command)
        self.console.print(history_table)

    def display_simulation_mode(self, simulation_mode: bool) -> None:
        status = "ON" if simulation_mode else "OFF"
        self.console.print(
            Panel(
                f"Simulation mode is now {status}",
                title="[bold blue]Simulation Mode[/bold blue]",
                border_style="blue",
            )
        )

    def display_farewell_message(self) -> None:
        self.console.print(
            Panel(
                "Thank you for using AI Shell. Goodbye!",
                title="[bold blue]Farewell[/bold blue]",
                border_style="blue",
            )
        )
