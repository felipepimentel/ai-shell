import asyncio
import signal
import sys

from .ai_shell import AIShell
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
    ai_shell = await AIShell.create()
    await ai_shell.initialize()

    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        result = await ai_shell.process_command(command)
        if result.success:
            print("Command executed successfully:")
            print(result.message)
        else:
            print(f"Error executing command: {result.message}", file=sys.stderr)

        return
    else:
        await ai_shell.run_shell()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(s, lambda s=s: asyncio.create_task(shutdown(s, loop)))

    loop.set_exception_handler(handle_exception)

    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
        logger.info("Successfully shutdown the AI Shell.")
