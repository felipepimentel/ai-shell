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
        self._display_options(options)
        return await self._get_valid_choice(prompt, options)

    def _display_options(self, options: List[str]) -> None:
        table = Table(show_header=False, box=None)
        for i, option in enumerate(options, 1):
            table.add_row(f"{i}.", option)
        self.console.print(table)

    async def _get_valid_choice(self, prompt: str, options: List[str]) -> Optional[str]:
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
        self._display_panel(conflict, "Conflict detected", "yellow")
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
        self._display_panel(error_output, "Command execution failed", "red")
        self.console.print("[bold yellow]Please choose an action:[/bold yellow]")
        return await self.get_choice(
            '<ansiyellow>Enter the number of your choice (or "q" to quit): </ansiyellow>',
            options,
        )

    def _display_panel(self, content: str, title: str, color: str) -> None:
        self.console.print(
            Panel(
                content,
                title=f"[bold {color}]{title}[/bold {color}]",
                border_style=color,
            )
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
        self._display_panel(f"{command}\n\n{output}", "Command Output", "green")

    def display_welcome_message(self) -> None:
        welcome_text = (
            "Type your commands or questions, and I'll do my best to help.\n"
            "Type 'exit' to quit, 'help' for more information."
        )
        self._display_panel(welcome_text, "Welcome to AI Shell!", "blue")

    def display_help(self) -> None:
        help_items = [
            "Type natural language commands or questions",
            "Use 'exit' to quit the shell",
            "Use 'history' to view command history",
            "Use 'clear cache' to clear the command cache",
            "Use 'clear history' to clear the command history",
        ]
        self._display_table("AI Shell Help", help_items, bullet_point=True)

    def display_history(self, history: List[str]) -> None:
        self._display_table(
            "Command History",
            history,
            numbered=True,
            columns=["No.", "Command"],
            styles=["cyan", "magenta"],
        )

    def _display_table(
        self,
        title: str,
        items: List[str],
        bullet_point: bool = False,
        numbered: bool = False,
        columns: Optional[List[str]] = None,
        styles: Optional[List[str]] = None,
    ) -> None:
        table = Table(
            title=f"[bold blue]{title}[/bold blue]", box=None, show_header=bool(columns)
        )

        if columns:
            for col, style in zip(columns, styles or []):
                table.add_column(col, style=style, no_wrap=True)

        for i, item in enumerate(items, 1):
            if bullet_point:
                table.add_row(f"• {item}")
            elif numbered:
                table.add_row(str(i), item)
            else:
                table.add_row(item)

        self.console.print(table)

    def display_farewell_message(self) -> None:
        self._display_panel(
            "Thank you for using AI Shell. Goodbye!", "Farewell", "blue"
        )
