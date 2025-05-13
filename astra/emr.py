# === astra/emr.py ===

import json
from typing import List, Tuple
from pathlib import Path

WEIGHTS_PATH = Path("emr_weights.json")

def load_emr_weights():
    if WEIGHTS_PATH.exists():
        with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def update_emr_weight(tag, new_weight):
    weights = load_emr_weights()
    weights[tag] = float(new_weight)
    with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump(weights, f, indent=2)

def encode_fragments_with_emr(fragments: List[Tuple[str, str, str]]) -> str:
    """
    Codifica fragmentos con formato EMR comprimido para LLM.
    Entrada: lista de tuplas (tag, text, date)
    Salida: líneas tipo "DLU|2025-05-10|m sentí sl cnd djst eso"
    """
    if not fragments:
        return "[No memory fragments found]"

    lines = []
    for tag, text, date in fragments:
        tag_short = tag.strip()[:3].upper()
        text_compact = compress_text(text.strip())
        lines.append(f"{tag_short}|{date}|{text_compact}")

    return "\n".join(lines)

def compress_text(text: str) -> str:
    """
    Algoritmo simple de compresión textual sin perder legibilidad.
    Opcional: puedes aplicar alias, eliminación de artículos, etc.
    """
    import re
    text = re.sub(r"\b(el|la|los|las|de|del|un|una|que|y|en|con)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text
