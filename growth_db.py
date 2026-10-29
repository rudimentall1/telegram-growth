"""SQLite storage for Telegram growth events."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "growth.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.execute("PRAGMA busy_timeout=10000")
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
    db.execute("""
        CREATE TABLE IF NOT EXISTS growth_members (
            user_id INTEGER PRIMARY KEY,
            invite_link TEXT,
            is_member INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS growth_events (
            update_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK(event_type IN ('join','leave')),
            event_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS growth_processed_updates (
            update_id INTEGER PRIMARY KEY,
            processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS growth_schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Run the legacy-event backfill once, not on every database connection.
    migrated = db.execute(
        "SELECT 1 FROM growth_schema_migrations WHERE version = 1"
    ).fetchone()
    if not migrated:
        db.execute("""
            INSERT OR IGNORE INTO growth_processed_updates(update_id)
            SELECT update_id FROM growth_events
        """)
        db.execute(
            "INSERT INTO growth_schema_migrations(version) VALUES (1)"
        )
    return db


def save_link(link, source, user_id):
    with connect() as db:
        db.execute(
            "INSERT INTO growth_links(invite_link, source, created_by) VALUES (?, ?, ?)",
            (link, source, user_id),
        )


def record_join(user_id, invite_link):
    """Compatibility helper for recording use of a known invite link."""
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


def record_member(update_id, user_id, invite_link, joined):
    """Record membership transitions, idempotently by Telegram update_id.

    A join is attributed only to the invite link included in that event. Missing or
    unknown links become 'unattributed' and clear prior current attribution. A leave
    uses the currently stored attribution. Duplicate update IDs do not mutate state.
    """
    with connect() as db:
        # Track every received update, including ignored state transitions. Otherwise
        # an ignored duplicate join could be replayed after a later leave and reactivate
        # the member incorrectly.
        already_processed = db.execute(
            "SELECT 1 FROM growth_processed_updates WHERE update_id = ?", (update_id,)
        ).fetchone()
        if already_processed:
            return
        db.execute(
            "INSERT INTO growth_processed_updates(update_id) VALUES (?)", (update_id,)
        )

        current = db.execute(
            "SELECT invite_link, is_member FROM growth_members WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        selected_link = None
        join_source = "unattributed"
        if invite_link:
            row = db.execute(
                "SELECT source FROM growth_links WHERE invite_link = ?", (invite_link,)
            ).fetchone()
            if row:
                selected_link = invite_link
                join_source = row[0]

        if joined:
            # Ignore duplicate/stale joins while the user is already a member.
            if current and current[1] == 1:
                return
            db.execute(
                "INSERT INTO growth_events(update_id,user_id,source,event_type) "
                "VALUES(?,?,?,'join')",
                (update_id, user_id, join_source),
            )
            db.execute(
                "INSERT INTO growth_members(user_id,invite_link,is_member,updated_at) "
                "VALUES(?,?,1,CURRENT_TIMESTAMP) "
                "ON CONFLICT(user_id) DO UPDATE SET "
                "invite_link=excluded.invite_link,is_member=1,updated_at=CURRENT_TIMESTAMP",
                (user_id, selected_link),
            )
            if selected_link:
                db.execute(
                    "INSERT OR IGNORE INTO growth_joins(user_id,invite_link) VALUES(?,?)",
                    (user_id, selected_link),
                )
        else:
            # Ignore stale/incomplete leave events for users not currently active.
            if not current or current[1] == 0:
                return
            previous_link = current[0]
            row = db.execute(
                "SELECT source FROM growth_links WHERE invite_link = ?", (previous_link,)
            ).fetchone() if previous_link else None
            leave_source = row[0] if row else "unattributed"
            db.execute(
                "INSERT INTO growth_events(update_id,user_id,source,event_type) "
                "VALUES(?,?,?,'leave')",
                (update_id, user_id, leave_source),
            )
            db.execute(
                "UPDATE growth_members SET is_member=0,invite_link=NULL,"
                "updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                (user_id,),
            )


def report():
    with connect() as db:
        return db.execute("""
            SELECT source,
                   SUM(CASE WHEN event_type='join' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN event_type='leave' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN event_type='join' THEN 1 ELSE -1 END)
            FROM growth_events
            GROUP BY source
            ORDER BY 4 DESC, 1
        """).fetchall()


def active_count():
    with connect() as db:
        return db.execute(
            "SELECT COUNT(*) FROM growth_members WHERE is_member=1"
        ).fetchone()[0]

def source_report(days=None):
    """Return event totals and currently active known members per source.

    If days is provided, joins/leaves are limited to that event window while the
    active count reflects current database state. Active counts are not a complete
    Telegram channel member count; they only cover members observed by this bot.
    """
    if days is not None:
        try:
            days = int(days)
        except (TypeError, ValueError) as exc:
            raise ValueError("days must be an integer between 1 and 3650") from exc
        if not 1 <= days <= 3650:
            raise ValueError("days must be an integer between 1 and 3650")

    with connect() as db:
        if days is None:
            event_rows = db.execute("""
                SELECT source,
                       SUM(CASE WHEN event_type='join' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN event_type='leave' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN event_type='join' THEN 1 ELSE -1 END)
                FROM growth_events
                GROUP BY source
            """).fetchall()
        else:
            event_rows = db.execute("""
                SELECT source,
                       SUM(CASE WHEN event_type='join' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN event_type='leave' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN event_type='join' THEN 1 ELSE -1 END)
                FROM growth_events
                WHERE event_at >= datetime('now', ?)
                GROUP BY source
            """, (f"-{days} days",)).fetchall()

        active_rows = db.execute("""
            SELECT COALESCE(l.source, 'unattributed') AS source, COUNT(*) AS active
            FROM growth_members AS m
            LEFT JOIN growth_links AS l ON l.invite_link = m.invite_link
            WHERE m.is_member = 1
            GROUP BY COALESCE(l.source, 'unattributed')
        """).fetchall()

    totals = {}
    for source, joins, leaves, net in event_rows:
        totals[source] = {
            "joins": int(joins or 0),
            "leaves": int(leaves or 0),
            "net": int(net or 0),
            "active": 0,
        }

    for source, active in active_rows:
        totals.setdefault(source, {"joins": 0, "leaves": 0, "net": 0, "active": 0})
        totals[source]["active"] = int(active or 0)

    return [
        (source, item["joins"], item["leaves"], item["net"], item["active"])
        for source, item in sorted(
            totals.items(),
            key=lambda row: (-row[1]["net"], -row[1]["active"], row[0]),
        )
    ]
