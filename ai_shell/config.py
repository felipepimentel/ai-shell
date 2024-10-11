import os
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self, filename: str = "config.yaml"):
        self._config = self._load_config(filename)
        self.history_file: str = self._config.get("history_file", ".ai_shell_history")
        self.prompt: str = self._config.get("prompt", "AI Shell> ")
        self.exit_command: str = self._config.get("exit_command", "exit")
        self.help_command: str = self._config.get("help_command", "help")
        self.history_command: str = self._config.get("history_command", "history")
        self.prompt_timeout: int = self._config.get("prompt_timeout", 30)
        self.default_timeout: int = self._config.get("default_timeout", 120)
        self.long_running_timeout: int = self._config.get(
            "long_running_timeout", 600
        )  # 10 minutos
        self.verbose_mode: bool = self._config.get("verbose_mode", False)
        self.aliases: Dict[str, str] = self._config.get("aliases", {})
        self.dangerous_commands_list: List[str] = self._config.get(
            "dangerous_commands", ["rm -rf", "dd if=", "mkfs", ":(){ :|:& };:"]
        )
        self.clear_cache_command: str = self._config.get(
            "clear_cache_command", "clear_cache"
        )
        self.clear_history_command: str = self._config.get(
            "clear_history_command", "clear_history"
        )
        self.expert_mode: bool = self._config.get("expert_mode", False)

    @staticmethod
    def _load_config(filename: str) -> Dict[str, Any]:
        if os.path.exists(filename):
            with open(filename, "r") as file:
                return yaml.safe_load(file)
        return {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value

    def save_config(self, filename: str = "config.yaml") -> None:
        with open(filename, "w") as file:
            yaml.dump(self._config, file)

    def toggle_simulation_mode(self):
        self.simulation_mode = not self.simulation_mode
        return self.simulation_mode


config = Config()


def get_config() -> Config:
    return config


def load_config(config_file: str = "config.yaml") -> Dict[str, Any]:
    with open(config_file, "r") as f:
        return yaml.safe_load(f)


def save_config(config: Dict[str, Any], config_file: str = "config.yaml") -> None:
    with open(config_file, "w") as f:
        yaml.dump(config, f)
