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

                CREATE TABLE IF NOT EXISTS target_review_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_id INTEGER NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
                    action TEXT NOT NULL CHECK(action IN ('approved','rejected','paused')),
                    promotion_policy TEXT NOT NULL,
                    permission_evidence TEXT,
                    recorded_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_target_review_history_target
                    ON target_review_history(target_id, id);

                CREATE TABLE IF NOT EXISTS drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft'
                        CHECK(status IN ('draft','approved','archived')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS source_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_chat_id INTEGER NOT NULL,
                    source_message_id INTEGER NOT NULL,
                    source_url TEXT,
                    draft_id INTEGER NOT NULL REFERENCES drafts(id),
                    captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source_chat_id, source_message_id)
                );

                CREATE TABLE IF NOT EXISTS target_invite_links (
                    target_id INTEGER PRIMARY KEY REFERENCES targets(id) ON DELETE CASCADE,
                    invite_link TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS publication_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    draft_id INTEGER NOT NULL REFERENCES drafts(id),
                    target_id INTEGER NOT NULL REFERENCES targets(id),
                    status TEXT NOT NULL CHECK(status IN ('sending','sent','failed','unknown')),
                    attempt_count INTEGER NOT NULL DEFAULT 1,
                    telegram_chat_id INTEGER,
                    telegram_message_id INTEGER,
                    message_url TEXT,
                    error TEXT,
                    started_at TEXT NOT NULL,
                    sent_at TEXT,
                    UNIQUE(draft_id, target_id)
                );

                CREATE TABLE IF NOT EXISTS source_moderation_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    draft_id INTEGER NOT NULL REFERENCES drafts(id),
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    decision TEXT NOT NULL CHECK(decision IN ('allow','hold','block','error')),
                    confidence REAL,
                    category TEXT,
                    reason TEXT NOT NULL,
                    raw_response TEXT,
                    reviewed_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_source_moderation_reviews_draft
                    ON source_moderation_reviews(draft_id, id);
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
        if not isinstance(item, dict):
            raise ValueError("catalog community must be an object")
        url = item.get("url") or item.get("evidence_url")
        handle = normalize_public_target(url)
        raw_kind = str(item.get("kind") or "").lower()
        kind = "channel" if "channel" in raw_kind else "group"
        target_id = self.add_target(kind, handle, item.get("rules_url"))
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
            db.execute(
                """INSERT INTO target_review_history(
                       target_id, action, promotion_policy, permission_evidence, recorded_at
                   ) VALUES (?, ?, ?, ?, ?)""",
                (target_id, status, promotion_policy,
                 evidence.strip() if evidence else None, reviewed_at),
            )

    def pause_target(self, target_id):
        from datetime import datetime, timezone

        recorded_at = datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            cur = db.execute(
                "UPDATE targets SET status='paused' WHERE id=?",
                (target_id,),
            )
            if cur.rowcount != 1:
                raise LookupError(f"target {target_id} not found")
            target = db.execute(
                "SELECT promotion_policy, permission_evidence FROM targets WHERE id=?",
                (target_id,),
            ).fetchone()
            db.execute(
                """INSERT INTO target_review_history(
                       target_id, action, promotion_policy, permission_evidence, recorded_at
                   ) VALUES (?, 'paused', ?, ?, ?)""",
                (target_id, target["promotion_policy"],
                 target["permission_evidence"], recorded_at),
            )

    def list_target_review_history(self, target_id):
        with self.connect() as db:
            rows = db.execute(
                """SELECT action, promotion_policy, permission_evidence, recorded_at
                   FROM target_review_history WHERE target_id=? ORDER BY id""",
                (target_id,),
            ).fetchall()
            return [dict(row) for row in rows]

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
            row = db.execute("""
                SELECT t.*, m.catalog_id, m.display_name, m.source_kind,
                       m.language, m.audience_topics_json,
                       m.publicly_stated_permission, m.observed_members,
                       m.source_checked_at, m.source_status, m.evidence_url, m.notes
                FROM targets t
                LEFT JOIN target_catalog_metadata m ON m.target_id=t.id
                WHERE t.id=?
            """, (target_id,)).fetchone()
            return dict(row) if row else None


    def capture_source_post(self, chat_id, message_id, title, body, source_url=None):
        """Create one reviewable draft per incoming source-channel post."""
        with self.connect() as db:
            existing = db.execute(
                "SELECT draft_id FROM source_posts WHERE source_chat_id=? AND source_message_id=?",
                (chat_id, message_id),
            ).fetchone()
            if existing:
                return existing["draft_id"], False
            cur = db.execute(
                "INSERT INTO drafts(title, body) VALUES (?, ?)",
                (title.strip()[:120] or f"Source post {message_id}", body.strip()),
            )
            draft_id = cur.lastrowid
            db.execute(
                "INSERT INTO source_posts(source_chat_id, source_message_id, source_url, draft_id) VALUES (?, ?, ?, ?)",
                (chat_id, message_id, source_url, draft_id),
            )
            return draft_id, True

    def record_moderation_review(self, draft_id, review):
        """Append an immutable moderation decision or retryable provider error."""
        from datetime import datetime, timezone

        decision = review.get("decision")
        if decision not in ("allow", "hold", "block", "error"):
            raise ValueError("invalid moderation decision")
        raw_response = review.get("raw_response")
        if raw_response is not None and not isinstance(raw_response, str):
            raw_response = json.dumps(raw_response, ensure_ascii=False)
        with self.connect() as db:
            cur = db.execute("""
                INSERT INTO source_moderation_reviews(
                    draft_id, provider, model, decision, confidence,
                    category, reason, raw_response, reviewed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(draft_id),
                str(review.get("provider") or "unknown")[:80],
                str(review.get("model") or "unknown")[:120],
                decision,
                review.get("confidence"),
                str(review.get("category") or "other")[:40],
                str(review.get("reason") or "No reason supplied")[:400],
                raw_response[:4000] if raw_response else None,
                datetime.now(timezone.utc).isoformat(),
            ))
            return cur.lastrowid

    def list_source_posts(self, limit=10):
        with self.connect() as db:
            rows = db.execute("""
                SELECT s.*, d.title, d.status AS draft_status,
                       r.provider AS moderation_provider,
                       r.model AS moderation_model,
                       r.decision AS moderation_decision,
                       r.confidence AS moderation_confidence,
                       r.category AS moderation_category,
                       r.reason AS moderation_reason,
                       r.reviewed_at AS moderation_reviewed_at
                FROM source_posts s
                JOIN drafts d ON d.id=s.draft_id
                LEFT JOIN source_moderation_reviews r
                  ON r.id=(
                    SELECT MAX(r2.id) FROM source_moderation_reviews r2
                    WHERE r2.draft_id=s.draft_id
                  )
                ORDER BY s.id DESC LIMIT ?
            """, (max(1, min(int(limit), 20)),)).fetchall()
            return [dict(row) for row in rows]

    def list_unprocessed_source_posts(self, limit=10):
        """Return source drafts not yet reviewed or sent; transient errors retry after ten minutes."""
        with self.connect() as db:
            rows = db.execute("""
                SELECT s.*, d.title, d.body, d.status AS draft_status
                FROM source_posts s JOIN drafts d ON d.id=s.draft_id
                WHERE d.status='draft'
                  AND NOT EXISTS (
                    SELECT 1 FROM publication_deliveries p WHERE p.draft_id=d.id
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM source_moderation_reviews r
                    WHERE r.draft_id=d.id
                      AND (
                        r.decision IN ('allow','hold','block')
                        OR (
                            r.decision='error'
                            AND julianday(r.reviewed_at) > julianday('now', '-10 minutes')
                        )
                      )
                  )
                ORDER BY s.id ASC LIMIT ?
            """, (max(1, min(int(limit), 20)),)).fetchall()
            return [dict(row) for row in rows]

    def get_or_create_target_invite(self, target_id, invite_link):
        """Persist a target-scoped community invite so retries reuse the same URL."""
        with self.connect() as db:
            row = db.execute(
                "SELECT invite_link FROM target_invite_links WHERE target_id=?",
                (target_id,),
            ).fetchone()
            if row:
                return row["invite_link"], False
            db.execute(
                "INSERT INTO target_invite_links(target_id, invite_link) VALUES (?, ?)",
                (target_id, invite_link),
            )
            return invite_link, True

    def get_target_invite(self, target_id):
        with self.connect() as db:
            row = db.execute(
                "SELECT invite_link FROM target_invite_links WHERE target_id=?",
                (target_id,),
            ).fetchone()
            return row["invite_link"] if row else None

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

    def claim_delivery(self, draft_id, target_id):
        """Atomically claim one delivery; sent/unknown/in-flight rows never auto-repeat."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            existing = db.execute(
                "SELECT status FROM publication_deliveries WHERE draft_id=? AND target_id=?",
                (draft_id, target_id),
            ).fetchone()
            if existing is None:
                db.execute(
                    """INSERT INTO publication_deliveries(
                           draft_id, target_id, status, attempt_count, started_at
                       ) VALUES (?, ?, 'sending', 1, ?)""",
                    (draft_id, target_id, now),
                )
                return True
            if existing["status"] != "failed":
                return False
            db.execute(
                """UPDATE publication_deliveries
                   SET status='sending', attempt_count=attempt_count+1,
                       started_at=?, error=NULL
                   WHERE draft_id=? AND target_id=? AND status='failed'""",
                (now, draft_id, target_id),
            )
            return db.execute("SELECT changes()").fetchone()[0] == 1

    def mark_delivery_sent(self, draft_id, target_id, chat_id, message_id, message_url=None):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            cur = db.execute(
                """UPDATE publication_deliveries
                   SET status='sent', telegram_chat_id=?, telegram_message_id=?,
                       message_url=?, sent_at=?, error=NULL
                   WHERE draft_id=? AND target_id=? AND status='sending'""",
                (chat_id, message_id, message_url, now, draft_id, target_id),
            )
            if cur.rowcount != 1:
                raise RuntimeError("delivery claim was lost before sent status could be recorded")
            db.execute(
                "UPDATE targets SET last_posted_at=? WHERE id=?",
                (now, target_id),
            )

    def mark_delivery_failed(self, draft_id, target_id, error):
        with self.connect() as db:
            db.execute(
                """UPDATE publication_deliveries
                   SET status='failed', error=?
                   WHERE draft_id=? AND target_id=? AND status='sending'""",
                (str(error)[:1000], draft_id, target_id),
            )

    def mark_delivery_unknown(self, draft_id, target_id, error):
        """Ambiguous network outcome is never retried automatically to avoid duplicates."""
        with self.connect() as db:
            db.execute(
                """UPDATE publication_deliveries
                   SET status='unknown', error=?
                   WHERE draft_id=? AND target_id=? AND status='sending'""",
                (str(error)[:1000], draft_id, target_id),
            )

    def get_delivery(self, draft_id, target_id):
        with self.connect() as db:
            row = db.execute(
                """SELECT * FROM publication_deliveries
                   WHERE draft_id=? AND target_id=?""",
                (draft_id, target_id),
            ).fetchone()
            return dict(row) if row else None

    def list_deliveries(self, draft_id):
        with self.connect() as db:
            rows = db.execute(
                """SELECT d.*, t.handle FROM publication_deliveries d
                   JOIN targets t ON t.id=d.target_id
                   WHERE d.draft_id=? ORDER BY d.id""",
                (draft_id,),
            ).fetchall()
            return [dict(row) for row in rows]
