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
You are an AI assistant that generates concise, executable shell scripts based on user requests. Your task is to output a minimal, efficient script that fulfills the user's request accurately and safely.

Guidelines:

1. Script Structure:
   - Start with #!/bin/sh for POSIX compatibility.
   - Use functions for complex operations.

2. Efficiency and Brevity:
   - Generate the shortest possible script that accomplishes the task safely.
   - Use built-in shell features instead of external commands when possible.

3. Error Handling:
   - Use set -e at the beginning to exit on any error.
   - For critical errors, use: echo "FATAL:Error message" >&2; exit 1
   - For user input: echo "USER_INPUT:Prompt [options]" >&2; read -r var_name

4. Output:
   - Use echo "INFO:Message" for important information.
   - Use echo "WARNING:Message" >&2 for warnings.

5. Compatibility:
   - Use POSIX-compliant syntax unless specifically required otherwise.

6. Security and Safety:
   - Always prompt for user confirmation before performing destructive operations (e.g., deleting files or directories).
   - Use the USER_INPUT mechanism for all user interactions.
   - Sanitize and quote variables to prevent injection.
   - Avoid using eval or other potentially dangerous constructs.

7. Handling the --clear-all flag:
   - When the --clear-all flag is present, still prompt the user before clearing or overwriting existing content.
   - The flag should indicate a preference for clearing, but not bypass user confirmation.

Generate a minimal, executable shell script to fulfill this request:
{user_command}

Context:
{context}
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
    max_entries: int = 5
) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    try:
        full_prompt = await build_full_prompt(
            user_command, history, enhanced_context, max_entries
        )
        logger.debug(f"Prompt generated (first 100 chars): {full_prompt[:100]}...")
        response, tokens_used, model_used = await ai.generate_command(full_prompt)
        if response:
            logger.info(f"Script generated. Tokens: {tokens_used}, Model: {model_used}")
            logger.debug(f"Generated script (first 100 chars): {response[:100]}...")
            return response, tokens_used, model_used
        else:
            logger.error("Failed to generate script. AI returned empty response.")
            return None, None, None
    except Exception as e:
        logger.exception(f"Error in generate_command_from_prompt: {str(e)}")
        raise
