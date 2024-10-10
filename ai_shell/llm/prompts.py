from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ai_shell.utils.cache import check_cache, save_cache
from ai_shell.utils.logger import get_logger

from ..datatypes import CommandHistoryEntry
from ..utils.os_api import get_system_info
from .openrouter_ai import OpenRouterAI

logger = get_logger("ai_shell.llm.prompts")

ai = OpenRouterAI()

PROMPTS_DIR = Path(__file__).parent.parent.parent / "assets" / "prompts"
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)


def load_prompt(prompt_name: str) -> str:
    prompt_file = PROMPTS_DIR / f"{prompt_name}.md"
    if prompt_file.exists():
        return prompt_file.read_text()
    else:
        logger.warning(f"Prompt file {prompt_file} not found. Using default prompt.")
        return ""


COMMAND_GENERATION_PROMPT = load_prompt("command_generation")


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
    structured_prompt += f"\nSystem Info:\n{json.dumps(system_info, indent=2)}\n"

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
    prompt_name: str = "command_generation",
) -> str:
    """
    Builds the complete prompt with rich context, user command, and system information.
    """
    contextual_prompt = await build_contextual_prompt(
        history, max_entries, enhanced_context
    )
    main_prompt = load_prompt(prompt_name)
    full_prompt = main_prompt.format(
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
    max_entries: int = 5,
    prompt_name: str = "command_generation",
) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    try:
        # Check cache first
        cached_command, cached_output = await check_cache(user_command)
        if cached_command and cached_output:
            logger.info("Using cached command and output")
            return cached_command, None, "cached"

        full_prompt = await build_full_prompt(
            user_command, history, enhanced_context, max_entries, prompt_name
        )
        logger.debug(f"Full prompt generated (first 100 chars): {full_prompt[:100]}...")
        logger.info("Sending prompt to AI for command generation")
        response, tokens_used, model_used = await ai.generate_command(full_prompt)
        if response and response.strip():
            logger.info(
                f"Script generated successfully. Tokens: {tokens_used}, Model: {model_used}"
            )
            logger.debug(f"Generated script (first 100 chars): {response[:100]}...")
            # Save to cache
            await save_cache(user_command, response, "")
            return response, tokens_used, model_used
        else:
            logger.error(
                "Failed to generate script. AI returned empty or invalid response."
            )
            return None, None, None
    except Exception as e:
        logger.exception(f"Error in generate_command_from_prompt: {str(e)}")
        raise
