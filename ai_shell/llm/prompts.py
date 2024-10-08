from typing import List
from ..utils.os_api import get_system_info
from .openrouter_ai import OpenRouterAI
from ai_shell.utils.logger import get_logger
from ..command import CommandHistoryEntry

logger = get_logger("ai_shell.llm.prompts")

ai = OpenRouterAI()

async def build_contextual_prompt(
    history: List[CommandHistoryEntry], max_entries: int = 10
) -> str:
    """
    Creates a contextual prompt based on command history and operating system.
    """
    structured_prompt = "Here is what has been done so far:\n"
    for entry in history[-max_entries:]:
        structured_prompt += (
            f"Command: {entry.command}\n"
            f"Output: {entry.output}\n"
            f"Timestamp: {entry.timestamp}\n"
            f"Working Directory: {entry.working_directory}\n\n"
        )

    system_info = await get_system_info()  # Get system information asynchronously
    structured_prompt += f"\nSystem Info: {system_info}\n"

    return structured_prompt


async def build_full_prompt(
    user_command: str, history: List[CommandHistoryEntry], max_entries: int = 10
) -> str:
    """
    Builds the complete prompt with concise history, user command, and system context.
    Incorporates safety, compatibility, efficiency, and accuracy guidelines for command generation.
    """
    contextual_prompt = await build_contextual_prompt(history, max_entries)

    prompt = (
        "You are an AI assistant integrated into a system that generates and executes shell commands based on user requests. "
        "Your task is to output only the command that accurately fulfills the user's request. "
        "The command must adhere to the following guidelines:\n\n"
        "Safety:\n"
        "- Ensure the command is safe to execute and does not harm the system, compromise security, or result in data loss.\n"
        "- Avoid commands that delete, modify, or expose sensitive data unless explicitly requested in a safe and precise manner.\n"
        "- Do not include dangerous operations or commands that require confirmation.\n\n"
        "Compatibility:\n"
        "- The command should be compatible with common shells (sh, bash, zsh, fish, PowerShell, cmd).\n"
        "- Ensure functionality across different operating systems (Linux, macOS, Windows).\n\n"
        "Efficiency:\n"
        "- Use best practices for command syntax and options.\n"
        "- Optimize for performance and resource usage.\n"
        "- Utilize appropriate flags and parameters for clarity and effectiveness.\n\n"
        "Accuracy:\n"
        "- Precisely address the user's request without adding or omitting functionality.\n"
        "- Do not include unnecessary components or superfluous options.\n\n"
        "Instructions:\n"
        "- Output only the command, without any additional text, explanations, warnings, or formatting.\n"
        "- Do not communicate with the user or ask for clarifications.\n"
        "- If the user's request is ambiguous, unsafe, or cannot be fulfilled while adhering to these guidelines, output nothing.\n"
        "- Do not include prompts for user input or confirmation unless explicitly required by the request.\n"
        "- Ensure the command complies with all ethical guidelines and does not include disallowed content.\n"
        "- Use appropriate methods for privilege escalation (e.g., sudo) only if explicitly specified in the user's request.\n\n"
        f"{contextual_prompt}\n"
        f"User's current request: '{user_command}'\n"
    )
    return prompt


async def generate_command_from_prompt(
    user_command: str, history: List[CommandHistoryEntry], max_entries: int = 10
) -> str:
    try:
        full_prompt = await build_full_prompt(user_command, history, max_entries)
        response = await ai.generate_command(full_prompt)
        if response:
            logger.info("Command generated successfully")
            return response
        else:
            logger.warning("Failed to generate command")
            return None
    except Exception as e:
        logger.error(f"Error in generate_command_from_prompt: {str(e)}")
        return None
