# === as astra/utils.py ===

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

def compress_log_text(text: str) -> str:
    """
    Comprime texto de logs eliminando palabras comunes y normalizando espacios,
    similar a compress_text en emr.py.
    """
    text = re.sub(r"\b(el|la|los|las|de|del|un|una|que|y|en|con|a|por|para)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)  # Reducir múltiples saltos de línea a uno
    return text.strip()

def load_recent_log_summary(lines=200, log_dir="logs"):
    """
    Carga las últimas líneas de los logs más recientes y las comprime.
    """
    if not os.path.exists(log_dir):
        return "[No recent logs found]"

    logs = sorted(
        [f for f in os.listdir(log_dir) if f.endswith(".txt")],
        key=lambda f: os.path.getmtime(os.path.join(log_dir, f)),
        reverse=True
    )
    if not logs:
        return "[No recent logs found]"

    try:
        # Cargar solo el log más reciente
        with open(os.path.join(log_dir, logs[0]), "r", encoding="utf-8") as f:
            content = "".join(f.readlines()[-lines:]).strip()
        # Comprimir el contenido
        compressed = compress_log_text(content)
        return compressed if compressed else "[Empty log]"
    except Exception as e:
        return f"[Error cargando log reciente: {e}]"

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


def compress_text_for_model(text: str) -> str:
    """
    Compress text by removing interior vowels from words longer than 4 characters.
    Humans will find this harder to read, but an LLM can learn to decompress.
    """
    vowels = set('aeiouAEIOU')
    def compress_word(w: str) -> str:
        if len(w) <= 4:
            return w
        # keep first and last character, drop interior vowels
        core = ''.join(c for c in w[1:-1] if c not in vowels)
        return f"{w[0]}{core}{w[-1]}"
    # split on whitespace to preserve punctuation attachments
    return ' '.join(compress_word(w) for w in text.split())

def load_and_summarize_logs(num_files=3, lines_per_file=100, log_dir="logs") -> str:
    """
    Carga múltiples archivos de log recientes, extrae y comprime líneas clave,
    y aplica codificación sintética optimizada para LLMs.
    """
    if not os.path.exists(log_dir):
        return "[No recent logs found]"

    logs = sorted(
        [f for f in os.listdir(log_dir) if f.endswith(".txt")],
        key=lambda f: os.path.getmtime(os.path.join(log_dir, f)),
        reverse=True
    )[:num_files]

    all_content = []
    for log_file in logs:
        path = os.path.join(log_dir, log_file)
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-lines_per_file:]
                compressed = compress_log_text("".join(lines))
                synthetic = compress_text_for_model(compressed)
                all_content.append(synthetic)
        except Exception as e:
            all_content.append(f"[Error en {log_file}: {e}]")

    return "\n".join(all_content) if all_content else "[Empty logs]"
