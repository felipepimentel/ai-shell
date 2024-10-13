import asyncio
import sys

from .ai_shell import AIShell
from .ui_handler import UIHandler


async def main():
    ui_handler = UIHandler()
    await ui_handler.initialize()
    ai_shell = AIShell(ui_handler)
    await ai_shell.initialize()

    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        result = await ai_shell.process_command(command)
        print(result.message)
    else:
        await ai_shell.run_shell()


if __name__ == "__main__":
    asyncio.run(main())
