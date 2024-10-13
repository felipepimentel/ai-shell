from typing import List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.style import Style as RichStyle
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .models import AIShellResult, HistoryEntry
from .utils.logger import class_logger, get_logger

logger = get_logger("ui_handler")


@class_logger
class UIHandler:
    def __init__(self):
        self.console = Console()
        self.prompt_toolkit = None
        self.theme = {
            "header": RichStyle(color="blue", bold=True),
            "footer": RichStyle(color="green", italic=True),
            "ai_response": RichStyle(color="cyan"),
            "user_input": RichStyle(color="yellow"),
            "error": RichStyle(color="red", bold=True),
            "success": RichStyle(color="green", bold=True),
            "progress": RichStyle(color="magenta"),
            "command": RichStyle(color="bright_yellow"),
            "output": RichStyle(color="bright_white"),
        }
        self.prompt_style = Style.from_dict(
            {
                "prompt": "#ansiyellow",
                "command": "#ansibrightcyan",
            }
        )

    async def initialize(self):
        self.prompt_toolkit = PromptSession(history=InMemoryHistory())

    def _create_panel(self, content, title, style):
        return Panel(content, title=title, border_style=style, expand=False)

    def display_panel(self, panel):
        self.console.print(panel)

    def format_ai_response(self, response: str) -> Panel:
        syntax = Syntax(
            response, "bash", theme="monokai", line_numbers=True, word_wrap=True
        )
        return self._create_panel(syntax, "AI Response", self.theme["ai_response"])

    def display_ai_response(self, response: str) -> None:
        panel = self.format_ai_response(response)
        self.display_panel(panel)

    async def confirm_execution(self) -> str:
        prompt = HTML(
            "<ansigreen>Execute</ansigreen>, <ansiyellow>edit</ansiyellow>, or <ansired>quit</ansired>? [E/e/Q]: "
        )
        return await self.prompt_toolkit.prompt_async(prompt, style=self.prompt_style)

    async def get_choice(self, prompt: str, options: List[str]) -> Optional[str]:
        table = Table(show_header=False, box=None, expand=True)
        for i, option in enumerate(options, 1):
            table.add_row(f"{i}.", Text(option, style=self.theme["command"]))
        panel = self._create_panel(
            table, "Correction Choices", self.theme["ai_response"]
        )
        self.display_panel(panel)
        return await self._get_valid_choice(prompt, options)

    async def _get_valid_choice(self, prompt: str, options: List[str]) -> Optional[str]:
        while True:
            choice = await self.prompt_toolkit.prompt_async(
                HTML(f"<ansiyellow>{prompt}</ansiyellow> "), style=self.prompt_style
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
            HTML("<ansiyellow>Edit the command: </ansiyellow>"),
            default=command,
            style=self.prompt_style,
        )

    def display_command_output(
        self, command: str, output: str, success: bool, execution_time: float
    ) -> None:
        result = Text()
        result.append("Command: ", style=self.theme["command"])
        result.append(command + "\n\n", style=self.theme["user_input"])
        result.append("Output:\n", style=self.theme["output"])
        result.append(output, style=self.theme["ai_response"])
        result.append(
            f"\n\nExecution time: {execution_time:.2f} seconds",
            style=self.theme["footer"],
        )

        status = "✅ Execution Success" if success else "❌ Execution Failed"
        panel = self._create_panel(
            result, status, self.theme["success"] if success else self.theme["error"]
        )
        self.display_panel(panel)

    def display_error_message(self, message: str) -> None:
        self.console.print(f"🚨 Error: {message}", style=self.theme["error"])

    def display_success_message(self, message: str) -> None:
        self.console.print(f"✅ Success: {message}", style=self.theme["success"])

    def display_welcome_message(self) -> None:
        welcome_text = (
            "# Welcome to AI Shell!\n\n"
            "Type your commands or questions, and I'll do my best to help.\n"
            "Type 'exit' to quit, 'help' for more information."
        )
        self.console.print(Markdown(welcome_text), style=self.theme["header"])

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
        self.console.print(Markdown(help_text), style=self.theme["ai_response"])

    def display_history(self, history: List[HistoryEntry]) -> None:
        table = Table(title="Command History", box=None, expand=True)
        table.add_column("No.", style="cyan", no_wrap=True)
        table.add_column("Command", style="magenta")
        table.add_column("Status", style="green", justify="center")
        table.add_column("Timestamp", style="yellow", justify="right")

        for i, entry in enumerate(history, 1):
            table.add_row(
                str(i),
                Text(entry.command, style=self.theme["command"]),
                entry.status,
                entry.timestamp,
            )

        self.console.print(table)

    def display_farewell_message(self) -> None:
        self.console.print(
            Markdown("# Thank you for using AI Shell. Goodbye!"),
            style=self.theme["header"],
        )

    async def get_user_input(self, prompt: str) -> str:
        return await self.prompt_toolkit.prompt_async(
            HTML(f"<ansiyellow>{prompt}</ansiyellow> "), style=self.prompt_style
        )

    def display_result(self, result: AIShellResult):
        color = self.theme["success"] if result.success else self.theme["error"]
        self.console.print(result.message, style=color)

    async def execute_with_progress(self, message: str, coroutine):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task(message, total=None)
            result = await coroutine
            progress.update(task, completed=100)
        return result

    def set_theme(self, new_theme: dict):
        self.theme.update(new_theme)

    def display_thinking(self):
        self.console.print("🤔 Thinking...", style=self.theme["ai_response"])

    def clear_thinking(self):
        # This method is now a no-op, as we don't need to clear anything
        pass
