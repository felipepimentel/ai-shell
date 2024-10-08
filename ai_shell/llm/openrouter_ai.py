import os

import aiohttp
from dotenv import load_dotenv

from ai_shell.utils.logger import get_logger

load_dotenv()

logger = get_logger("ai_shell.llm.openrouter_ai")


class OpenRouterAI:
    def __init__(self, api_key=None):
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")

    async def generate_command(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Referer": "https://github.com/felipepimentel/ai-shell",
            "X-Title": "AI Shell",
        }
        data = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "system", "content": prompt},
            ],
            "max_tokens": 100,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url, json=data, headers=headers
                ) as response:
                    if response.status == 200:
                        response_json = await response.json()
                        return response_json["choices"][0]["message"]["content"].strip()
                    else:
                        logger.error(
                            f"API Error: {response.status} - {await response.text()}"
                        )
                        return None
        except aiohttp.ClientError as e:
            logger.error(f"Connection error: {e}")
            return None
