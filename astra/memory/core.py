import sqlite3
import json
from datetime import datetime
from astra.utils import sanitize

class Core:
    DB_FILE = "astra_memory.db"

    def __init__(self, db_file=None):
        self.DB_FILE = db_file or Core.DB_FILE
        self.conn = sqlite3.connect(self.DB_FILE, check_same_thread=False)
        self.c = self.conn.cursor()
        self.init_db()
        self.emr_tags = self.get_all_emotion_tags()

    def get_db_cursor(self):
        return self.c

    def close_connection(self):
        self.conn.close()

    def init_db(self):
        self.c.execute('''CREATE TABLE IF NOT EXISTS fragments
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, tag TEXT, date TEXT, user_input TEXT)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS forgotten_fragments
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, tag TEXT, date TEXT, user_input TEXT)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS diary
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, context TEXT, date TEXT)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS last_inputs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, date TEXT)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS last_responses
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, date TEXT)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS user_memory
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, value TEXT, date TEXT)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS emotion_tags
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT NOT NULL, keyword TEXT NOT NULL, language TEXT, significant INTEGER DEFAULT 1)''')
        self.c.execute("CREATE INDEX IF NOT EXISTS idx_fragments_text ON fragments(text)")
        self.c.execute("CREATE INDEX IF NOT EXISTS idx_forgotten_text ON forgotten_fragments(text)")
        self.conn.commit()

    def ensure_user_initialized(self):
        self.c.execute("SELECT key, value FROM user_memory")
        data = {row[0]: row[1] for row in self.c.fetchall()}

        campos_requeridos = {
            "name": "¿Cuál es tu nombre real?",
            "alias": "¿Y cómo debería llamarte yo?",
            "fecha_inicio": datetime.now().strftime("%Y-%m-%d")
        }
        for key, pregunta in campos_requeridos.items():
            if key not in data or not data[key]:
                if "¿" in pregunta:
                    from rich.prompt import Prompt
                    respuesta = Prompt.ask(pregunta)
                else:
                    respuesta = pregunta
                self.c.execute("INSERT INTO user_memory (key, value, date) VALUES (?, ?, ?)",
                               (key, respuesta, datetime.now().strftime("%Y-%m-%d %H:%M")))
                data[key] = respuesta

        opcionales = ["pronombre", "edad", "ciudad"]
        for key in opcionales:
            if key not in data:
                self.c.execute("INSERT INTO user_memory (key, value, date) VALUES (?, ?, ?)",
                               (key, "", datetime.now().strftime("%Y-%m-%d %H:%M")))
                data[key] = ""

        self.conn.commit()
        return data

    def load_user_fields(self):
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

    def log_last_input(self, text):
        text = sanitize(text)
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.c.execute("INSERT INTO last_inputs (text, date) VALUES (?, ?)", (text, date))
        self.c.execute("DELETE FROM last_inputs WHERE id NOT IN (SELECT id FROM last_inputs ORDER BY date DESC LIMIT 5)")
        self.conn.commit()

    def log_last_response(self, text):
        text = sanitize(text)
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.c.execute("INSERT INTO last_responses (text, date) VALUES (?, ?)", (text, date))
        self.c.execute("DELETE FROM last_responses WHERE id NOT IN (SELECT id FROM last_responses ORDER BY date DESC LIMIT 5)")
        self.conn.commit()

    def log_diary(self, text, context="sistema"):
        text = sanitize(text)
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.c.execute("INSERT INTO diary (text, context, date) VALUES (?, ?, ?)", (text, context, date))
        self.conn.commit()

    def update_memory(self, key, value):
        value = sanitize(value)
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.c.execute("INSERT INTO user_memory (key, value, date) VALUES (?, ?, ?)", (key, value, date))
        self.conn.commit()

    def load_last_fragments(self, limit=50):
        from astra.memory.emr import load_emr_weights
        weights = load_emr_weights()
        self.c.execute("SELECT tag, text, date FROM fragments")
        fragments = self.c.fetchall()

        def score(row):
            tag_string, _, date_str = row
            main_emr_tag_short = tag_string.split(" ")[0] if tag_string else ""
            weight = weights.get(main_emr_tag_short, 1.0)
            try:
                timestamp = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            except ValueError:
                return 0
            recency = (datetime.now() - timestamp).total_seconds()
            return weight / (1 + recency / 3600.0) if (1 + recency / 3600.0) > 0 else 0

        return sorted(fragments, key=score, reverse=True)[:limit]

    def filter_relevant_fragments(self, user_input, limit=15):
        keywords = user_input.lower().split()
        if not keywords:
            return []
        query = "SELECT tag, text, date FROM fragments WHERE " + " OR ".join(["text LIKE ?" for _ in keywords])
        params = [f"%{kw}%" for kw in keywords]
        self.c.execute(query, params)
        return self.c.fetchall()[:limit]

    # --- Métodos de tags y emociones ---

    def get_all_emotion_tags(self, language="en"):
        self.c.execute("SELECT DISTINCT tag FROM emotion_tags WHERE language = ?", (language,))
        return [row[0] for row in self.c.fetchall()]

    def get_keywords_for_tag(self, tag, language="en"):
        self.c.execute("SELECT keyword FROM emotion_tags WHERE tag = ? AND language = ?", (tag, language))
        return [row[0] for row in self.c.fetchall()]

    def get_all_tags_with_keywords(self, language="en"):
        self.c.execute("SELECT tag, keyword FROM emotion_tags WHERE language = ?", (language,))
        tags_dict = {}
        for tag, keyword in self.c.fetchall():
            tags_dict.setdefault(tag, []).append(keyword)
        return tags_dict

    def get_significant_tags(self, language="en"):
        self.c.execute("SELECT DISTINCT tag FROM emotion_tags WHERE significant = 1 AND language = ?", (language,))
        return set(row[0] for row in self.c.fetchall())

    # --- Fragmentos y etiquetado ---

    def save_fragment(self, text, tag, user_input, client=None):
        text = sanitize(text).replace("\n", " ")
        user_input = sanitize(user_input).replace("\n", " ")
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.c.execute("INSERT INTO fragments (text, tag, date, user_input) VALUES (?, ?, ?, ?)",
                       (text, tag, date, user_input))
        self.conn.commit()

    def tag_fragment(self, text: str) -> str:
        # Por defecto, reemplaza por tu lógica avanzada o llama a tu analyzer externo
        return "reflexión"

    def format_tags(self, emr_tag: str, analysis: dict) -> str:
        concept_tags = analysis.get("concepts", [])
        emotion_tags_from_analysis = analysis.get("emotions", [])
        all_tags_set = set()
        ordered_tags = [emr_tag]
        all_tags_set.add(emr_tag)
        for tag in emotion_tags_from_analysis:
            if tag not in all_tags_set:
                ordered_tags.append(tag)
                all_tags_set.add(tag)
        for tag in concept_tags:
            if tag not in all_tags_set:
                ordered_tags.append(tag)
                all_tags_set.add(tag)
        return " ".join(ordered_tags).strip()

    def is_memorable_by_ai(self, client, text, model_name):
        """
        Evalúa si 'text' debe guardarse como recuerdo emocional,
        usando 'client' con el modelo 'model_name'.
        """
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
            response_text = client.chat_completion(messages, model_name)
            normalized = response_text.strip().lower()
            return normalized in ["sí", "si", "yes", "sí, guardar", "yes, store"]
        except Exception as e:
            print(f"[debug] Error en is_memorable_by_ai: {e}")
            return False

