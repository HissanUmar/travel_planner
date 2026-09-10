import json
from .connection import get_conn

def init_dealer_threads_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dealer_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                shop_id INTEGER,
                shop_name TEXT,
                shop_phone TEXT,
                status TEXT DEFAULT 'CONTACTED',
                is_genuine TEXT,
                price REAL,
                notes TEXT,
                conversation TEXT DEFAULT '[]',
                last_outbound_msg_id TEXT,
                contacted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                replied_at DATETIME
            )
        """)

def create_thread(request_id: int, shop: dict, outreach_message: str):
    initial_convo = json.dumps([{"role": "llm", "text": outreach_message}])
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO dealer_threads (request_id, shop_id, shop_name, shop_phone, conversation) VALUES (?, ?, ?, ?, ?)",
            (request_id, shop["id"], shop["name"], shop["phone"], initial_convo)
        )
        thread_id = cur.lastrowid
    return thread_id

def append_thread_conversation(thread_id: int, role: str, text: str):
    with get_conn() as conn:
        row = conn.execute("SELECT conversation FROM dealer_threads WHERE id = ?", (thread_id,)).fetchone()
        convo = json.loads(row["conversation"])
        convo.append({"role": role, "text": text})
        conn.execute("UPDATE dealer_threads SET conversation = ? WHERE id = ?", (json.dumps(convo), thread_id))

def get_open_thread_by_phone(phone: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM dealer_threads WHERE shop_phone = ? AND status != 'CLOSED' ORDER BY id DESC LIMIT 1",
            (phone,)
        ).fetchone()
    return dict(row) if row else None

def update_thread(thread_id: int, **fields):
    with get_conn() as conn:
        for key, value in fields.items():
            conn.execute(f"UPDATE dealer_threads SET {key} = ? WHERE id = ?", (value, thread_id))

def get_threads_for_request(request_id: int):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM dealer_threads WHERE request_id = ?", (request_id,)).fetchall()
    return [dict(r) for r in rows]

def set_last_outbound_msg_id(thread_id: int, wamid: str):
    with get_conn() as conn:
        conn.execute("UPDATE dealer_threads SET last_outbound_msg_id = ? WHERE id = ?", (wamid, thread_id))

def get_stale_threads(hours: int = 6):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM dealer_threads
            WHERE status = 'CONTACTED'
            AND replied_at IS NULL
            AND contacted_at < datetime('now', ?)
        """, (f'-{hours} hours',)).fetchall()
    return [dict(r) for r in rows]

def close_stale_thread(thread_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE dealer_threads SET status = 'NO_RESPONSE' WHERE id = ?", (thread_id,))