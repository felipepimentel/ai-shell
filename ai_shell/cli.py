import asyncio
import sys
import traceback

import structlog
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from rich.console import Console

from .command import CommandProcessor
from .config import config
from .utils.cache import clean_expired_cache, init_cache
from .utils.console import display_help, display_history
from .utils.logger import setup_logging

logger = structlog.get_logger()
console = Console()


class AIShell:
    def __init__(self):
        self.processor = CommandProcessor()
        self.simulation_mode = config.simulation_mode

    async def handle_initial_command(self, args):
        if len(args) > 1:
            initial_command = " ".join(args[1:])
            prompt_text = await self.processor.process_command(
                initial_command, self.simulation_mode
            )
            if prompt_text:
                console.print(f"[cyan]Next step: {prompt_text}[/cyan]")
            return prompt_text
        return None

    async def handle_user_input(self, session, completer):
        try:
            return await session.prompt_async(config.prompt, completer=completer)
        except (EOFError, KeyboardInterrupt):
            return config.exit_command
        except asyncio.TimeoutError:
            console.print("[yellow]Timeout: No input provided.[/yellow]")
            return config.exit_command

    async def run_shell(self):
        await init_cache()
        session = PromptSession(history=FileHistory(config.history_file))
        completer = WordCompleter(
            list(config.aliases.keys())
            + [
                config.exit_command,
                config.help_command,
                config.history_command,
                config.simulate_command,
            ]
        )

        console.print("[bold green]Welcome to AI Shell![/bold green]")
        console.print(
            f"Type '{config.exit_command}' to quit, '{config.help_command}' for assistance, "
            f"'{config.simulate_command}' to toggle simulation mode, or start with your command."
        )

        prompt_text = await self.handle_initial_command(sys.argv)

        while True:
            if not prompt_text:
                prompt_text = await self.handle_user_input(session, completer)

            if prompt_text.lower() == config.exit_command:
                break
            elif prompt_text.lower() == config.help_command:
                await display_help()
            elif prompt_text.lower() == config.history_command:
                await display_history(self.processor.history)
            elif prompt_text.lower() == config.simulate_command:
                self.simulation_mode = not self.simulation_mode
                console.print(
                    f"[cyan]Simulation mode {'enabled' if self.simulation_mode else 'disabled'}[/cyan]"
                )
            else:
                prompt_text = await self.processor.process_command(
                    prompt_text, self.simulation_mode
                )
                continue

            prompt_text = None

        await self.processor.save_history()
        clean_expired_cache()
        console.print("[bold green]Thank you for using AI Shell. Goodbye![/bold green]")


async def main():
    setup_logging()
    shell = AIShell()
    try:
        await shell.run_shell()
    except KeyboardInterrupt:
        console.print("[yellow]Program interrupted by user.[/yellow]")
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb = traceback.extract_tb(exc_traceback)
        filename, line_number, func_name, text = tb[-1]
        error_message = f"[red]Unexpected error in file {filename}, line {line_number}, in {func_name}:[/red]\n[red]{text}[/red]\n[red]{str(e)}[/red]"
        console.print(error_message)
        logger.error("Unexpected error", error=str(e), traceback=traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())
