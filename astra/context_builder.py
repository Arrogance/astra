from pathlib import Path
from astra.memory.core import Core
from astra.memory.emr import encode_fragments_with_emr
from astra.utils import load_and_summarize_logs
from collections import defaultdict

class ContextBuilder:
    emr_tags = {
        "grief": "@DL", "desire": "@DS", "identity": "@ID", "guilt": "@CU", "nostalgia": "@NS",
        "hope": "@ES", "rage": "@RB", "loneliness": "@SO", "affection": "@AF", "anxiety": "@AN", "shame": "@VG"
    }

    def __init__(self, core=None):
        # You can pass an initialized Core, or create a new one by default
        self.core = core if core else Core()

    @staticmethod
    def detect_temporal_label(text: str) -> str:
        lower = text.lower()
        if any(w in lower for w in ["yesterday", "before", "remember", "was", "lost", "had"]): return "#PAST"
        if any(w in lower for w in ["now", "today", "feel", "am", "happening"]): return "#NOW"
        if any(w in lower for w in ["tomorrow", "someday", "maybe", "hope", "dream"]): return "#FUT"
        return ""

    def build_context(self, profile="astra") -> str:
        instr_path = Path(f"instructions/{profile}.txt")
        if not instr_path.exists():
            raise FileNotFoundError(f"Instructions not found: {instr_path}")

        user_data = self.core.ensure_user_initialized()

        class SafeDict(defaultdict):
            def __missing__(self, key):
                return f"{{{key}}}"

        base_instructions = instr_path.read_text(encoding="utf-8").strip()
        base_instructions = base_instructions.format_map(SafeDict(lambda: "", **user_data))

        emr_path = Path("emr.txt")
        emr_reference = emr_path.read_text(encoding="utf-8").strip() if emr_path.exists() else "[EMR reference missing]"

        fragments = self.core.load_last_fragments(limit=10)
        emr_block = encode_fragments_with_emr(fragments)

        user_block = "[User memory:]\n"
        for k, v in user_data.items():
            if v.strip():
                user_block += f"- {k.capitalize()}: {v}\n"

        recent_logs = load_and_summarize_logs(num_files=3, lines_per_file=100)
        log_block = f"[Recent conversation logs]\n{recent_logs}"

        context = (
            f"{base_instructions}\n\n"
            f"{emr_reference}\n\n"
            f"{user_block}\n\n"
            f"[EMR memory block]\n{emr_block}\n\n"
            f"{log_block}"
        )
        return context
