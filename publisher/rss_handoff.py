"""Reliable handoff from the legacy RSS sender to Publisher's review queue.

A Telegram send is already committed before this function runs. If the shared
Publisher database is temporarily unavailable, preserve the record in a
JSONL outbox and retry it during the next RSS cron run.
"""
import json
import os
from pathlib import Path

from .storage import PublisherStore


DEFAULT_OUTBOX = Path(__file__).resolve().parent.parent / "data" / "publisher_outbox.jsonl"


def _record(chat_id, message_id, text, source_url):
    body = str(text or "").strip()
    first_line = next((line.strip() for line in body.splitlines() if line.strip()), "")
    if not body or not first_line:
        raise ValueError("published Telegram message has no text")
    return {
        "chat_id": int(chat_id),
        "message_id": int(message_id),
        "title": first_line[:120],
        "body": body,
        "source_url": str(source_url) if source_url else None,
    }


def _append_outbox(record, outbox_path):
    path = Path(outbox_path) if outbox_path else DEFAULT_OUTBOX
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def enqueue_published_post(chat_id, message_id, text, source_url=None,
                           db_path=None, outbox_path=None):
    """Insert a successful Telegram send idempotently, or persist it for retry."""
    record = _record(chat_id, message_id, text, source_url)
    try:
        store = PublisherStore(str(db_path)) if db_path else PublisherStore()
        draft_id, created = store.capture_source_post(
            record["chat_id"], record["message_id"], record["title"],
            record["body"], record["source_url"],
        )
        return {
            "status": "queued" if created else "duplicate",
            "draft_id": int(draft_id),
        }
    except Exception as exc:
        _append_outbox(record, outbox_path)
        return {"status": "spooled", "error": str(exc)[:240]}


def flush_pending_publisher_posts(db_path=None, outbox_path=None):
    """Replay the durable JSONL outbox; keep records whose DB insert still fails."""
    path = Path(outbox_path) if outbox_path else DEFAULT_OUTBOX
    if not path.exists():
        return {"processed": 0, "remaining": 0}
    try:
        store = PublisherStore(str(db_path)) if db_path else PublisherStore()
    except Exception as exc:
        return {"processed": 0, "remaining": sum(1 for _ in path.open(encoding="utf-8")),
                "error": str(exc)[:240]}

    processed = 0
    pending = []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                record = _record(
                    item["chat_id"], item["message_id"], item["body"],
                    item.get("source_url"),
                )
                store.capture_source_post(
                    record["chat_id"], record["message_id"], record["title"],
                    record["body"], record["source_url"],
                )
                processed += 1
            except Exception:
                pending.append(line if line.endswith("\n") else line + "\n")

    if pending:
        temporary = path.with_suffix(path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            stream.writelines(pending)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    else:
        path.unlink(missing_ok=True)
    return {"processed": processed, "remaining": len(pending)}
