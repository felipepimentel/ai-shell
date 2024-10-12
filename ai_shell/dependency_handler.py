import asyncio
import re
import shutil
import sys
from typing import List, Tuple

import pkg_resources

from .utils.logger import get_logger
from .utils.system_utils import run_process, check_system_dependency

logger = get_logger(__name__)


async def check_dependencies(command: str) -> List[str]:
    """
    Check for missing dependencies based on the command.
    """
    all_dependencies = pkg_resources.working_set
    installed_packages = {d.key for d in all_dependencies}

    potential_deps = set(re.findall(r"\b([a-zA-Z0-9_-]+)\b", command))
    missing_deps = [
        dep for dep in potential_deps if dep.lower() not in installed_packages
    ]
    return missing_deps


async def check_and_install_dependencies(
    command: str, non_interactive: bool
) -> Tuple[bool, List[str]]:
    """
    Check if required dependencies are installed and install them if necessary.
    """
    missing_deps = await check_dependencies(command)
    if not missing_deps:
        return True, []

    if non_interactive:
        return await install_dependencies(missing_deps)

    to_install = []
    for dep in missing_deps:
        if confirm_installation(dep):
            to_install.append(dep)

    if to_install:
        return await install_dependencies(to_install)

    return False, missing_deps


async def install_dependencies(missing_deps: List[str]) -> Tuple[bool, List[str]]:
    """
    Attempt to install all missing dependencies.
    """
    success = True
    failed_deps = []
    for dep in missing_deps:
        if not await install_dependency(dep):
            success = False
            failed_deps.append(dep)
    return success, failed_deps


async def install_dependency(dep: str) -> bool:
    """
    Install a single dependency using pip.
    """
    try:
        returncode, stdout, stderr = await run_process(f"{sys.executable} -m pip install {dep}")
        if returncode == 0:
            logger.info(f"Successfully installed {dep}")
            return True
        else:
            logger.error(f"Failed to install {dep}. Error: {stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"Error while installing {dep}: {str(e)}")
        return False


def confirm_installation(dependency: str) -> bool:
    """
    Ask user for confirmation to install a dependency.
    """
    response = input(
        f"The dependency '{dependency}' is required. Do you want to install it? (y/n): "
    )
    return response.lower() == "y"


async def resume_command_after_dependency_install(original_command: str) -> Tuple[bool, str, str]:
    """
    Resume the original command after dependency installation.
    """
    returncode, stdout, stderr = await run_process(original_command)
    return returncode == 0, stdout, stderr


# Additional utility functions can be added here as needed
