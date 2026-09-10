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
                pending_mechanic_question TEXT DEFAULT NULL,
                alternative_offer TEXT DEFAULT NULL,
                contacted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                replied_at DATETIME
            )
        """)
        for col, definition in [
            ("pending_mechanic_question", "TEXT DEFAULT NULL"),
            ("alternative_offer", "TEXT DEFAULT NULL")
        ]:
            try:
                conn.execute(f"ALTER TABLE dealer_threads ADD COLUMN {col} {definition}")
            except Exception:
                pass

def create_thread(request_id: int, shop: dict, outreach_message: str):
    initial_convo = json.dumps([{"role": "llm", "text": outreach_message, "type": "text"}])
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO dealer_threads (request_id, shop_id, shop_name, shop_phone, conversation) VALUES (?, ?, ?, ?, ?)",
            (request_id, shop["id"], shop["name"], shop["phone"], initial_convo)
        )
        thread_id = cur.lastrowid
    return thread_id

def append_thread_conversation(thread_id: int, role: str, text: str, msg_type: str = "text"):
    with get_conn() as conn:
        row = conn.execute("SELECT conversation FROM dealer_threads WHERE id = ?", (thread_id,)).fetchone()
        convo = json.loads(row["conversation"])
        convo.append({"role": role, "text": text, "type": msg_type})
        conn.execute("UPDATE dealer_threads SET conversation = ? WHERE id = ?", (json.dumps(convo), thread_id))

def get_open_thread_by_phone(phone: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM dealer_threads WHERE shop_phone = ? AND status != 'CLOSED' ORDER BY id DESC LIMIT 1",
            (phone,)
        ).fetchone()
    return dict(row) if row else None

def get_thread(thread_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM dealer_threads WHERE id = ?", (thread_id,)).fetchone()
    return dict(row) if row else None

def update_thread(thread_id: int, **fields):
    with get_conn() as conn:
        for key, value in fields.items():
            conn.execute(f"UPDATE dealer_threads SET {key} = ? WHERE id = ?", (value, thread_id))

def set_pending_mechanic_question(thread_id: int, question: str):
    with get_conn() as conn:
        conn.execute("UPDATE dealer_threads SET pending_mechanic_question = ?, status = 'AWAITING_MECHANIC_INPUT' WHERE id = ?", (question, thread_id))

def clear_pending_mechanic_question(thread_id: int, revert_status: str):
    with get_conn() as conn:
        conn.execute("UPDATE dealer_threads SET pending_mechanic_question = NULL, status = ? WHERE id = ?", (revert_status, thread_id))

def set_alternative_offer(thread_id: int, offer: dict):
    with get_conn() as conn:
        conn.execute("UPDATE dealer_threads SET alternative_offer = ? WHERE id = ?", (json.dumps(offer), thread_id))

def get_threads_for_request(request_id: int):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM dealer_threads WHERE request_id = ?", (request_id,)).fetchall()
    return [dict(r) for r in rows]

def close_other_threads(request_id: int, except_thread_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM dealer_threads WHERE request_id = ? AND id != ? AND status NOT IN ('CLOSED', 'REJECTED')",
            (request_id, except_thread_id)
        ).fetchall()
        for row in rows:
            conn.execute("UPDATE dealer_threads SET status = 'CLOSED' WHERE id = ?", (row["id"],))
    return [dict(r) for r in rows]

def get_stale_threads(hours: int = 6):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM dealer_threads
            WHERE status IN ('CONTACTED', 'AWAITING_MECHANIC_INPUT')
            AND replied_at IS NULL
            AND contacted_at < datetime('now', ?)
        """, (f'-{hours} hours',)).fetchall()
    return [dict(r) for r in rows]

def close_stale_thread(thread_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE dealer_threads SET status = 'NO_RESPONSE' WHERE id = ?", (thread_id,))