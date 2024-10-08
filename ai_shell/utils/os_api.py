import os
import platform
import pwd
import asyncio

async def get_system_info():
    try:
        user = os.getlogin()
    except OSError:
        user = pwd.getpwuid(os.getuid())[0]

    # Simulando uma operação assíncrona
    await asyncio.sleep(0)

    return {
        "os": platform.system(),
        "os_version": platform.release(),
        "user": user,
        "current_directory": os.getcwd(),
        "shell": os.getenv("SHELL", "unknown"),
        "python_version": platform.python_version(),
    }
