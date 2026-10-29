import tempfile
import unittest
from pathlib import Path

import cross_promo
import growth_db


class CrossPromoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_db_path = growth_db.DB_PATH
        growth_db.DB_PATH = Path(self.temp.name) / "growth.db"
        cross_promo.init_db()
        cross_promo.ensure_home_channel(
            -1000000000001, "CryptoPing RU", "cryptoping_ru", 23
        )

    def tearDown(self):
        growth_db.DB_PATH = self.original_db_path
        self.temp.cleanup()

    def add_active(self, chat_id, title, username, members, owner_id):
        row_id, status = cross_promo.add_pending_channel(
            chat_id=chat_id,
            title=title,
            username=username,
            member_count=members,
            owner_user_id=owner_id,
            home_invite_link=f"https://t.me/+tracked{abs(chat_id)}",
        )
        self.assertEqual(status, "pending")
        self.assertTrue(cross_promo.approve_channel(row_id, owner_id))
        return row_id

    def test_home_channel_is_registered_active_once(self):
        home = cross_promo.get_channel(-1000000000001)
        self.assertEqual(home["status"], "active")
        self.assertEqual(home["username"], "cryptoping_ru")
        self.assertEqual(home["member_count"], 23)

    def test_a_partner_is_pending_until_admin_approval(self):
        row_id, status = cross_promo.add_pending_channel(
            -1000000000002, "Partner", "partner_channel", 30, 42,
            "https://t.me/+trackedpartner",
        )
        self.assertEqual(status, "pending")
        self.assertEqual(len(cross_promo.pending_channels()), 1)
        self.assertFalse(cross_promo.due_targets())
        self.assertTrue(cross_promo.approve_channel(row_id, 7))
        self.assertEqual(len(cross_promo.pending_channels()), 0)
        self.assertEqual(len(cross_promo.due_targets()), 2)

    def test_same_channel_cannot_be_promoted_to_itself(self):
        self.assertIsNone(cross_promo.select_candidate(-1000000000001))

    def test_candidate_rotation_skips_recent_partner_when_alternative_exists(self):
        self.add_active(-1000000000002, "Partner A", "partner_a", 25, 42)
        self.add_active(-1000000000003, "Partner B", "partner_b", 30, 43)

        first = cross_promo.select_candidate(-1000000000001)
        self.assertIsNotNone(first)
        self.assertEqual(first["chat_id"], -1000000000002)

        cross_promo.mark_delivery(
            -1000000000001, int(first["chat_id"]), 1234
        )
        second = cross_promo.select_candidate(-1000000000001)
        self.assertIsNotNone(second)
        self.assertEqual(second["chat_id"], -1000000000003)

    def test_audience_size_matching_prefers_similar_channels(self):
        self.add_active(-1000000000002, "Similar", "similar_channel", 30, 42)
        self.add_active(-1000000000003, "Huge", "huge_channel", 9000, 43)
        chosen = cross_promo.select_candidate(-1000000000001)
        self.assertEqual(chosen["username"], "similar_channel")

    def test_mark_delivery_sets_cooldown_timestamp_and_log(self):
        partner_id = self.add_active(
            -1000000000002, "Partner", "partner_channel", 27, 42
        )
        cross_promo.mark_delivery(-1000000000001, -1000000000002, 555)
        cross_promo.mark_delivery(-1000000000002, -1000000000001, 556)
        home = cross_promo.get_channel(-1000000000001)
        self.assertIsNotNone(home["last_promo_at"])
        self.assertEqual(
            cross_promo.due_targets(),
            [],
        )
        with growth_db.connect() as db:
            row = db.execute(
                "SELECT target_chat_id, promoted_chat_id, message_id "
                "FROM crosspromo_deliveries WHERE target_chat_id=?",
                (-1000000000001,),
            ).fetchone()
        self.assertEqual(row, (-1000000000001, -1000000000002, 555))
        self.assertGreater(partner_id, 0)

    def test_paused_home_channel_is_not_auto_enabled(self):
        cross_promo.set_channel_status(-1000000000001, "paused")
        home = cross_promo.ensure_home_channel(
            -1000000000001, "CryptoPing RU", "cryptoping_ru", 24
        )
        self.assertEqual(home["status"], "paused")

    def test_home_channel_can_be_resumed_explicitly(self):
        cross_promo.set_channel_status(-1000000000001, "paused")
        self.assertTrue(cross_promo.set_channel_status(-1000000000001, "active"))
        self.assertEqual(cross_promo.get_channel(-1000000000001)["status"], "active")

    def test_interval_validation(self):
        for invalid in (0, -1, 721, "never"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    cross_promo.due_targets(invalid)


if __name__ == "__main__":
    unittest.main()
