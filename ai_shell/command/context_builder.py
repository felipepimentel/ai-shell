from typing import List, Dict, Any
from ..datatypes import CommandHistoryEntry

class ContextBuilder:
    def build_enhanced_context(self, recent_commands: List[CommandHistoryEntry]) -> Dict[str, Any]:
        context = {
            "recent_commands": [
                {
                    "command": entry.command,
                    "output": entry.output,
                    "status": entry.status
                }
                for entry in recent_commands
            ]
        }
        # Add any other relevant context information here
        return context
