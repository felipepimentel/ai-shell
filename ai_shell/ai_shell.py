import asyncio
import signal
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.theme import Theme

from .command import command_processor
from .config import config
from .ui_handler import UIHandler
from .utils.logger import ErrorHandler, get_logger, setup_logging

logger = get_logger("ai_shell.ai_shell")


class AIShell:
    def __init__(self):
        self.console = Console(theme=self._create_theme())
        self.ui_handler = UIHandler(self.console)
        setup_logging(self.console)
        self.logger = get_logger("ai_shell.cli")
        self.error_handler = ErrorHandler(self.console)

        self.processor = command_processor
        signal.signal(signal.SIGINT, self.handle_interrupt_signal)
        self.style = self._create_style()

    def _create_theme(self):
        return Theme(
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

    def _create_style(self):
        return Style.from_dict(
            {
                "prompt": "ansicyan bold",
                "command": "ansigreen",
            }
        )

    def handle_interrupt_signal(self, sig, frame):
        self.console.print("\n[error]Execution interrupted by user (Ctrl + C).[/error]")
        sys.exit(0)

    async def process_command(self, command: str, use_cache: bool = True):
        output = None
        async with self.error_handler.catch_errors():
            ai_response = await self.processor.generate_ai_response(command)
            if ai_response is None:
                self.console.print("[red]Failed to generate AI response.[/red]")
                return None

            simplified_script = self.processor.simplify_script(ai_response)
            self.console.print(
                "[bold cyan]AI generated the following plan:[/bold cyan]"
            )
            self.console.print(self.ui_handler.format_ai_response(simplified_script))

            user_choice = await self.ui_handler.confirm_execution()
            if user_choice == "":
                output = await self.processor.process_command(
                    command,
                    ai_response,
                    simulation_mode=config.simulation_mode,
                    verbose_mode=config.verbose_mode,
                    interactive_mode=True,
                    use_cache=use_cache,
                )
                if output is not None:
                    self.ui_handler.display_command_output(command, output)
                else:
                    self.console.print("[red]Failed to process command.[/red]")
            elif user_choice == "e":
                edited_script = await self.ui_handler.edit_multiline(simplified_script)
                output = await self.processor.execute_script_interactively(
                    edited_script,
                    simulation_mode=config.simulation_mode,
                    verbose_mode=config.verbose_mode,
                )
                self.ui_handler.display_command_output(command, output)
            elif user_choice == "q":
                self.console.print("[yellow]Command execution cancelled.[/yellow]")

        return output

    async def prompt_edit_command(self, ai_response: str) -> str:
        self.console.print(
            "[bold yellow]Expert mode: You can edit the generated script.[/bold yellow]"
        )
        edited = await self.ui_handler.edit_multiline(ai_response)
        return edited

    async def handle_initial_command(self, args):
        if len(args) > 1:
            initial_command = " ".join(args[1:])
            output = await self.process_command(initial_command, use_cache=False)
            self.ui_handler.display_command_output(initial_command, output)
            return True
        return False

    async def handle_user_input(self, session, completer):
        try:
            return await asyncio.wait_for(
                session.prompt_async(
                    HTML('<prompt>AI Shell</prompt> <style fg="ansiyellow">></style> '),
                    completer=completer,
                    style=self.style,
                ),
                timeout=30,
            )
        except asyncio.TimeoutError:
            self.console.print("[yellow]Timeout: No input received.[/yellow]")
            return config.exit_command
        except (EOFError, KeyboardInterrupt):
            return config.exit_command

    async def run_shell(self):
        session = PromptSession(history=FileHistory(config.history_file))

        # Verifique se há argumentos de linha de comando
        if len(sys.argv) > 1:
            await self.handle_initial_command(sys.argv)
            return  # Saia após executar o comando de linha única

        def get_dynamic_completer():
            return WordCompleter(
                list(config.aliases.keys())
                + list(self.processor.history_manager.get_recent_commands(10))
                + [
                    config.exit_command,
                    config.help_command,
                    config.history_command,
                    config.simulate_command,
                    config.clear_cache_command,
                    config.clear_history_command,
                ]
            )

        self.ui_handler.display_welcome_message()

        while True:
            async with self.error_handler.catch_errors():
                prompt_text = await self.handle_user_input(
                    session, get_dynamic_completer()
                )

                if prompt_text.lower() == config.exit_command:
                    break
                elif prompt_text.lower() == config.help_command:
                    self.ui_handler.display_help()
                elif prompt_text.lower() == config.history_command:
                    self.ui_handler.display_history(
                        self.processor.history_manager.history
                    )
                elif prompt_text.lower() == config.simulate_command:
                    config.toggle_simulation_mode()
                    self.ui_handler.display_simulation_mode(config.simulation_mode)
                elif prompt_text.lower() == config.clear_cache_command:
                    await self.processor.cache_manager.clear_cache()
                elif prompt_text.lower() == config.clear_history_command:
                    self.processor.history_manager.clear_history()
                else:
                    await self.process_command(prompt_text)

        await self.processor.cache_manager.clean_expired_cache()
        self.ui_handler.display_farewell_message()
