import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from astra.memory import get_db_cursor, tag_fragment

def actualizar_etiquetas_y_limpiar_lineas():
    c = get_db_cursor()
    c.execute("SELECT id, text FROM fragments")
    filas = c.fetchall()

    actualizados = 0
    for fid, texto in filas:
        texto_limpio = texto.replace("\n", " ").strip()
        nueva_etiqueta = tag_fragment(texto_limpio)
        c.execute("UPDATE fragments SET text = ?, tag = ? WHERE id = ?", (texto_limpio, nueva_etiqueta, fid))
        actualizados += 1

    c.connection.commit()
    print(f"✅ {actualizados} fragmentos reetiquetados y limpiados de saltos de línea.")

if __name__ == "__main__":
    actualizar_etiquetas_y_limpiar_lineas()
