import os

import aiohttp
from dotenv import load_dotenv

from ai_shell.utils.logger import get_logger

load_dotenv()

logger = get_logger("ai_shell.llm.openrouter_ai")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterAI:
    def __init__(self):
        self.model = OPENROUTER_MODEL

    async def generate(self, prompt: str) -> str:
        logger.info(f"Generating response for prompt: {prompt[:50]}...")

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OPENROUTER_URL, json=data, headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        generated_text = result["choices"][0]["message"]["content"]
                        logger.info(f"Generated response: {generated_text[:50]}...")
                        return generated_text
                    else:
                        error_message = await response.text()
                        logger.error(f"Error from OpenRouter API: {error_message}")
                        raise Exception(f"OpenRouter API error: {error_message}")
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise

    def get_model_name(self) -> str:
        return self.model
