from rich.console import Console
from rich.syntax import Syntax
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from typing import List, Optional

class UIHandler:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.session = PromptSession()

    def format_ai_response(self, response: str) -> str:
        # Formata a resposta da IA para exibição
        return Syntax(response, "bash", theme="monokai", line_numbers=True)

    def display_ai_response(self, response: str):
        self.console.print(self.format_ai_response(response))

    async def confirm_execution(self) -> str:
        return await self.session.prompt_async(
            HTML('<ansiyellow>Press [Enter] to execute, [e] to edit, or [q] to quit: </ansiyellow>')
        )

    async def get_conflict_resolution_choice(self, conflict: str, options: List[str]) -> Optional[str]:
        self.console.print("[bold yellow]Conflict detected:[/bold yellow]")
        self.console.print(conflict)
        self.console.print("[bold yellow]Please choose a resolution option:[/bold yellow]")
        
        for i, option in enumerate(options, 1):
            self.console.print(f"{i}. {option}")
        
        while True:
            choice = await self.session.prompt_async(
                HTML('<ansiyellow>Enter the number of your choice (or "q" to quit): </ansiyellow>')
            )
            if choice.lower() == 'q':
                return None
            try:
                choice_index = int(choice) - 1
                if 0 <= choice_index < len(options):
                    return options[choice_index]
            except ValueError:
                pass
            self.console.print("[bold red]Invalid choice. Please try again.[/bold red]")

    async def get_error_resolution_choice(self, error_output: str, options: List[str]) -> Optional[str]:
        self.console.print("[bold red]Command execution failed:[/bold red]")
        self.console.print(error_output)
        self.console.print("[bold yellow]Please choose an action:[/bold yellow]")
        
        for i, option in enumerate(options, 1):
            self.console.print(f"{i}. {option}")
        
        while True:
            choice = await self.session.prompt_async(
                HTML('<ansiyellow>Enter the number of your choice (or "q" to quit): </ansiyellow>')
            )
            if choice.lower() == 'q':
                return None
            try:
                choice_index = int(choice) - 1
                if 0 <= choice_index < len(options):
                    return options[choice_index]
            except ValueError:
                pass
            self.console.print("[bold red]Invalid choice. Please try again.[/bold red]")

    async def edit_command(self, command: str) -> str:
        self.console.print("[bold yellow]Editing mode. Press [Enter] to keep the current line unchanged.[/bold yellow]")
        edited_command = await self.session.prompt_async(
            HTML('<ansiyellow>Edit the command: </ansiyellow>'),
            default=command
        )
        return edited_command

    async def edit_multiline(self, text: str) -> str:
        self.console.print("[bold yellow]Editing mode. Press [Esc] then [Enter] to finish editing.[/bold yellow]")
        edited_text = await self.session.prompt_async(
            HTML('<ansiyellow>Edit the text:\n</ansiyellow>'),
            default=text,
            multiline=True
        )
        return edited_text

    def display_command_output(self, command: str, output: str):
        self.console.print(f"[bold green]Command:[/bold green] {command}")
        self.console.print(f"[bold green]Output:[/bold green]\n{output}")

    def display_welcome_message(self):
        self.console.print("[bold blue]Welcome to AI Shell![/bold blue]")
        self.console.print("Type your commands or questions, and I'll do my best to help.")
        self.console.print("Type 'exit' to quit, 'help' for more information.")

    def display_help(self):
        self.console.print("[bold blue]AI Shell Help:[/bold blue]")
        self.console.print("- Type natural language commands or questions")
        self.console.print("- Use 'exit' to quit the shell")
        self.console.print("- Use 'history' to view command history")
        self.console.print("- Use 'simulate' to toggle simulation mode")
        self.console.print("- Use 'clear cache' to clear the command cache")
        self.console.print("- Use 'clear history' to clear the command history")

    def display_history(self, history: List[str]):
        self.console.print("[bold blue]Command History:[/bold blue]")
        for i, command in enumerate(history, 1):
            self.console.print(f"{i}. {command}")

    def display_simulation_mode(self, simulation_mode: bool):
        status = "ON" if simulation_mode else "OFF"
        self.console.print(f"[bold blue]Simulation mode is now {status}[/bold blue]")

    # ... (other methods)
