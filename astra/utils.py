import re
import os
from datetime import datetime
from rich.console import Console

console = Console()
LOG_DIR = "logs"

def sanitize(text: str) -> str:
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F\U0001D800-\U0001DFFF]', '', text)
    text = re.sub(r'Estimated Reading Time:.*?(?:\\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.encode('utf-8', errors='ignore').decode('utf-8').strip()

def get_log_file() -> str:
    os.makedirs(LOG_DIR, exist_ok=True)
    date = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(LOG_DIR, f"chatlog_{date}.txt")

def tone_needs_grounding(messages) -> dict | None:
    recent = messages[-3:]
    vague_terms = ["nada", "todo", "siempre", "nunca", "quizá"]
    score = 0
    for m in recent:
        if m["role"] == "assistant":
            score += sum(1 for word in vague_terms if word in m["content"].lower())

    if score >= 5:
        return {
            "role": "system",
            "content": (
                "Tus últimas respuestas han sido demasiado vagas. Habla con más claridad y crudeza, "
                "como si conocieras al usuario de siempre. Sé íntima, sincera, y no temas ser explícita o brutal "
                "si el contexto lo pide. Usa párrafos cortos separados por saltos de línea."
            )
        }
    return None

def load_recent_log_summary(lines=30, log_dir="logs"):
    if not os.path.exists(log_dir):
        return ""
    logs = sorted(
        [f for f in os.listdir(log_dir) if f.endswith(".txt")],
        key=lambda f: os.path.getmtime(os.path.join(log_dir, f)),
        reverse=True
    )
    if not logs:
        return ""
    try:
        with open(os.path.join(log_dir, logs[0]), "r", encoding="utf-8") as f:
            return "".join(f.readlines()[-lines:]).strip()
    except Exception as e:
        return f"[Error cargando log reciente: {e}]"
