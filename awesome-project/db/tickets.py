from .connection import get_conn

def init_tickets_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                dealer_thread_id INTEGER,
                shop_name TEXT,
                shop_phone TEXT,
                final_price REAL,
                is_genuine TEXT,
                status TEXT DEFAULT 'CREATED',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

def create_ticket(request_id: int, thread: dict):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tickets (request_id, dealer_thread_id, shop_name, shop_phone, final_price, is_genuine) VALUES (?, ?, ?, ?, ?, ?)",
            (request_id, thread["id"], thread["shop_name"], thread["shop_phone"], thread["price"], thread["is_genuine"])
        )
        ticket_id = cur.lastrowid
    return ticket_id

def get_ticket_for_request(request_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE request_id = ? ORDER BY id DESC LIMIT 1", (request_id,)).fetchone()
    return dict(row) if row else None