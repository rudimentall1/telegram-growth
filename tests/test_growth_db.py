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

    def test_leave_for_unknown_member_is_ignored(self):
        growth_db.record_member(9, 909, None, False)
        self.assertEqual(growth_db.report(), [])
        self.assertEqual(growth_db.active_count(), 0)


if __name__ == "__main__":
    unittest.main()
