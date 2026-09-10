from .connection import get_conn

def init_whatsapp_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT,
                direction TEXT,
                text TEXT,
                msg_id TEXT UNIQUE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

def save_whatsapp_message(phone: str, direction: str, text: str, msg_id: str = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO whatsapp_messages (phone, direction, text, msg_id) VALUES (?, ?, ?, ?)",
            (phone, direction, text, msg_id)
        )

def message_already_processed(msg_id: str):
    if not msg_id:
        return False
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM whatsapp_messages WHERE msg_id = ?", (msg_id,)).fetchone()
    return row is not None

def get_conversations():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT phone, text, timestamp FROM whatsapp_messages
            WHERE id IN (SELECT MAX(id) FROM whatsapp_messages GROUP BY phone)
            ORDER BY timestamp DESC
        """).fetchall()
    return [dict(r) for r in rows]

def get_messages(phone: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM whatsapp_messages WHERE phone = ? ORDER BY id ASC", (phone,)
        ).fetchall()
    return [dict(r) for r in rows]