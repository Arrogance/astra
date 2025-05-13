# === as astra/analysis/emotion_detector.py ===

class EmotionDetector:
    def __init__(self, language="es"):
        self.language = language
        self.emotions = {
            "#POSITIVE": {
                "es": ["feliz", "alegría", "amo", "brilla", "esperanza", "abrazo", "sonrío", "consuelo"],
                "en": ["happy", "joy", "love", "shine", "hope", "hug", "smile", "comfort"]
            },
            "#NEGATIVE": {
                "es": ["triste", "sufro", "miedo", "odio", "dolor", "lloro", "vacío", "rabia"],
                "en": ["sad", "suffer", "fear", "hate", "pain", "cry", "empty", "anger"]
            },
            "#BITTERSWEET": {
                "es": ["recuerdo", "añoro", "nostalgia", "melancolía", "fue bonito", "adiós"],
                "en": ["remember", "miss", "nostalgia", "melancholy", "it was beautiful", "goodbye"]
            }
        }

    def detect(self, text: str) -> list[str]:
        lower = text.lower()
        tags = []

        for label, keywords in self.emotions.items():
            if any(word in lower for word in keywords.get(self.language, [])):
                tags.append(label)

        return tags
