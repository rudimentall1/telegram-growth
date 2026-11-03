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

    def test_non_string_record_ids_are_structural_errors(self):
        for value in ([], {}, 123):
            with self.subTest(value=value):
                self.registry["communities"][0]["id"] = value
                result = audit_registry(self.registry, date(2026, 10, 31))
                self.assertFalse(result["ok"])
                self.assertTrue(any("id must be a non-empty string" in item for item in result["errors"]))

    def test_paid_network_cannot_be_recommended_as_free_first_wave(self):
        network = self.registry["networks"][0]
        network.update({
            "money_required": True,
            "free_cash_route_confirmed": True,
            "recommendation": "first_wave",
        })
        result = audit_registry(self.registry, date(2026, 10, 31))
        self.assertFalse(result["ok"])
        self.assertTrue(any("paid route cannot be marked" in item for item in result["errors"]))

    def test_first_wave_requires_confirmed_zero_cash_route(self):
        network = self.registry["networks"][0]
        network.update({
            "money_required": False,
            "free_cash_route_confirmed": False,
            "recommendation": "first_wave",
        })
        result = audit_registry(self.registry, date(2026, 10, 31))
        self.assertFalse(result["ok"])
        self.assertTrue(any("first_wave requires a confirmed zero-cash route" in item for item in result["errors"]))

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
