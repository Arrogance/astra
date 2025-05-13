# === astra/memory/core.py ===

import sqlite3
import json
from datetime import datetime
from astra.utils import sanitize
from astra.memory.emr import load_emr_weights

DB_FILE = "astra_memory.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# EMR tags
emr_tags = {
    "duelo": "@DL", "deseo": "@DS", "identidad": "@ID", "culpa": "@CU", "nostalgia": "@NS",
    "esperanza": "@ES", "rabia": "@RB", "soledad": "@SO", "afecto": "@AF", "ansiedad": "@AN", "vergüenza": "@VG"
}

def get_db_cursor():
    return c

def close_connection():
    conn.close()

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS fragments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, tag TEXT, date TEXT, user_input TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS forgotten_fragments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, tag TEXT, date TEXT, user_input TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS diary
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, context TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS last_inputs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS last_responses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_memory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, value TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS emotion_tags
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT NOT NULL, keyword TEXT NOT NULL)''')
    c.execute("CREATE INDEX IF NOT EXISTS idx_fragments_text ON fragments(text)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_forgotten_text ON forgotten_fragments(text)")
    conn.commit()

def detect_temporal_label(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in ["ayer", "antes", "recuerdo", "fue", "perdí", "tuve"]): return "#PAST"
    if any(w in lower for w in ["ahora", "hoy", "siento", "estoy", "me pasa"]): return "#NOW"
    if any(w in lower for w in ["mañana", "algún día", "quizá", "espero", "soñaré"]): return "#FUT"
    return ""

def log_last_input(text):
    text = sanitize(text)
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO last_inputs (text, date) VALUES (?, ?)", (text, date))
    c.execute("DELETE FROM last_inputs WHERE id NOT IN (SELECT id FROM last_inputs ORDER BY date DESC LIMIT 5)")
    conn.commit()

def log_last_response(text):
    text = sanitize(text)
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO last_responses (text, date) VALUES (?, ?)", (text, date))
    c.execute("DELETE FROM last_responses WHERE id NOT IN (SELECT id FROM last_responses ORDER BY date DESC LIMIT 5)")
    conn.commit()

def log_diary(text, context="sistema"):
    text = sanitize(text)
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO diary (text, context, date) VALUES (?, ?, ?)", (text, context, date))
    conn.commit()

def update_memory(key, value):
    value = sanitize(value)
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO user_memory (key, value, date) VALUES (?, ?, ?)", (key, value, date))
    conn.commit()

def load_last_fragments(limit=50):
    """
    Carga los últimos fragmentos, puntuados por peso emocional y antigüedad.
    """
    c = get_db_cursor()
    weights = load_emr_weights()

    c.execute("SELECT tag, text, date FROM fragments")
    fragments = c.fetchall()

    def score(row):
        tag, _, date = row
        weight = weights.get(tag, 1.0)
        try:
            timestamp = datetime.strptime(date, "%Y-%m-%d %H:%M")
        except:
            return 0  # descartar si hay error
        recency = (datetime.now() - timestamp).total_seconds()
        return weight / (1 + recency / 3600)

    return sorted(fragments, key=score, reverse=True)[:limit]

def extract_memory_note(text):
    import re
    patterns = [
        r"acuérdate de (?:que )?(.*)",
        r"recuérdame (?:que )?(.*)",
        r"anota (?:que )?(.*)",
        r"apunta (?:que )?(.*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().rstrip(".")
    return None

def format_tags(emr_tag: str, analysis: dict) -> str:
    """
    Combina una etiqueta EMR (ej: @DL) con las etiquetas del análisis
    (concepts y emotions), y las devuelve como string serializado.

    Ejemplo: "@DL #PAST #NEGATIVE"
    """
    if not emr_tag:
        emr_tag = "reflexión"  # etiqueta por defecto si no hay EMR match

    concept_tags = analysis.get("concepts", [])
    emotion_tags = analysis.get("emotions", [])

    all_tags = [emr_tag] + sorted(set(concept_tags + emotion_tags))
    return " ".join(all_tags).strip()

def save_fragment(text, tag, user_input, client):
    text = sanitize(text).replace("\n", " ")
    user_input = sanitize(user_input).replace("\n", " ")
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    c = get_db_cursor()
    c.execute("INSERT INTO fragments (text, tag, date, user_input) VALUES (?, ?, ?, ?)",
              (text, tag, date, user_input))
    c.connection.commit()

def filter_relevant_fragments(user_input, limit=15):
    keywords = user_input.lower().split()
    if not keywords:
        return []
    query = "SELECT tag, text, date FROM fragments WHERE " + " OR ".join(["text LIKE ?" for _ in keywords])
    params = [f"%{kw}%" for kw in keywords]
    c.execute(query, params)
    return c.fetchall()[:limit]

def tag_fragment(text: str) -> str:
    text = text.lower()
    c = get_db_cursor()
    c.execute("SELECT tag, keyword FROM emotion_tags")
    entries = c.fetchall()

    tag_score = {}

    for tag, keyword in entries:
        if keyword in text:
            tag_score[tag] = tag_score.get(tag, 0) + 1

    if not tag_score:
        return "reflexión"

    return max(tag_score.items(), key=lambda x: x[1])[0]

def is_memorable_by_ai(client, text, model_name):
    """
    Evalúa si 'text' debe guardarse como recuerdo emocional,
    usando 'aux_client' con el modelo 'aux_model_name'.
    """
    # Construimos el prompt
    messages = [
        {
            "role": "system",
            "content": (
                "Eres un asistente emocional que detecta si un fragmento de texto "
                "debería guardarse como un recuerdo emocional importante. "
                "Responde únicamente “Sí” o “No”."
            )
        },
        {
            "role": "user",
            "content": (
                f"Texto: {text}\n\n"
                "¿Debo guardar este fragmento como un recuerdo emocional importante?"
            )
        }
    ]

    try:
        # Llamada correcta: solo le pasamos mensajes y nombre de modelo
        response_text = client.chat_completion(messages, model_name)
        # response_text ya es un string
        normalized = response_text.strip().lower()
        # Devuelve True sólo si ha respondido afirmativamente
        return normalized in ["sí", "si", "yes", "sí, guardar", "yes, store"]
    except Exception as e:
        # Por si algo falla, logueamos y devolvemos False
        print(f"[debug] Error en is_memorable_by_ai: {e}")
        return False

def ensure_user_initialized(cursor):
    cursor.execute("SELECT key, value FROM user_memory")
    data = {row[0]: row[1] for row in cursor.fetchall()}

    campos_requeridos = {
        "name": "¿Cuál es tu nombre real?",
        "alias": "¿Y cómo debería llamarte yo?",
        "fecha_inicio": datetime.now().strftime("%Y-%m-%d")
    }

    for key, pregunta in campos_requeridos.items():
        if key not in data or not data[key]:
            if "¿" in pregunta:  # Es una pregunta
                from rich.prompt import Prompt
                respuesta = Prompt.ask(pregunta)
            else:
                respuesta = pregunta  # valor directo como fecha
            cursor.execute("INSERT INTO user_memory (key, value, date) VALUES (?, ?, ?)",
                           (key, respuesta, datetime.now().strftime("%Y-%m-%d %H:%M")))
            data[key] = respuesta

    # Añadir campos opcionales si no existen, con valor vacío
    opcionales = ["pronombre", "edad", "ciudad"]
    for key in opcionales:
        if key not in data:
            cursor.execute("INSERT INTO user_memory (key, value, date) VALUES (?, ?, ?)",
                           (key, "", datetime.now().strftime("%Y-%m-%d %H:%M")))
            data[key] = ""

    cursor.connection.commit()
    return data

def load_user_fields():
    path = "user_fields.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "name": "Nombre real",
            "alias": "Apodo",
            "fecha_inicio": "Fecha de inicio",
            "edad": "Edad",
            "ciudad": "Ciudad",
            "pronombre": "Pronombre",
            "notas": "Notas"
        }
