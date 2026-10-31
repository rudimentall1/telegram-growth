"""SQLite persistence isolated from the legacy growth database."""
import json
import sqlite3
from pathlib import Path
from typing import Optional

from .links import normalize_public_target


DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "publisher.db"


class PublisherStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        db = sqlite3.connect(str(self.db_path), timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def initialize(self):
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL CHECK(kind IN ('group','channel')),
                    handle TEXT NOT NULL UNIQUE,
                    rules_url TEXT,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending','approved','rejected','paused')),
                    promotion_policy TEXT NOT NULL DEFAULT 'unknown'
                        CHECK(promotion_policy IN ('unknown','allowed','approval_required','prohibited')),
                    permission_evidence TEXT,
                    reviewed_at TEXT,
                    last_posted_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS target_catalog_metadata (
                    target_id INTEGER PRIMARY KEY REFERENCES targets(id) ON DELETE CASCADE,
                    catalog_id TEXT,
                    display_name TEXT,
                    source_kind TEXT,
                    language TEXT,
                    audience_topics_json TEXT,
                    publicly_stated_permission TEXT,
                    observed_members INTEGER,
                    source_checked_at TEXT,
                    source_status TEXT,
                    evidence_url TEXT,
                    notes TEXT
                );

                CREATE TABLE IF NOT EXISTS drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft'
                        CHECK(status IN ('draft','approved','archived')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def add_target(self, kind, handle, rules_url=None):
        if kind not in ("group", "channel"):
            raise ValueError("kind must be group or channel")
        handle = normalize_public_target(handle)
        with self.connect() as db:
            existing = db.execute("SELECT id FROM targets WHERE handle=?", (handle,)).fetchone()
            if existing:
                return existing["id"]
            cur = db.execute(
                "INSERT INTO targets(kind, handle, rules_url) VALUES (?, ?, ?)",
                (kind, handle, rules_url or None),
            )
            return cur.lastrowid

    def import_catalog_community(self, item):
        url = item.get("url") or item.get("evidence_url")
        handle = normalize_public_target(url)
        raw_kind = str(item.get("kind") or "").lower()
        kind = "channel" if "channel" in raw_kind else "group"
        target_id = self.add_target(kind, handle, item.get("evidence_url") or url)
        with self.connect() as db:
            db.execute("""
                INSERT INTO target_catalog_metadata (
                    target_id, catalog_id, display_name, source_kind, language,
                    audience_topics_json, publicly_stated_permission,
                    observed_members, source_checked_at, source_status,
                    evidence_url, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(target_id) DO UPDATE SET
                    catalog_id=excluded.catalog_id,
                    display_name=excluded.display_name,
                    source_kind=excluded.source_kind,
                    language=excluded.language,
                    audience_topics_json=excluded.audience_topics_json,
                    publicly_stated_permission=excluded.publicly_stated_permission,
                    observed_members=excluded.observed_members,
                    source_checked_at=excluded.source_checked_at,
                    source_status=excluded.source_status,
                    evidence_url=excluded.evidence_url,
                    notes=excluded.notes
            """, (
                target_id, item.get("id"), item.get("name"), item.get("kind"),
                item.get("language"),
                json.dumps(item.get("audience_topics") or [], ensure_ascii=False),
                item.get("publicly_stated_permission"),
                item.get("observed_members"), item.get("checked_at"),
                item.get("automation_status"), item.get("evidence_url"),
                item.get("notes"),
            ))
        return target_id

    def review_target(self, target_id, decision, promotion_policy, evidence):
        from datetime import datetime, timezone

        if decision not in ("approve", "reject"):
            raise ValueError("decision must be approve or reject")
        if promotion_policy not in ("allowed", "approval_required", "prohibited", "unknown"):
            raise ValueError("invalid promotion policy")
        if decision == "approve" and promotion_policy != "allowed":
            raise ValueError("only targets with explicitly allowed promotion can be approved")
        if decision == "approve" and not (evidence and evidence.strip()):
            raise ValueError("permission evidence is required for approval")

        status = "approved" if decision == "approve" else "rejected"
        reviewed_at = datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            cur = db.execute(
                """UPDATE targets
                   SET status=?, promotion_policy=?, permission_evidence=?, reviewed_at=?
                   WHERE id=?""",
                (status, promotion_policy, evidence.strip() if evidence else None,
                 reviewed_at, target_id),
            )
            if cur.rowcount != 1:
                raise LookupError(f"target {target_id} not found")

    def list_targets(self):
        with self.connect() as db:
            rows = db.execute("""
                SELECT t.*, m.catalog_id, m.display_name, m.source_kind,
                       m.language, m.audience_topics_json,
                       m.publicly_stated_permission, m.observed_members,
                       m.source_checked_at, m.source_status, m.evidence_url, m.notes
                FROM targets t
                LEFT JOIN target_catalog_metadata m ON m.target_id=t.id
                ORDER BY t.id
            """).fetchall()
            return [dict(row) for row in rows]

    def get_target(self, target_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM targets WHERE id=?", (target_id,)).fetchone()
            return dict(row) if row else None

    def add_draft(self, title, body):
        if not title.strip() or not body.strip():
            raise ValueError("draft title and body must not be empty")
        with self.connect() as db:
            cur = db.execute(
                "INSERT INTO drafts(title, body) VALUES (?, ?)",
                (title.strip(), body.strip()),
            )
            return cur.lastrowid

    def approve_draft(self, draft_id):
        with self.connect() as db:
            cur = db.execute(
                "UPDATE drafts SET status='approved' WHERE id=? AND status='draft'",
                (draft_id,),
            )
            if cur.rowcount != 1:
                raise LookupError(f"draft {draft_id} not found or not in draft status")

    def get_draft(self, draft_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
            return dict(row) if row else None
