import os
from typing import Any, Dict, List

from .user_preferences_manager import UserPreferencesManager


class ContextBuilder:
    @staticmethod
    def build_enhanced_context(recent_commands: List[str]) -> Dict[str, Any]:
        return {
            "current_directory": os.getcwd(),
            "environment_variables": dict(os.environ),
            "recent_commands": recent_commands,
            "user_preferences": UserPreferencesManager.get_user_preferences(),
        }
