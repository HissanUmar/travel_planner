import json
from .connection import get_conn

REQUIRED_FIELDS = ["car_model", "car_variant", "car_year", "part_name", "spec", "genuine_pref"]

def init_requests_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS part_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mechanic_phone TEXT,
                car_model TEXT, car_variant TEXT, car_year TEXT,
                part_name TEXT, spec TEXT, genuine_pref TEXT,
                status TEXT DEFAULT 'COLLECTING_INFO',
                conversation TEXT DEFAULT '[]',
                has_unread INTEGER DEFAULT 0,
                pending_dealer_question TEXT DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for col, definition in [
            ("has_unread", "INTEGER DEFAULT 0"),
            ("pending_dealer_question", "TEXT DEFAULT NULL")
        ]:
            try:
                conn.execute(f"ALTER TABLE part_requests ADD COLUMN {col} {definition}")
            except Exception:
                pass

def mark_unread(request_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE part_requests SET has_unread = 1 WHERE id = ?", (request_id,))

def mark_read(request_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE part_requests SET has_unread = 0 WHERE id = ?", (request_id,))

def set_pending_dealer_question(request_id: int, thread_id: int, shop_name: str, question: str):
    payload = json.dumps({"thread_id": thread_id, "shop_name": shop_name, "question": question})
    with get_conn() as conn:
        conn.execute("UPDATE part_requests SET pending_dealer_question = ? WHERE id = ?", (payload, request_id))

def clear_pending_dealer_question(request_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE part_requests SET pending_dealer_question = NULL WHERE id = ?", (request_id,))

def get_open_request(phone: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM part_requests WHERE mechanic_phone = ? AND status IN ('COLLECTING_INFO', 'AWAITING_CONFIRMATION') ORDER BY id DESC LIMIT 1",
            (phone,)
        ).fetchone()
    return dict(row) if row else None

def create_request(phone: str):
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO part_requests (mechanic_phone) VALUES (?)", (phone,))
        req_id = cur.lastrowid
    return req_id

def append_conversation(request_id: int, role: str, text: str, msg_type: str = "text", thread_id: int = None):
    with get_conn() as conn:
        row = conn.execute("SELECT conversation FROM part_requests WHERE id = ?", (request_id,)).fetchone()
        convo = json.loads(row["conversation"])
        entry = {"role": role, "text": text, "type": msg_type}
        if thread_id is not None:
            entry["thread_id"] = thread_id
        convo.append(entry)
        conn.execute("UPDATE part_requests SET conversation = ? WHERE id = ?", (json.dumps(convo), request_id))

def update_fields(request_id: int, fields: dict):
    with get_conn() as conn:
        for key, value in fields.items():
            if key in REQUIRED_FIELDS and value:
                conn.execute(f"UPDATE part_requests SET {key} = ? WHERE id = ?", (value, request_id))

def set_status(request_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE part_requests SET status = ? WHERE id = ?", (status, request_id))

def get_request(request_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM part_requests WHERE id = ?", (request_id,)).fetchone()
    return dict(row) if row else None

def missing_fields(request: dict):
    return [f for f in REQUIRED_FIELDS if not request.get(f)]

def get_requests_for_phone(phone: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM part_requests WHERE mechanic_phone = ? ORDER BY id DESC", (phone,)
        ).fetchall()
    return [dict(r) for r in rows]

def get_all_requests():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM part_requests ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]