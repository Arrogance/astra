# === as astra/analysis/concept_labels.py ===

class ConceptDetector:
    def __init__(self, language="es"):
        self.language = language
        self.concepts = {
            "#PAST": {
                "es": ["ayer", "antes", "recuerdo", "fue", "perdí", "tuve"],
                "en": ["yesterday", "ago", "remember", "was", "lost", "had"]
            },
            "#NOW": {
                "es": ["ahora", "hoy", "siento", "estoy", "me pasa"],
                "en": ["now", "today", "feel", "am", "happening"]
            },
            "#FUTURE": {
                "es": ["mañana", "algún día", "quizá", "espero", "soñaré"],
                "en": ["tomorrow", "someday", "maybe", "hope", "will dream"]
            }
        }

    def detect(self, text: str) -> list[str]:
        lower = text.lower()
        tags = []

        for label, keywords in self.concepts.items():
            if any(word in lower for word in keywords.get(self.language, [])):
                tags.append(label)

        return tags
