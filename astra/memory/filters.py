# === as astra/memory/filters.py ===

class FragmentFilter:
    def __init__(self):
        self.reason = None

    def should_save(self, analysis: dict) -> bool:
        emotions = analysis.get("emotions", [])
        concepts = analysis.get("concepts", [])

        if any(tag in emotions for tag in ("#NEGATIVE", "#BITTERSWEET")):
            return True

        if "#PAST" in concepts and "#NOW" not in concepts:
            return True

        if "#FUTURE" in concepts and "#BITTERSWEET" in emotions:
            return True

        self.reason = "Fragment lacked emotional or reflective weight"
        return False
