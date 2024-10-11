from typing import Any, Dict, List

from .config import config
from .datatypes import CommandHistoryEntry


class ContextManager:
    @staticmethod
    def build_enhanced_context(
        recent_commands: List[CommandHistoryEntry],
    ) -> Dict[str, Any]:
        return {
            "recent_commands": [
                {
                    "command": entry.command,
                    "output": entry.output,
                    "status": entry.status,
                }
                for entry in recent_commands
            ]
        }

    @staticmethod
    def get_user_preferences() -> Dict[str, Any]:
        return {
            "preferred_shell": config.get("shell", "bash"),
            "verbose_output": config.get("verbose", True),
            "safety_level": config.get("safety_level", "high"),
        }
