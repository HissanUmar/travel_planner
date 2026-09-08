import sqlite3
import os

DB_PATH = os.path.join("db_data", "chat.db")  # renamed folder to avoid clashing with db/ package

def get_conn():
    os.makedirs("db_data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn