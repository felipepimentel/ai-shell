import asyncio
import sys
from ai_shell.ai_shell import AIShell
from ai_shell.utils.logger import get_logger, setup_logging

logger = get_logger("ai_shell.cli")

async def main():
    setup_logging()  # Ensure logging is set up
    ai_shell = AIShell()
    await ai_shell.initialize()
    
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        result = await ai_shell.process_command(command)
        if result.success:
            print(result.message)
        else:
            print(f"Error: {result.message}", file=sys.stderr)
    else:
        await ai_shell.run_shell()

if __name__ == "__main__":
    asyncio.run(main())
