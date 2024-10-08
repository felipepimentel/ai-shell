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
from .utils.cache import clean_expired_cache, clear_cache, init_cache
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
            output = await self.processor.process_command(
                initial_command, self.simulation_mode
            )
            if output:
                console.print(f"[cyan]{output}[/cyan]")
            return True  # Retorna True para indicar que um comando inicial foi processado
        return False

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
                config.clear_cache_command,
                config.clear_history_command,
            ]
        )

        console.print("[bold green]Welcome to AI Shell![/bold green]")
        console.print(
            f"Type '{config.exit_command}' to quit, '{config.help_command}' for assistance, "
            f"'{config.simulate_command}' to toggle simulation mode, or start with your command."
        )

        initial_command_processed = await self.handle_initial_command(sys.argv)
        if initial_command_processed:
            return  # Encerra o programa após processar o comando inicial

        while True:
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
            elif prompt_text.lower() == config.clear_cache_command:
                await clear_cache()
                console.print("[green]Cache cleared successfully.[/green]")
            elif prompt_text.lower() == config.clear_history_command:
                self.processor.clear_history()
                console.print("[green]Command history cleared successfully.[/green]")
            else:
                output = await self.processor.process_command(
                    prompt_text, self.simulation_mode
                )
                if output:
                    console.print(f"[cyan]{output}[/cyan]")

        await self.processor.save_history()
        await clean_expired_cache()  # Modificado para ser assíncrono
        console.print("[bold green]Thank you for using AI Shell. Goodbye![/bold green]")

# ... (rest of the code remains the same)


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
