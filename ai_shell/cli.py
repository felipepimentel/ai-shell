import asyncio
import signal
import sys

from .ai_shell import AIShell
from .ui_handler import UIHandler


async def main():
    ui_handler = UIHandler()
    await ui_handler.initialize()
    ai_shell = AIShell(ui_handler)
    await ai_shell.initialize()

    def signal_handler(sig, frame):
        print("\nGracefully shutting down...")
        asyncio.get_event_loop().stop()

    signal.signal(signal.SIGINT, signal_handler)

    try:
        if len(sys.argv) > 1:
            command = " ".join(sys.argv[1:])
            result = await ai_shell.process_command(command)
            print(result.message)
        else:
            await ai_shell.run_shell()
    except KeyboardInterrupt:
        print("\nGracefully shutting down...")
    finally:
        ui_handler.display_farewell_message()


if __name__ == "__main__":
    asyncio.run(main())
