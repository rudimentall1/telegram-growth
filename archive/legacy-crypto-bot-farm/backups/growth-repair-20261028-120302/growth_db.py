import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "growth.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def connect():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS growth_links (
            invite_link TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS growth_joins (
            user_id INTEGER NOT NULL,
            invite_link TEXT NOT NULL,
            joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, invite_link)
        )
    """)
    return db

def save_link(link, source, user_id):
    with connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO growth_links(invite_link, source, created_by) VALUES (?, ?, ?)",
            (link, source, user_id),
        )

def record_join(user_id, invite_link):
    if not invite_link:
        return
    with connect() as db:
        known = db.execute(
            "SELECT 1 FROM growth_links WHERE invite_link = ?", (invite_link,)
        ).fetchone()
        if known:
            db.execute(
                "INSERT OR IGNORE INTO growth_joins(user_id, invite_link) VALUES (?, ?)",
                (user_id, invite_link),
            )

def report():
    with connect() as db:
        return db.execute("""
            SELECT l.source, COUNT(DISTINCT j.user_id)
            FROM growth_links l
            LEFT JOIN growth_joins j ON j.invite_link = l.invite_link
            GROUP BY l.invite_link
            ORDER BY l.created_at DESC
        """).fetchall()
