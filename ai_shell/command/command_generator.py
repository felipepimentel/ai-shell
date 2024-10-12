from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..llm.openrouter_ai import OpenRouterAI
from ..utils.logger import class_logger, get_logger

logger = get_logger(__name__)


class CommandGenerationError(Exception):
    pass


@class_logger
class CommandGenerator:
    PROMPTS_DIR = Path(__file__).parent.parent.parent / "assets" / "prompts"
    COMMAND_GENERATION_PROMPT = "command_generation"
    CONFLICT_RESOLUTION_PROMPT = "conflict_resolution"

    def __init__(self):
        self.ai = OpenRouterAI()
        self.command_generation_prompt = self._load_prompt(
            self.COMMAND_GENERATION_PROMPT
        )
        self.conflict_resolution_prompt = self._load_prompt(
            self.CONFLICT_RESOLUTION_PROMPT
        )

    async def generate_command(
        self, prompt: str, context: dict
    ) -> Tuple[str, int, str]:
        try:
            generated_command = await self.ai.generate(prompt)
            tokens_used = len(generated_command.split())  # Simple estimation
            model_name = self.ai.get_model_name()
            return generated_command, tokens_used, model_name
        except Exception as e:
            logger.error(f"Failed to generate command: {str(e)}")
            raise CommandGenerationError(f"Failed to generate command: {str(e)}")

    def _create_prompt(self, user_command: str, context: Dict[str, Any]) -> str:
        return self.command_generation_prompt.format(
            user_command=user_command, context=context
        )

    @staticmethod
    def _extract_command(response: str) -> str:
        return response.strip().split("\n")[0]

    @staticmethod
    def _estimate_tokens(response: str) -> int:
        return len(response.split())

    @classmethod
    def _load_prompt(cls, prompt_name: str) -> str:
        prompt_file = cls.PROMPTS_DIR / f"{prompt_name}.md"
        if prompt_file.exists():
            return prompt_file.read_text()
        else:
            logger.warning(
                f"Prompt file {prompt_file} not found. Using default prompt."
            )
            return ""

    @staticmethod
    def sanitize_command(command: str) -> str:
        return (
            command.strip("`").strip().removeprefix("bash").removeprefix("sh").strip()
        )

    @staticmethod
    def is_valid_command(command: str) -> bool:
        return bool(command.strip())

    async def generate_conflict_resolution_options(
        self, user_command: str, error_message: str, context: Dict[str, Any]
    ) -> List[str]:
        prompt = self.conflict_resolution_prompt.format(
            user_command=user_command,
            conflict_message=error_message,
            context=context,
        )

        response = await self.ai.generate(prompt)

        if response and response.strip():
            options = [
                option.strip() for option in response.split("\n") if option.strip()
            ]
            return options

        logger.error("Failed to generate conflict resolution options")
        return []
