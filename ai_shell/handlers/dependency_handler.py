import re
import shutil
from typing import List, Tuple
import subprocess
import sys
import asyncio
import pkg_resources

async def check_dependencies(command: str) -> List[str]:
    # Use a more comprehensive list of dependencies
    all_dependencies = pkg_resources.working_set
    installed_packages = {d.key for d in all_dependencies}
    
    # Extract potential package names from the command
    potential_deps = set(re.findall(r'\b([a-zA-Z0-9_-]+)\b', command))
    
    missing_deps = [dep for dep in potential_deps if dep.lower() not in installed_packages]
    return missing_deps

async def install_dependencies(missing_deps: List[str]) -> Tuple[bool, List[str]]:
    success = True
    failed_deps = []
    for dep in missing_deps:
        if not await install_dependency(dep):
            success = False
            failed_deps.append(dep)
    return success, failed_deps

async def install_dependency(dep: str) -> bool:
    try:
        process = await asyncio.create_subprocess_shell(
            f"{sys.executable} -m pip install {dep}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0
    except Exception:
        return False

async def check_and_install_dependency(dep: str) -> bool:
    if not await asyncio.to_thread(shutil.which, dep):
        return await install_dependency(dep)
    return True

async def resume_command_after_dependency_install(original_command: str):
    process = await asyncio.create_subprocess_shell(
        original_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return process.returncode == 0, stdout, stderr