import json
import os
from rich.prompt import Prompt

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    # Config inicial si no existe
    key = Prompt.ask("[bold cyan]Enter your OpenRouter API key[/]")
    config = {
        "api_key": key,
        "model": "openai/gpt-4o",
        "aux_model": "openai/gpt-3.5-turbo",
        "referer": "https://github.com/yourusername/astra",
        "title": "Astra Chatbot",
        "profile": "astra",
        "max_tokens": 1000
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    return config
