import argparse
import asyncio
import signal
import sys
from typing import Optional

from ai_shell.ai_shell import AIShell
from ai_shell.config import config

from .utils.logger import get_logger, setup_logging

logger = get_logger("ai_shell.cli")

ai_shell: Optional[AIShell] = None

def force_exit(signum, frame):
    logger.info("Forced exit requested. Exiting immediately.")
    sys.exit(0)

async def main():
    global ai_shell
    setup_logging()

    parser = argparse.ArgumentParser(description="AI Shell")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose mode")
    parser.add_argument("--expert", action="store_true", help="Enable expert mode")
    parser.add_argument("command", nargs="*", help="Command to execute")
    args = parser.parse_args()

    if args.config:
        config._config = config._load_config(args.config)
    if args.verbose:
        config.verbose_mode = True
    if args.expert:
        config.expert_mode = True

    ai_shell = await AIShell.create()
    await ai_shell.initialize()

    if args.command:
        command = " ".join(args.command)
        result = await ai_shell.process_command(command)
        if result.success:
            print("Command executed successfully:")
            print(result.message)
        else:
            print(f"Error executing command: {result.message}", file=sys.stderr)
    else:
        await ai_shell.run_shell()

if __name__ == "__main__":
    # Configurar o manipulador de sinal para saída forçada
    signal.signal(signal.SIGINT, force_exit)
    signal.signal(signal.SIGTERM, force_exit)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Exiting.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        logger.info("AI Shell has been terminated.")
