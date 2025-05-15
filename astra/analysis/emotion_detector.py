from astra.memory.core import Core

class EmotionDetector:
    """
    Manages emotion tags and keywords, supporting multi-language and database-backed storage.
    All variable and column names are in English.
    """

    def __init__(self, language="en", tags_dict=None):
        """
        Initialize the tag manager for a specific language.
        :param language: ISO code, e.g. "en" or "es"
        :param tags_dict: Optional dict {"#GRIEF": ["death", "loss", ...], ...}. If None, loads from DB.
        """
        self.language = language
        self.memory_core = Core()
        self._tags = tags_dict if tags_dict is not None else self._load_tags_from_db()

    def _load_tags_from_db(self):
        """
        Loads all tags and their keywords for the given language from DB.
        :return: dict {tag: [keyword, ...], ...}
        """
        return self.memory_core.get_all_tags_with_keywords(language=self.language)

    def detect(self, text: str) -> list[str]:
        """
        Detects which tags appear in the given text.
        :param text: Input string (should be lowercased for accurate match)
        :return: List of matching tags (labels) as strings
        """
        lower_text = text.lower()
        found_tags = []
        for tag, keywords in self._tags.items():
            if any(keyword in lower_text for keyword in keywords):
                found_tags.append(tag)
        return found_tags

    def get_keywords_for_tag(self, tag) -> list[str]:
        """
        Returns the keywords associated with a tag.
        """
        return self._tags.get(tag, [])

    def reload_from_db(self):
        """
        Reloads tags and keywords from the database for current language.
        """
        self._tags = self._load_tags_from_db()

    def all_tags(self) -> list[str]:
        """
        List all tags for the current language.
        """
        return list(self._tags.keys())

    def as_dict(self) -> dict:
        """
        Returns the internal tags dict {tag: [keywords, ...]}
        """
        return dict(self._tags)

    def is_memorable_by_ai(client, text, model_name):
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