import unittest
from datetime import date

from scripts.audit_distribution_targets import audit_registry


class DistributionRegistryAuditTests(unittest.TestCase):
    def setUp(self):
        self.registry = {
            "networks": [
                {"id": "n1", "name": "Network", "url": "https://example.com",
                 "evidence_url": "https://example.com/evidence",
                 "setup_status": "discovered_not_connected"}
            ],
            "communities": [
                {"id": "c1", "name": "Community", "url": "https://t.me/example",
                 "evidence_url": "https://t.me/example", "checked_at": "2026-10-28",
                 "publicly_stated_permission": "Free PR allowed",
                 "automation_status": "discovered_not_joined"}
            ],
            "directories": [
                {"id": "d1", "name": "Directory", "url": "https://directory.example",
                 "evidence_url": "https://directory.example",
                 "submission_status": "not_submitted"}
            ],
        }

    def test_reports_status_and_missing_freshness_without_failing(self):
        result = audit_registry(self.registry, date(2026, 10, 31), max_age_days=14)
        self.assertTrue(result["ok"])
        self.assertEqual(result["total_records"], 3)
        self.assertEqual(result["groups"]["communities"]["statuses"],
                         {"discovered_not_joined": 1})
        self.assertEqual(result["groups"]["networks"]["missing_checked_at"], 1)
        self.assertEqual(result["groups"]["directories"]["missing_checked_at"], 1)

    def test_stale_community_evidence_is_flagged(self):
        result = audit_registry(self.registry, date(2026, 11, 30), max_age_days=14)
        self.assertEqual(result["groups"]["communities"]["stale_checked_at"], 1)
        self.assertTrue(any("older than 14 days" in item for item in result["warnings"]))

    def test_duplicate_ids_are_structural_errors(self):
        self.registry["directories"][0]["id"] = "c1"
        result = audit_registry(self.registry, date(2026, 10, 31))
        self.assertFalse(result["ok"])
        self.assertTrue(any("duplicate id c1" in item for item in result["errors"]))

    def test_noncanonical_and_impossible_dates_are_rejected(self):
        for value in ("20261028", "2026-W44-3", "2026-02-30"):
            with self.subTest(value=value):
                self.registry["communities"][0]["checked_at"] = value
                result = audit_registry(self.registry, date(2026, 10, 31))
                self.assertFalse(result["ok"])
                self.assertTrue(any("invalid checked_at date" in item for item in result["errors"]))

    def test_non_object_registry_root_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_registry([], date(2026, 10, 31))

    def test_invalid_dates_and_negative_age_are_rejected(self):
        self.registry["communities"][0]["checked_at"] = "not-a-date"
        result = audit_registry(self.registry, date(2026, 10, 31))
        self.assertFalse(result["ok"])
        with self.assertRaises(ValueError):
            audit_registry(self.registry, date(2026, 10, 31), max_age_days=-1)


if __name__ == "__main__":
    unittest.main()
