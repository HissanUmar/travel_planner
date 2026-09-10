import csv
from .connection import get_conn

def init_shops_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                parts TEXT
            )
        """)

def load_shops_from_csv(path="shops.csv"):
    with get_conn() as conn:
        conn.execute("DELETE FROM shops")
        with open(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                conn.execute(
                    "INSERT INTO shops (name, phone, parts) VALUES (?, ?, ?)",
                    (row["name"], row["phone"], row["parts"])
                )

def get_shop_by_phone(phone: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM shops WHERE phone = ?", (phone,)).fetchone()
    return dict(row) if row else None

def find_shop_for_part(part: str):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM shops").fetchall()
    for row in rows:
        if part.lower() in row["parts"].lower():
            return dict(row)
    return None

def find_shops_for_part(part: str):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM shops").fetchall()
    return [dict(row) for row in rows if part.lower() in row["parts"].lower()]