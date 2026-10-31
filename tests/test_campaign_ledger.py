import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_campaign_ledger import validate_ledger


def published_row():
    return {
        "record_id": "wave1-chat-a",
        "target_id": "chat-a",
        "status": "published",
        "rules_checked_at": "2026-10-31",
        "permission_decision": "approved_for_manual_post",
        "permission_evidence_url": "https://t.me/chat_a/12",
        "approved_by": "channel-owner-confirmed",
        "approved_at": "2026-10-31",
        "campaign_source": "wave1_chat_a",
        "invite_link": "https://t.me/+example",
        "post_url": "https://t.me/chat_a/13",
        "posted_at": "2026-10-31",
    }


class CampaignLedgerTests(unittest.TestCase):
    def test_candidate_does_not_imply_permission(self):
        data = {"version": 1, "placements": [
            {"record_id": "r1", "target_id": "chat-a", "status": "candidate"}
        ]}
        self.assertEqual(validate_ledger(data), [])

    def test_published_requires_explicit_permission(self):
        row = published_row()
        row["permission_decision"] = "needs_clarification"
        errors = validate_ledger({"version": 1, "placements": [row]})
        self.assertTrue(any("permission_decision=approved_for_manual_post" in e for e in errors))

    def test_published_requires_post_and_invite_links(self):
        row = published_row()
        row.pop("invite_link")
        row.pop("post_url")
        errors = validate_ledger({"version": 1, "placements": [row]})
        self.assertTrue(any(".invite_link" in e for e in errors))
        self.assertTrue(any(".post_url" in e for e in errors))

    def test_measured_requires_observed_metrics(self):
        row = published_row()
        row["status"] = "measured"
        errors = validate_ledger({"version": 1, "placements": [row]})
        self.assertTrue(any(".views_24h is required" in e for e in errors))
        self.assertTrue(any(".attributed_joins is required" in e for e in errors))
        self.assertTrue(any(".observed_leaves is required" in e for e in errors))

    def test_negative_metric_and_duplicate_ids_fail(self):
        first = published_row()
        first["views_24h"] = -1
        second = dict(first)
        errors = validate_ledger({"version": 1, "placements": [first, second]})
        self.assertTrue(any("duplicates" in e for e in errors))
        self.assertTrue(any(".views_24h must be a non-negative integer" in e for e in errors))

    def test_invalid_date_fails(self):
        row = published_row()
        row["rules_checked_at"] = "yesterday"
        errors = validate_ledger({"version": 1, "placements": [row]})
        self.assertTrue(any(".rules_checked_at must be YYYY-MM-DD" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
