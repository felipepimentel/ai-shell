from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

from ai_shell.utils.logger import get_logger
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
CONFLICT_RESOLUTION_PROMPT = load_prompt("conflict_resolution")

async def generate_command_from_prompt(
    user_command: str,
    context: Dict[str, Any],
) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    try:
        # Aqui você implementaria a lógica para gerar o comando usando um modelo de linguagem
        # Por enquanto, vamos simular uma resposta mais realista
        generated_command = user_command  # Alterado para retornar o comando do usuário
        tokens_used = 10
        model_used = "simulated_model"
        
        return generated_command, tokens_used, model_used
    except Exception as e:
        logger.error(f"Error generating command from prompt: {str(e)}")
        return None, None, None

def sanitize_command(command: str) -> str:
    command = command.strip('`').strip()
    command = command.removeprefix('bash').removeprefix('sh').strip()
    return command

def is_valid_command(command: str) -> bool:
    return bool(command.strip())

async def generate_command(user_command: str, config: Dict[str, Any]) -> str:
    context = {"command_history": [], "enhanced_context": config}
    generated_command, _, _ = await generate_command_from_prompt(user_command, context)
    return generated_command or ""

async def generate_conflict_resolution_options(
    user_command: str,
    error_message: str,
    context: Dict[str, Any]
) -> List[str]:
    prompt = CONFLICT_RESOLUTION_PROMPT.format(
        user_command=user_command,
        conflict_message=error_message,  # Alterado de error_message para conflict_message
        context=context
    )
    
    response, _, _ = await ai.generate_command(prompt)
    
    if response and response.strip():
        options = [option.strip() for option in response.split('\n') if option.strip()]
        return options
    
    logger.error("Failed to generate conflict resolution options")
    return []