from typing import Any, Dict

from ..config import config


class UserPreferencesManager:
    @staticmethod
    def get_user_preferences() -> Dict[str, Any]:
        return {
            "preferred_shell": config.get("shell", "bash"),
            "verbose_output": config.get("verbose", True),
            "safety_level": config.get("safety_level", "high"),
        }
