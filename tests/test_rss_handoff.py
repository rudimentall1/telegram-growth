import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from publisher.rss_handoff import enqueue_published_post, flush_pending_publisher_posts
from publisher.storage import PublisherStore


class PublisherRssHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.db_path = root / "publisher.db"
        self.outbox_path = root / "publisher_outbox.jsonl"
        self.store = PublisherStore(str(self.db_path))

    def tearDown(self):
        self.tmp.cleanup()

    def test_successful_send_is_queued_idempotently(self):
        body = "🪂 Новость о Web3\n\nОригинал: Example\nhttps://example.com/story"
        first = enqueue_published_post(
            -100123, 456, body, "https://t.me/cryptoping_ru/456",
            db_path=self.db_path, outbox_path=self.outbox_path,
        )
        second = enqueue_published_post(
            -100123, 456, body, "https://t.me/cryptoping_ru/456",
            db_path=self.db_path, outbox_path=self.outbox_path,
        )

        self.assertEqual(first["status"], "queued")
        self.assertEqual(second["status"], "duplicate")
        self.assertEqual(len(self.store.list_source_posts()), 1)
        self.assertFalse(self.outbox_path.exists())

    def test_database_failure_spools_then_replays_to_publisher(self):
        body = "Новость о крипторынке\nhttps://example.com/story"
        with patch("publisher.rss_handoff.PublisherStore", side_effect=RuntimeError("db offline")):
            result = enqueue_published_post(
                -100123, 789, body, "https://t.me/cryptoping_ru/789",
                db_path=self.db_path, outbox_path=self.outbox_path,
            )

        self.assertEqual(result["status"], "spooled")
        record = json.loads(self.outbox_path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(record["message_id"], 789)

        replay = flush_pending_publisher_posts(
            db_path=self.db_path, outbox_path=self.outbox_path,
        )
        self.assertEqual(replay, {"processed": 1, "remaining": 0})
        self.assertEqual(len(self.store.list_source_posts()), 1)
        self.assertFalse(self.outbox_path.exists())

    def test_existing_source_post_is_not_duplicated_when_outbox_replays(self):
        self.store.capture_source_post(
            -100123, 999, "Existing title", "Existing body",
            "https://t.me/cryptoping_ru/999",
        )
        self.outbox_path.write_text(
            json.dumps({
                "chat_id": -100123,
                "message_id": 999,
                "title": "Existing title",
                "body": "Existing body",
                "source_url": "https://t.me/cryptoping_ru/999",
            }) + "\n",
            encoding="utf-8",
        )

        replay = flush_pending_publisher_posts(
            db_path=self.db_path, outbox_path=self.outbox_path,
        )
        self.assertEqual(replay, {"processed": 1, "remaining": 0})
        self.assertEqual(len(self.store.list_source_posts()), 1)


if __name__ == "__main__":
    unittest.main()
