from __future__ import annotations

import asyncio
import sys

from ai_shell.ai_shell import AIShell

from .utils.logger import get_logger

logger = get_logger("ai_shell.cli")


async def main():
    shell = AIShell()
    if len(sys.argv) > 1:
        await shell.handle_initial_command(sys.argv)
    else:
        await shell.run_shell()


if __name__ == "__main__":
    asyncio.run(main())
