from typing import Any, Dict, List, Optional, Tuple

from ..datatypes import CommandHistoryEntry
from ..llm.prompts import generate_command_from_prompt
from ..utils.logger import get_logger

logger = get_logger("ai_shell.command_generator")


class CommandGenerator:
    async def generate_command(
        self, command: str, history: List[CommandHistoryEntry], context: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        try:
            ai_response, tokens_used, model_used = await generate_command_from_prompt(
                command, history, context
            )
            if not ai_response:
                logger.error("AI failed to generate a response.")
                return None, None, None
            logger.info(
                f"AI response generated successfully. Tokens used: {tokens_used}, Model: {model_used}"
            )
            return ai_response, tokens_used, model_used
        except Exception as e:
            logger.exception(f"Error generating AI response: {str(e)}")
            return None, None, None
