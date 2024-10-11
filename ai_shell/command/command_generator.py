from typing import Any, Dict, Optional, Tuple

from ..llm.prompts import generate_command_from_prompt
from ..utils.logger import get_logger

logger = get_logger("ai_shell.command_generator")

class CommandGenerator:
    async def generate_command(
        self, user_command: str, context: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        return await generate_command_from_prompt(user_command, context)
