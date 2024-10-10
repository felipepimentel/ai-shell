from rich.console import Console
from rich.syntax import Syntax
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML

class UIHandler:
    def __init__(self, console: Console):
        self.console = console

    def display_command_output(self, command: str, output: str):
        self.console.print(output)

    def format_ai_response(self, response: str) -> str:
        return Syntax(response, "bash", theme="monokai")

    async def confirm_execution(self) -> str:
        session = PromptSession()
        response = await session.prompt_async(
            HTML('<ansiyellow>Press [Enter] to execute, [e] to edit, or [q] to quit: </ansiyellow>')
        )
        return response.lower()

    async def edit_multiline(self, text: str) -> str:
        self.console.print("[bold yellow]Editing mode. Press [Ctrl+D] or [Ctrl+Z] on empty line to finish.[/bold yellow]")
        session = PromptSession()
        lines = text.split('\n')
        edited_lines = []
        for i, line in enumerate(lines):
            edited_line = await session.prompt_async(
                f"{i + 1}: ",
                default=line
            )
            edited_lines.append(edited_line)
        return '\n'.join(edited_lines)

    async def get_user_input(self, prompt: str) -> str:
        session = PromptSession()
        response = await session.prompt_async(
            HTML(f'<ansiyellow>{prompt} </ansiyellow>')
        )
        return response.lower()

    # ... (mantenha os outros métodos existentes)
