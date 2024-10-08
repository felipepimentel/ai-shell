import json
import os
from datetime import datetime

AI_HISTORY_FILE = "ai_response_history.json"

async def save_ai_response(user_input: str, ai_response: str):
    history_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_input": user_input,
        "ai_response": ai_response
    }

    if os.path.exists(AI_HISTORY_FILE):
        with open(AI_HISTORY_FILE, "r") as f:
            history = json.load(f)
    else:
        history = []

    history.append(history_entry)

    with open(AI_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)