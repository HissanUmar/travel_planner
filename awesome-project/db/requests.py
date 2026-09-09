import json
from .connection import get_conn

REQUIRED_FIELDS = ["car_model", "car_variant", "car_year", "part_name", "spec", "genuine_pref"]

def init_requests_table():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS part_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mechanic_phone TEXT,
            car_model TEXT, car_variant TEXT, car_year TEXT,
            part_name TEXT, spec TEXT, genuine_pref TEXT,
            status TEXT DEFAULT 'COLLECTING_INFO',
            conversation TEXT DEFAULT '[]',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_open_request(phone: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM part_requests WHERE mechanic_phone = ? AND status = 'COLLECTING_INFO' ORDER BY id DESC LIMIT 1",
        (phone,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def create_request(phone: str):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO part_requests (mechanic_phone) VALUES (?)", (phone,)
    )
    conn.commit()
    req_id = cur.lastrowid
    conn.close()
    return req_id

def append_conversation(request_id: int, role: str, text: str):
    conn = get_conn()
    row = conn.execute("SELECT conversation FROM part_requests WHERE id = ?", (request_id,)).fetchone()
    convo = json.loads(row["conversation"])
    convo.append({"role": role, "text": text})
    conn.execute(
        "UPDATE part_requests SET conversation = ? WHERE id = ?",
        (json.dumps(convo), request_id)
    )
    conn.commit()
    conn.close()

def update_fields(request_id: int, fields: dict):
    conn = get_conn()
    for key, value in fields.items():
        if key in REQUIRED_FIELDS and value:
            conn.execute(f"UPDATE part_requests SET {key} = ? WHERE id = ?", (value, request_id))
    conn.commit()
    conn.close()

def set_status(request_id: int, status: str):
    conn = get_conn()
    conn.execute("UPDATE part_requests SET status = ? WHERE id = ?", (status, request_id))
    conn.commit()
    conn.close()

def get_request(request_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM part_requests WHERE id = ?", (request_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def missing_fields(request: dict):
    return [f for f in REQUIRED_FIELDS if not request.get(f)]