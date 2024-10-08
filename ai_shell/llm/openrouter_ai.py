import logging
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv()


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
            "model": "openai/gpt-4-turbo",
            "messages": [
                {"role": "system", "content": "You are an AI assistant that generates shell commands based on user requests. Provide only the command without any explanation. Do not include 'cd' commands or any navigation unless explicitly requested. The command should be executable as-is in the current directory."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 100,  # Limit the response length
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
                        logging.error(
                            f"API Error: {response.status} - {await response.text()}"
                        )
                        return None
        except aiohttp.ClientError as e:
            logging.error(f"Connection error: {e}")
            return None
