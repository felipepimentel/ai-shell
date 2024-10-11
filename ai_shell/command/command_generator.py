from typing import Any, Dict, Optional, Tuple

from ai_shell.llm import ai

from ..utils.logger import get_logger

logger = get_logger("ai_shell.command_generator")


class CommandGenerator:
    async def generate_command(
        self, user_command: str, context: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        logger.info(f"Generating command for user input: {user_command}")

        prompt = f"""
        Given the following user command in natural language:
        "{user_command}"
        
        And the following context:
        {context}
        
        Generate a valid shell command that accurately represents the user's intention.
        Ensure that all paths and arguments are correctly formatted and preserved.
        
        Return only the generated shell command, without any additional explanation.
        """

        try:
            generated_command = await ai.generate(prompt)
            generated_command = generated_command.strip()
            logger.info(f"Generated command: {generated_command}")
            return (
                generated_command,
                None,
                "AI Model",
            )  # You may want to add actual token count and model name
        except Exception as e:
            logger.error(f"Error generating command: {str(e)}")
            return None, None, None
