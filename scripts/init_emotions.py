import sqlite3

DB_PATH = "astra.sqlite3"

emotions = [
    ("@DL", "Duelo / Pérdida", "es", 1),
    ("@DS", "Deseo / Motivación", "es", 1),
    ("@ID", "Identidad", "es", 1),
    ("@CU", "Culpa", "es", 1),
    ("@NS", "Nostalgia", "es", 1),
    ("@ES", "Esperanza", "es", 1),
    ("@RB", "Rabia", "es", 1),
    ("@SO", "Soledad", "es", 1),
    ("@AF", "Afecto / Cariño", "es", 1),
    ("@AN", "Ansiedad", "es", 1),
    ("@VG", "Vergüenza", "es", 1),
    ("@DL", "Grief / Loss", "en", 1),
    ("@DS", "Desire / Motivation", "en", 1),
    ("@ID", "Identity", "en", 1),
    ("@CU", "Guilt", "en", 1),
    ("@NS", "Nostalgia", "en", 1),
    ("@ES", "Hope", "en", 1),
    ("@RB", "Rage", "en", 1),
    ("@SO", "Loneliness", "en", 1),
    ("@AF", "Affection / Fondness", "en", 1),
    ("@AN", "Anxiety", "en", 1),
    ("@VG", "Shame", "en", 1),
]

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS emr_tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tag TEXT NOT NULL,
                        description TEXT,
                        lang TEXT DEFAULT 'es',
                        is_significant INTEGER DEFAULT 1
                   )
                   ''')
    cursor.execute('DELETE FROM emr_tags')
    for tag, description, lang, is_significant in emotions:
        cursor.execute(
            '''
            INSERT INTO emr_tags (tag, description, lang, is_significant)
            VALUES (?, ?, ?, ?)
            ''',
            (tag, description, lang, is_significant)
        )
    conn.commit()
    conn.close()
    print("Tabla de emociones inicializada con éxito.")

if __name__ == "main":
    main()