import os
from typing import Any, Dict, Tuple

import aiohttp
from dotenv import load_dotenv

from ai_shell.utils.logger import get_logger

load_dotenv()

logger = get_logger("ai_shell.llm.openrouter_ai")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterAI:
    async def generate_command(self, prompt: str) -> Tuple[str, int, str]:
        if not OPENROUTER_API_KEY:
            logger.error("OPENROUTER_API_KEY is not set")
            raise ValueError("OPENROUTER_API_KEY is not set")

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        data: Dict[str, Any] = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
            "temperature": 0.7,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OPENROUTER_URL, headers=headers, json=data
                ) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        result = await response.json()
                        if "choices" not in result or not result["choices"]:
                            logger.error(f"Unexpected API response structure: {result}")
                            raise ValueError("Unexpected API response structure")
                        content = result["choices"][0]["message"]["content"].strip()
                        tokens_used = result["usage"]["total_tokens"]
                        model_used = result["model"]
                        return content, tokens_used, model_used
                    else:
                        logger.error(
                            f"Error from OpenRouter API: {response.status} - {response_text}"
                        )
                        raise Exception(
                            f"API Error: {response.status} - {response_text}"
                        )
        except aiohttp.ClientError as e:
            logger.exception(f"Network error in generate_command: {str(e)}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in generate_command: {str(e)}")
            raise
