import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join("db_data", "chat.db")

@contextmanager
def get_conn():
    os.makedirs("db_data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return conn
