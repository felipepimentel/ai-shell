import argparse
import asyncio
import signal
import sys

from ai_shell.ai_shell import AIShell
from ai_shell.config import config

from .utils.logger import get_logger, setup_logging

logger = get_logger("ai_shell.cli")

ai_shell = None


async def shutdown(signal, loop):
    global ai_shell
    logger.info(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    [task.cancel() for task in tasks]

    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)

    if ai_shell:
        await ai_shell.cleanup()

    loop.stop()


def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logger.error(f"Caught exception: {msg}")
    logger.info("Shutting down...")
    asyncio.create_task(shutdown(signal.SIGINT, loop))


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
        try:
            result = await ai_shell.process_command(command)
            if result.success:
                print("Command executed successfully:")
                print(result.message)
            else:
                print(f"Error executing command: {result.message}", file=sys.stderr)
        except asyncio.CancelledError:
            logger.info("Command execution cancelled")
    else:
        try:
            await ai_shell.run_shell()
        except asyncio.CancelledError:
            logger.info("AI Shell execution cancelled")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(s, lambda s=s: asyncio.create_task(shutdown(s, loop)))

    loop.set_exception_handler(handle_exception)

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(shutdown(signal.SIGINT, loop))
        loop.close()
        logger.info("Successfully shutdown the AI Shell.")
