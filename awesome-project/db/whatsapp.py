from .connection import get_conn

def init_whatsapp_table():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            direction TEXT,
            text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_whatsapp_message(phone: str, direction: str, text: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO whatsapp_messages (phone, direction, text) VALUES (?, ?, ?)",
        (phone, direction, text)
    )
    conn.commit()
    conn.close()

def get_conversations():
    conn = get_conn()
    rows = conn.execute("""
        SELECT phone, text, timestamp FROM whatsapp_messages
        WHERE id IN (SELECT MAX(id) FROM whatsapp_messages GROUP BY phone)
        ORDER BY timestamp DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_messages(phone: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM whatsapp_messages WHERE phone = ? ORDER BY id ASC", (phone,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]