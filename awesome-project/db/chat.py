from .connection import get_conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_message TEXT,
                bot_response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_message(user_message: str, bot_response: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO history (user_message, bot_response) VALUES (?, ?)",
            (user_message, bot_response)
        )


def get_history():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM history ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]


def get_recent_history(limit: int = 10):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in reversed(rows)]