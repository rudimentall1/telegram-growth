import tempfile
import unittest
from pathlib import Path

import growth_db


class GrowthDbTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_db_path = growth_db.DB_PATH
        growth_db.DB_PATH = Path(self.temp.name) / "growth.db"
        with growth_db.connect() as db:
            db.executemany(
                "INSERT INTO growth_links(invite_link, source, created_by) VALUES (?, ?, ?)",
                [
                    ("https://t.me/+campaignA", "campaign_a", 1),
                    ("https://t.me/+campaignB", "campaign_b", 1),
                ],
            )

    def tearDown(self):
        growth_db.DB_PATH = self.original_db_path
        self.temp.cleanup()

    def test_join_uses_known_source_and_counts_active_member(self):
        growth_db.record_member(1, 101, "https://t.me/+campaignA", True)
        self.assertEqual(growth_db.report(), [("campaign_a", 1, 0, 1)])
        self.assertEqual(growth_db.active_count(), 1)

    def test_leave_is_attributed_to_current_source(self):
        growth_db.record_member(1, 101, "https://t.me/+campaignA", True)
        growth_db.record_member(2, 101, None, False)
        self.assertEqual(growth_db.report(), [("campaign_a", 1, 1, 0)])
        self.assertEqual(growth_db.active_count(), 0)

    def test_rejoin_without_link_does_not_reuse_old_source(self):
        growth_db.record_member(1, 101, "https://t.me/+campaignA", True)
        growth_db.record_member(2, 101, None, False)
        growth_db.record_member(3, 101, None, True)
        growth_db.record_member(4, 101, None, False)
        report = {row[0]: row[1:] for row in growth_db.report()}
        self.assertEqual(report["campaign_a"], (1, 1, 0))
        self.assertEqual(report["unattributed"], (1, 1, 0))
        self.assertEqual(growth_db.active_count(), 0)

    def test_rejoin_via_another_campaign_updates_current_source(self):
        growth_db.record_member(1, 101, "https://t.me/+campaignA", True)
        growth_db.record_member(2, 101, None, False)
        growth_db.record_member(3, 101, "https://t.me/+campaignB", True)
        growth_db.record_member(4, 101, None, False)
        report = {row[0]: row[1:] for row in growth_db.report()}
        self.assertEqual(report["campaign_a"], (1, 1, 0))
        self.assertEqual(report["campaign_b"], (1, 1, 0))

    def test_duplicate_update_id_does_not_double_count(self):
        growth_db.record_member(1, 101, "https://t.me/+campaignA", True)
        growth_db.record_member(1, 101, "https://t.me/+campaignA", True)
        self.assertEqual(growth_db.report(), [("campaign_a", 1, 0, 1)])
        self.assertEqual(growth_db.active_count(), 1)

    def test_replayed_old_join_cannot_reactivate_member_after_leave(self):
        growth_db.record_member(1, 101, "https://t.me/+campaignA", True)
        growth_db.record_member(2, 101, None, False)
        growth_db.record_member(1, 101, "https://t.me/+campaignA", True)
        self.assertEqual(growth_db.report(), [("campaign_a", 1, 1, 0)])
        self.assertEqual(growth_db.active_count(), 0)

    def test_ignored_duplicate_join_cannot_reactivate_after_leave(self):
        growth_db.record_member(1, 101, "https://t.me/+campaignA", True)
        # Duplicate transition while already active is ignored but marked processed.
        growth_db.record_member(2, 101, "https://t.me/+campaignB", True)
        growth_db.record_member(3, 101, None, False)
        # A replay of that previously ignored update must not reactivate the member.
        growth_db.record_member(2, 101, "https://t.me/+campaignB", True)
        self.assertEqual(growth_db.report(), [("campaign_a", 1, 1, 0)])
        self.assertEqual(growth_db.active_count(), 0)

    def test_unknown_invite_is_unattributed(self):
        growth_db.record_member(1, 101, "https://t.me/+campaignA", True)
        growth_db.record_member(2, 101, None, False)
        growth_db.record_member(3, 101, "https://t.me/+unknown", True)
        growth_db.record_member(4, 101, None, False)
        report = {row[0]: row[1:] for row in growth_db.report()}
        self.assertEqual(report["campaign_a"], (1, 1, 0))
        self.assertEqual(report["unattributed"], (1, 1, 0))

    def test_duplicate_join_transition_does_not_inflate_events(self):
        growth_db.record_member(1, 101, "https://t.me/+campaignA", True)
        growth_db.record_member(2, 101, "https://t.me/+campaignB", True)
        self.assertEqual(growth_db.report(), [("campaign_a", 1, 0, 1)])
        self.assertEqual(growth_db.active_count(), 1)

    def test_legacy_event_ids_are_backfilled_before_replay(self):
        legacy_db_path = Path(self.temp.name) / "legacy.db"
        growth_db.DB_PATH = legacy_db_path
        import sqlite3
        with sqlite3.connect(legacy_db_path) as db:
            db.execute("""
                CREATE TABLE growth_events (
                    update_id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    event_type TEXT NOT NULL CHECK(event_type IN ('join','leave')),
                    event_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute(
                "INSERT INTO growth_events(update_id,user_id,source,event_type) "
                "VALUES(77,101,'campaign_a','join')"
            )
            db.execute("""
                CREATE TABLE growth_members (
                    user_id INTEGER PRIMARY KEY,
                    invite_link TEXT,
                    is_member INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute(
                "INSERT INTO growth_members(user_id,invite_link,is_member) "
                "VALUES(101,'https://t.me/+campaignA',1)"
            )

        # First connect creates new schema tables and migrates the old event ID.
        with growth_db.connect() as db:
            self.assertIsNotNone(db.execute(
                "SELECT 1 FROM growth_processed_updates WHERE update_id=77"
            ).fetchone())
        # Replayed legacy update must not alter active membership or event totals.
        growth_db.record_member(77, 101, "https://t.me/+campaignA", True)
        self.assertEqual(growth_db.active_count(), 1)
        self.assertEqual(growth_db.report(), [("campaign_a", 1, 0, 1)])

    def test_leave_for_unknown_member_is_ignored(self):
        growth_db.record_member(9, 909, None, False)
        self.assertEqual(growth_db.report(), [])
        self.assertEqual(growth_db.active_count(), 0)


    def test_source_report_includes_active_members_by_source(self):
        growth_db.record_member(1, 101, "https://t.me/+campaignA", True)
        growth_db.record_member(2, 202, "https://t.me/+campaignB", True)
        growth_db.record_member(3, 202, None, False)

        report = {row[0]: row[1:] for row in growth_db.source_report()}
        self.assertEqual(report["campaign_a"], (1, 0, 1, 1))
        self.assertEqual(report["campaign_b"], (1, 1, 0, 0))

    def test_source_report_period_filters_events_but_keeps_current_active_count(self):
        growth_db.record_member(1, 101, "https://t.me/+campaignA", True)
        with growth_db.connect() as db:
            db.execute(
                "UPDATE growth_events SET event_at='2020-01-01 00:00:00' WHERE update_id=1"
            )

        report = {row[0]: row[1:] for row in growth_db.source_report(days=7)}
        self.assertEqual(report["campaign_a"], (0, 0, 0, 1))

    def test_source_report_rejects_invalid_period(self):
        for value in (0, -1, 3651, "last week"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    growth_db.source_report(value)


if __name__ == "__main__":
    unittest.main()
