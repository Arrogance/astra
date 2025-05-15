# === as astra/memory/filters.py ===

class FragmentFilter:
    def __init__(self):
        self.reason = None

    def should_save(self, analysis: dict) -> bool:
        emotions = analysis.get("emotions", [])  # Ahora serán como ["#DUELO", "#NOSTALGIA"]
        concepts = analysis.get("concepts", [])

        # Definir qué emociones específicas o combinaciones justifican guardar
        significant_emotions = {
            "#DUELO", "#RABIA", "#CULPA", "#SOLEDAD", "#ANSIEDAD", 
            "#VERGUENZA", "#DESEO", "#ESPERANZA", "#NOSTALGIA", 
            # #IDENTIDAD y #AFECTO podrían ser menos críticos para guardar siempre,
            # o depender de otros factores/combinaciones.
            # Las anteriores #NEGATIVE y #BITTERSWEET se cubren ahora más específicamente.
        }

        if any(tag in emotions for tag in significant_emotions):
            self.reason = f"Fragment contains significant emotions: {', '.join(emotions)}"
            return True

        # Mantener o ajustar lógica existente con conceptos si es necesario
        if "#PAST" in concepts and "#NOW" not in concepts and any(e in emotions for e in ["#NOSTALGIA", "#DUELO"]): # Ejemplo: recuerdo pasado con nostalgia o duelo
            self.reason = "Fragment is a past reflection with emotional weight."
            return True

        if "#FUTURE" in concepts and any(e in emotions for e in ["#ESPERANZA", "#ANSIEDAD"]): # Ejemplo: futuro con esperanza o ansiedad
            self.reason = "Fragment is a future projection with emotional weight."
            return True
            
        # Ejemplo de regla más específica: si hay afecto Y se habla del pasado
        if "#AFECTO" in emotions and "#PAST" in concepts:
            self.reason = "Fragment expresses affection about the past."
            return True

        self.reason = "Fragment lacked sufficient emotional or reflective triggers for saving."
        return False