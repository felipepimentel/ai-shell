import os
from typing import Dict, List

import yaml


class Config:
    def __init__(self, filename: str = "config.yaml"):
        self._config = self._load_config(filename)
        self.history_file: str = ".ai_shell_history"
        self.prompt: str = "AI Shell> "
        self.exit_command: str = "exit"
        self.help_command: str = "help"
        self.history_command: str = "history"
        self.simulate_command: str = "simulate"
        self.prompt_timeout: int = 30
        self.default_timeout: int = self._config.get("default_timeout", 10)
        self.aliases: Dict[str, str] = self._config.get("aliases", {})
        self.simulation_mode: bool = False
        self.dangerous_commands_list: List[str] = self._config.get(
            "dangerous_commands", ["rm -rf", "dd if=", "mkfs", ":(){ :|:& };:"]
        )

    @staticmethod
    def _load_config(filename: str) -> Dict:
        if os.path.exists(filename):
            with open(filename, "r") as file:
                return yaml.safe_load(file)
        return {}

    def get(self, key: str, default=None):
        return self._config.get(key, default)


config = Config()
