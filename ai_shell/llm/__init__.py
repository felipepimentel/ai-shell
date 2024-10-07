from .openrouter_ai import OpenRouterAI
from .prompts import build_contextual_prompt

ai = OpenRouterAI()

__all__ = ["ai", "build_contextual_prompt"]
