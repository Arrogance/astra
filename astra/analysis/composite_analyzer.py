# === as astra/analysis/composite_analyzer.py ===

from astra.analysis.concept_labels import ConceptDetector
from astra.analysis.emotion_detector import EmotionDetector

class CompositeAnalyzer:
    def __init__(self, language="es"):
        self.language = language
        self.concept_analyzer = ConceptDetector(language=language)
        self.emotion_analyzer = EmotionDetector(language=language)
        # TODO: self.intent_analyzer = IntentDetector(language)
        # TODO: self.tone_analyzer = ToneDetector(language)

    def analyze(self, text: str) -> dict:
        return {
            "concepts": self.concept_analyzer.detect(text),
            "emotions": self.emotion_analyzer.detect(text),
            # "intent": self.intent_analyzer.detect(text),
            # "tone": self.tone_analyzer.detect(text)
        }
