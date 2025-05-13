import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from astra.memory import get_db_cursor

def resetear_memoria_de_astra():
    c = get_db_cursor()
    tablas = ("fragments", "forgotten_fragments", "diary")

    for tabla in tablas:
        c.execute(f"DELETE FROM {tabla}")
        c.execute("DELETE FROM sqlite_sequence WHERE name = ?", (tabla,))

    c.connection.commit()
    print("🧹 Memoria de Astra borrada: fragments, forgotten_fragments y diary.")

if __name__ == "__main__":
    resetear_memoria_de_astra()
