import unittest

from scripts.validate_campaign_ledger import validate_ledger


def rules_checked_row():
    return {
        "record_id": "rules-chat-a",
        "target_id": "chat-a",
        "status": "rules_checked",
        "rules_checked_at": "2026-10-31",
        "rules_evidence_url": "https://t.me/chat_a/10",
        "rules_evidence_type": "in_chat_rules",
        "rules_checked_by": "reviewer-1",
        "permission_decision": "needs_clarification",
    }


def published_row():
    return {
        "record_id": "wave1-chat-a",
        "target_id": "chat-a",
        "status": "published",
        "rules_checked_at": "2026-10-31",
        "rules_evidence_url": "https://t.me/chat_a/10",
        "rules_checked_by": "reviewer-1",
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

    def test_public_description_evidence_must_be_complete(self):
        row = {"record_id": "r1", "target_id": "chat-a", "status": "candidate",
               "public_description_checked_at": "2026-10-31"}
        errors = validate_ledger({"version": 1, "placements": [row]})
        self.assertTrue(any("public description evidence requires" in error for error in errors))

    def test_complete_public_description_evidence_is_valid_for_candidate(self):
        row = {"record_id": "r1", "target_id": "chat-a", "status": "candidate",
               "public_description_checked_at": "2026-10-31",
               "public_description_summary": "Preview says free promotion; rules unverified.",
               "public_description_evidence_url": "https://t.me/chat_a"}
        self.assertEqual(validate_ledger({"version": 1, "placements": [row]}), [])

    def test_rules_checked_requires_rules_permalink_and_reviewer(self):
        row = rules_checked_row()
        row.pop("rules_evidence_url")
        row.pop("rules_checked_by")
        errors = validate_ledger({"version": 1, "placements": [row]})
        self.assertTrue(any(".rules_evidence_url" in e for e in errors))
        self.assertTrue(any(".rules_checked_by is required" in e for e in errors))

    def test_rules_checked_with_explicit_evidence_is_valid(self):
        self.assertEqual(validate_ledger({"version": 1, "placements": [rules_checked_row()]}), [])

    def test_public_preview_cannot_substitute_for_in_chat_rules(self):
        row = rules_checked_row()
        row["rules_evidence_type"] = "public_preview"
        errors = validate_ledger({"version": 1, "placements": [row]})
        self.assertTrue(any("rules_evidence_type must be in_chat_rules" in e for e in errors))

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
