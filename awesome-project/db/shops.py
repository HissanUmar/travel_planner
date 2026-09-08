import csv
from .connection import get_conn

def init_shops_table():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            parts TEXT
        )
    """)
    conn.commit()
    conn.close()

def load_shops_from_csv(path="shops.csv"):
    conn = get_conn()
    conn.execute("DELETE FROM shops")
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute(
                "INSERT INTO shops (name, phone, parts) VALUES (?, ?, ?)",
                (row["name"], row["phone"], row["parts"])
            )
    conn.commit()
    conn.close()

def find_shop_for_part(part: str):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM shops").fetchall()
    conn.close()
    for row in rows:
        if part.lower() in row["parts"].lower():
            return dict(row)
    return None