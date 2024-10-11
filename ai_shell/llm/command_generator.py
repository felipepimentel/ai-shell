from typing import Tuple, Optional

async def generate_command(user_input: str, model: str) -> Tuple[Optional[str], Optional[int], str]:
    if user_input.lower() == "find all python files":
        return "find . -name '*.py'", 10, model
    elif user_input.lower() == "say hello":
        return "echo 'Hello, World!'", 10, model
    elif user_input.lower() == "invalid command":
        return None, None, model
    else:
        # Simular a geração de comando para outros casos
        return user_input, 10, model