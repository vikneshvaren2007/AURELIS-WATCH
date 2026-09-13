import sqlite3
import os
from contextlib import contextmanager
from backend.config import Config

DB_PATH = Config.DATABASE_URL
if DB_PATH.startswith("sqlite:///"):
    DB_PATH = DB_PATH.replace("sqlite:///", "")

def get_db_connection():
    """Returns a SQLite connection with Row factory enabled for dict-like access."""
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def dict_from_row(row):
    """Utility to convert a sqlite3.Row to standard python dict."""
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}

def dicts_from_rows(rows):
    return [dict_from_row(r) for r in rows]
