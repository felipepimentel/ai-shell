from typing import Any, Dict, List

from ..datatypes import CommandHistoryEntry


class ContextBuilder:
    def build_enhanced_context(
        self, recent_commands: List[CommandHistoryEntry]
    ) -> Dict[str, Any]:
        context = {
            "recent_commands": [
                {
                    "command": entry.command,
                    "output": entry.output,
                    "status": entry.status,
                }
                for entry in recent_commands
            ]
        }
        return context
