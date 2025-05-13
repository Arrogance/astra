# === as astra/context_builder.py ===

import sqlite3
from pathlib import Path
from astra.memory import ensure_user_initialized, get_db_cursor, load_last_fragments
from astra.emr import encode_fragments_with_emr
from astra.utils import load_recent_log_summary, compress_text_for_model, load_and_summarize_logs
from collections import defaultdict

# EMR tags
emr_tags = {
    "duelo": "@DL", "deseo": "@DS", "identidad": "@ID", "culpa": "@CU", "nostalgia": "@NS",
    "esperanza": "@ES", "rabia": "@RB", "soledad": "@SO", "afecto": "@AF", "ansiedad": "@AN", "vergüenza": "@VG"
}

def detect_temporal_label(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in ["ayer", "antes", "recuerdo", "fue", "perdí", "tuve"]): return "#PAST"
    if any(w in lower for w in ["ahora", "hoy", "siento", "estoy", "me pasa"]): return "#NOW"
    if any(w in lower for w in ["mañana", "algún día", "quizá", "espero", "soñaré"]): return "#FUT"
    return ""

def build_context(profile="astra") -> str:
    # Carga instrucciones del perfil
    instr_path = Path(f"instructions/{profile}.txt")
    if not instr_path.exists():
        raise FileNotFoundError(f"Instrucciones no encontradas: {instr_path}")

    c = get_db_cursor()
    user_data = ensure_user_initialized(c)

    # SafeDict para permitir placeholders ausentes en instructions
    class SafeDict(defaultdict):
        def __missing__(self, key):
            return f"{{{key}}}"

    # Instrucciones con interpolación de variables de usuario
    base_instructions = instr_path.read_text(encoding="utf-8").strip()
    base_instructions = base_instructions.format_map(SafeDict(lambda: "", **user_data))

    # EMR reference
    emr_path = Path("emr.txt")
    emr_reference = emr_path.read_text(encoding="utf-8").strip() if emr_path.exists() else "[EMR reference missing]"

    # Fragmentos codificados como EMR
    fragments = load_last_fragments(limit=10)
    emr_block = encode_fragments_with_emr(fragments)

    # Datos del usuario
    user_block = "[User memory:]\n"
    for k, v in user_data.items():
        if v.strip():
            user_block += f"- {k.capitalize()}: {v}\n"

    # Cargar y sintetizar múltiples logs recientes
    recent_logs = load_and_summarize_logs(num_files=3, lines_per_file=100)
    log_block = f"[Recent conversation logs]\n{recent_logs}"

    # Unir todo
    context = f"{base_instructions}\n\n{emr_reference}\n\n{user_block}\n\n[EMR memory block]\n{emr_block}\n\n{log_block}"
    return context
