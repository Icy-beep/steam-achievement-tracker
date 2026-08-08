import sqlite3

from .config import DB_FILE
from .game_data import POPULAR_GAMES


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS games_list (
            id INTEGER PRIMARY KEY,
            app_id VARCHAR NOT NULL UNIQUE,
            core_name VARCHAR NOT NULL,
            volume VARCHAR,
            subtitle VARCHAR
        )"""
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_list_core_name ON games_list (core_name)")
    conn.commit()
    conn.close()


def build_full_name(core_name, volume=None, subtitle=None):
    name = f"{core_name} {volume}".strip() if volume else core_name
    if subtitle:
        name += f": {subtitle}"
    return name


def add_game_to_db(app_id, core_name, volume=None, subtitle=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO games_list (app_id, core_name, volume, subtitle) VALUES (?, ?, ?, ?)",
            (app_id, core_name, volume, subtitle),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def delete_game_from_db(game_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM games_list WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()


def search_games(query):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    like_query = f"%{query}%"
    cursor.execute(
        """SELECT id, app_id, core_name, volume, subtitle
           FROM games_list
           WHERE (core_name || COALESCE(' ' || volume, '') || COALESCE(' ' || subtitle, '')) LIKE ?
           ORDER BY core_name, volume
           LIMIT 100""",
        (like_query,),
    )
    results = cursor.fetchall()
    conn.close()
    return results


def get_all_games():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, app_id, core_name, volume, subtitle FROM games_list ORDER BY core_name, volume")
    results = cursor.fetchall()
    conn.close()
    return results


def get_game_by_app_id(app_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, app_id, core_name, volume, subtitle FROM games_list WHERE app_id = ?", (app_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def import_builtin_popular_games():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    added = 0
    for app_id, core_name, volume, subtitle in POPULAR_GAMES:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO games_list (app_id, core_name, volume, subtitle) VALUES (?, ?, ?, ?)",
                (app_id, core_name, volume, subtitle),
            )
            if cursor.rowcount > 0:
                added += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return added, f"Добавлено {added} популярных игр (работает без интернета!)"
