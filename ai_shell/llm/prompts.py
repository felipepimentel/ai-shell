async def build_contextual_prompt(history, max_entries=10):
    structured_prompt = "Here is what has been done so far:\n"
    for entry in history[-max_entries:]:
        structured_prompt += (
            f"Command: {entry.command}\n"
            f"Output: {entry.output}\n"
            f"Timestamp: {entry.timestamp}\n"
            f"Working Directory: {entry.working_directory}\n\n"
        )
    return structured_prompt
