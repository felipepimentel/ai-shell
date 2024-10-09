from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

from ai_shell.utils.logger import get_logger

from ..models import CommandHistoryEntry
from ..utils.os_api import get_system_info
from .openrouter_ai import OpenRouterAI

logger = get_logger("ai_shell.llm.prompts")

ai = OpenRouterAI()

COMMAND_GENERATION_PROMPT = """
You are an AI assistant integrated into a system that generates and executes shell commands based on user requests. 
Your task is to output a complete, executable shell script that accurately fulfills the user's request, considering potential issues and providing appropriate checks and error handling.

Guidelines:

1. Script Completeness:
   - Ensure that the script is complete and properly formatted.
   - All opening brackets, parentheses, and quotes must have corresponding closing ones.
   - All functions, if statements, case statements, and loops must be properly closed.
   - The script must have a clear beginning and end.
   - Do not include any markdown formatting, code block delimiters (```), or explanatory comments at the beginning of the script.

2. Safety and Precautions:
   - Include checks for existing files/directories before operations that might overwrite or conflict.
   - Use conditional statements to handle potential errors and unexpected situations.
   - Avoid commands that could lead to data loss or system instability.
   - Always check for necessary permissions before executing privileged operations.
   - Validate and sanitize user inputs to prevent injection attacks.

3. Script Structure:
   - Start the script with #!/bin/sh (for POSIX compatibility) or #!/bin/bash if bash-specific features are required.
   - Ensure all conditional statements (if, elif, else) are properly closed with 'fi'.
   - Ensure all case statements are properly closed with 'esac'.
   - Use functions for complex operations to improve readability and reusability.
   - Make sure all functions are properly closed.

4. Cross-Platform Compatibility:
   - Use commands and syntax compatible with POSIX shell (sh) for maximum compatibility.
   - When OS-specific features are needed, include checks and alternatives for different systems (Linux, macOS, Windows).

5. Error Handling:
   - Implement comprehensive error handling with informative error messages.
   - Use exit codes to indicate different types of errors.
   - Consider using 'set -e' at the beginning of the script to exit on any error.

6. User Interaction:
   - For user input, use the 'read' command with clear and informative prompts.
   - Provide options to skip or cancel operations that might be destructive.

7. Output and Logging:
   - Use echo statements to keep the user informed about the script's progress.
   - Consider implementing a simple logging mechanism for complex operations.

8. Error Classification and User Interaction:
   - Classify potential errors or situations that require user input into the following categories:
     a) FATAL: Errors that prevent the operation from continuing and require immediate termination.
     b) USER_INPUT: Situations where user input is required to proceed.
     c) WARNING: Non-critical issues that the user should be aware of but don't necessarily prevent execution.
     d) INFO: Informational messages about the script's progress.
   - For USER_INPUT situations, provide clear options for the user, always including 'skip' and 'cancel' as possible choices.
   - Use the following format for error classification and user interaction:
     echo "ERROR_TYPE:MESSAGE" >&2
     For example:
     echo "USER_INPUT:The directory already exists. What would you like to do? [overwrite/skip/cancel]" >&2

9. Script Output:
   - Ensure all important information, warnings, and errors are output to stderr using >&2.
   - Use echo statements to keep the user informed about the script's progress.

Please provide your response as a complete, executable shell script, starting directly with #!/bin/sh or #!/bin/bash. Do not include any markdown formatting, code block delimiters, or explanatory comments at the beginning of the script.

{context}

User's current request: '{user_command}'

Generate a complete, executable shell script to fulfill this request, following the guidelines above:
"""


async def build_contextual_prompt(
    history: List[CommandHistoryEntry],
    max_entries: int = 10,
    enhanced_context: Dict = None,
) -> str:
    """
    Creates a rich contextual prompt based on command history, system information, and enhanced context.
    """
    structured_prompt = "Recent command history:\n"
    for entry in history[-max_entries:]:
        structured_prompt += (
            f"Command: {entry.command}\n"
            f"Output: {entry.output}\n"
            f"Timestamp: {entry.timestamp}\n"
            f"Working Directory: {entry.working_directory}\n\n"
        )

    system_info = await get_system_info()
    structured_prompt += f"\nSystem Info:\n{system_info}\n"

    if enhanced_context:
        structured_prompt += "\nAdditional Context:\n"
        structured_prompt += (
            f"Current Directory: {enhanced_context.get('current_directory', 'N/A')}\n"
        )
        structured_prompt += "Environment Variables:\n"
        for key, value in enhanced_context.get("environment_variables", {}).items():
            structured_prompt += f"  {key}={value}\n"
        structured_prompt += "Recent Commands:\n"
        for cmd in enhanced_context.get("recent_commands", []):
            structured_prompt += f"  {cmd}\n"
        structured_prompt += "User Preferences:\n"
        for key, value in enhanced_context.get("user_preferences", {}).items():
            structured_prompt += f"  {key}: {value}\n"

    return structured_prompt


async def build_full_prompt(
    user_command: str,
    history: List[CommandHistoryEntry],
    enhanced_context: Dict = None,
    max_entries: int = 10,
) -> str:
    """
    Builds the complete prompt with rich context, user command, and system information.
    """
    contextual_prompt = await build_contextual_prompt(
        history, max_entries, enhanced_context
    )
    full_prompt = COMMAND_GENERATION_PROMPT.format(
        context=contextual_prompt, user_command=user_command
    )

    # Save the full prompt to a file for auditing
    with open("last_prompt_used.json", "w") as f:
        json.dump(
            {
                "user_command": user_command,
                "context": contextual_prompt,
                "full_prompt": full_prompt,
            },
            f,
            indent=2,
        )

    return full_prompt


async def generate_command_from_prompt(
    user_command: str,
    history: List[CommandHistoryEntry],
    enhanced_context: Dict = None,
    max_entries: int = 10,
) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    try:
        full_prompt = await build_full_prompt(
            user_command, history, enhanced_context, max_entries
        )
        logger.debug(f"Full prompt generated: {full_prompt[:100]}...")  # Log the first 100 characters of the prompt
        response, tokens_used, model_used = await ai.generate_command(full_prompt)
        if response:
            logger.info(
                f"Commands generated successfully. Tokens used: {tokens_used}, Model: {model_used}"
            )
            logger.debug(f"Generated response: {response[:100]}...")  # Log the first 100 characters of the response
            return response, tokens_used, model_used
        else:
            logger.error("Failed to generate commands. AI returned empty response.")
            return None, None, None
    except Exception as e:
        logger.exception(f"Error in generate_command_from_prompt: {str(e)}")
        raise
