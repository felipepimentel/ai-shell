import asyncio
from typing import List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

from .models import AIShellResult, HistoryEntry
from .utils.logger import class_logger, get_logger

logger = get_logger("ui_handler")


@class_logger
class UIHandler:
    def __init__(self):
        self.console = Console()
        self.prompt_toolkit = None
        self.theme = {
            "header": "blue bold",
            "footer": "green italic",
            "ai_response": "cyan",
            "user_input": "yellow",
            "error": "red bold",
            "success": "green bold",
            "progress": "magenta",
        }

    async def initialize(self):
        self.prompt_toolkit = PromptSession(history=InMemoryHistory())

    def _create_panel(self, content, title, style):
        return Panel(content, title=title, border_style=style, expand=False)

    def display_panel(self, panel):
        self.console.print(panel)

    def format_ai_response(self, response: str) -> Panel:
        syntax = Syntax(response, "bash", theme="monokai", line_numbers=True)
        return self._create_panel(syntax, "AI Response", self.theme["ai_response"])

    def display_ai_response(self, response: str) -> None:
        panel = self.format_ai_response(response)
        self.display_panel(panel)

    async def confirm_execution(self) -> str:
        panel = self._create_panel(
            "Press [Enter] to execute, [e] to edit, or [q] to quit:",
            "Confirm Execution",
            self.theme["ai_response"],
        )
        self.display_panel(panel)
        return await self.prompt_toolkit.prompt_async(
            HTML(
                f"<{self.theme['user_input']}>Your choice: </{self.theme['user_input']}>"
            )
        )

    async def get_choice(self, prompt: str, options: List[str]) -> Optional[str]:
        table = Table(show_header=False, box=None)
        for i, option in enumerate(options, 1):
            table.add_row(f"{i}.", option)
        panel = self._create_panel(
            table, "Correction Choices", self.theme["ai_response"]
        )
        self.display_panel(panel)
        return await self._get_valid_choice(prompt, options)

    async def _get_valid_choice(self, prompt: str, options: List[str]) -> Optional[str]:
        while True:
            choice = await self.prompt_toolkit.prompt_async(
                HTML(
                    f"<{self.theme['user_input']}>{prompt}</{self.theme['user_input']}>"
                )
            )
            if choice.lower() == "q":
                return None
            try:
                choice_index = int(choice) - 1
                if 0 <= choice_index < len(options):
                    return options[choice_index]
            except ValueError:
                pass
            self.console.print(
                "Invalid choice. Please try again.", style=self.theme["error"]
            )

    async def edit_command(self, command: str) -> str:
        self.console.print(
            "Editing mode. Press [Enter] to keep the current line unchanged.",
            style=self.theme["user_input"],
        )
        return await self.prompt_toolkit.prompt_async(
            HTML(
                f"<{self.theme['user_input']}>Edit the command: </{self.theme['user_input']}>"
            ),
            default=command,
        )

    async def edit_multiline(self, text: str) -> str:
        self.console.print(
            "Editing mode. Press [Esc] then [Enter] to finish editing.",
            style=self.theme["user_input"],
        )
        return await self.prompt_toolkit.prompt_async(
            HTML(
                f"<{self.theme['user_input']}>Edit the text:\n</{self.theme['user_input']}>"
            ),
            default=text,
            multiline=True,
        )

    def display_execution_status(self, success: bool) -> None:
        if success:
            self.console.print(
                "✅ Command executed successfully.", style=self.theme["success"]
            )
        else:
            self.console.print("❌ Command failed.", style=self.theme["error"])

    def display_command_output(self, command: str, output: str, success: bool) -> None:
        if success:
            if not output.strip():
                return
            panel = self._create_panel(
                f"{command}\n\n✅ Command executed successfully.",
                "Execution Success",
                self.theme["success"],
            )
        else:
            panel = self._create_panel(
                f"{command}\n\nOutput:\n{output}", "Command Failed", self.theme["error"]
            )
        self.display_panel(panel)

    def display_error_message(self, message: str) -> None:
        panel = self._create_panel(
            f"🚨 {message}", "Error Occurred", self.theme["error"]
        )
        self.display_panel(panel)

    def display_success_message(self, message: str) -> None:
        panel = self._create_panel(
            f"✅ Success: {message}", "Operation Successful", self.theme["success"]
        )
        self.display_panel(panel)

    def display_welcome_message(self) -> None:
        welcome_text = (
            "# Welcome to AI Shell!\n\n"
            "Type your commands or questions, and I'll do my best to help.\n"
            "Type 'exit' to quit, 'help' for more information."
        )
        panel = self._create_panel(
            Markdown(welcome_text), "AI Shell", self.theme["header"]
        )
        self.display_panel(panel)

    def display_help(self) -> None:
        help_items = [
            "Type natural language commands or questions",
            "Use 'exit' to quit the shell",
            "Use 'history' to view command history",
            "Use 'clear history' to clear the command history",
        ]
        help_text = "# AI Shell Help\n\n" + "\n".join(
            f"- {item}" for item in help_items
        )
        panel = self._create_panel(
            Markdown(help_text), "AI Shell Help", self.theme["ai_response"]
        )
        self.display_panel(panel)

    def display_history(self, history: List[HistoryEntry]) -> None:
        table = Table(title="Command History", box=None)
        table.add_column("No.", style="cyan", no_wrap=True)
        table.add_column("Command", style="magenta")
        table.add_column("Status", style="green", justify="center")
        table.add_column("Timestamp", style="yellow", justify="right")

        for i, entry in enumerate(history, 1):
            table.add_row(str(i), entry.command, entry.status, entry.timestamp)

        panel = self._create_panel(table, "History", self.theme["ai_response"])
        self.display_panel(panel)

    def display_farewell_message(self) -> None:
        panel = self._create_panel(
            Markdown("# Thank you for using AI Shell. Goodbye!"),
            "Farewell",
            self.theme["header"],
        )
        self.display_panel(panel)

    async def get_user_input(self, prompt: str) -> str:
        return await self.prompt_toolkit.prompt_async(
            HTML(f"<{self.theme['user_input']}>{prompt}</{self.theme['user_input']}>")
        )

    def display_result(self, result: AIShellResult):
        color = self.theme["success"] if result.success else self.theme["error"]
        panel = self._create_panel(Markdown(result.message), "Result", color)
        self.display_panel(panel)

    async def show_progress(self, message: str):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(message, total=None)
            for _ in range(100):
                progress.update(task, advance=1)
                await asyncio.sleep(0.05)

        logger.info(f"Progress shown: {message}")

    def set_theme(self, new_theme: dict):
        self.theme.update(new_theme)
