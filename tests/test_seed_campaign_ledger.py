import unittest

from scripts.seed_campaign_ledger import seed_records


class SeedCampaignLedgerTests(unittest.TestCase):
    def setUp(self):
        self.registry = {
            "version": 1,
            "networks": [],
            "communities": [
                {
                    "id": "ifreepr",
                    "name": "Free пиар чат",
                    "url": "https://t.me/ifreepr",
                    "evidence_url": "https://t.me/ifreepr",
                    "publicly_stated_permission": "Description says free ads are allowed.",
                }
            ],
            "directories": [],
        }
        self.ledger = {"version": 1, "placements": []}

    def test_seed_creates_candidate_only_and_keeps_discovery_evidence(self):
        ledger, created, skipped = seed_records(self.registry, self.ledger, ["ifreepr"])
        self.assertEqual(len(created), 1)
        self.assertEqual(skipped, [])
        row = ledger["placements"][0]
        self.assertEqual(row["status"], "candidate")
        self.assertNotIn("permission_decision", row)
        self.assertNotIn("approved_by", row)
        self.assertEqual(row["discovery_evidence_url"], "https://t.me/ifreepr")

    def test_repeated_seed_is_idempotent(self):
        first, _, _ = seed_records(self.registry, self.ledger, ["ifreepr"])
        second, created, skipped = seed_records(self.registry, first, ["ifreepr"])
        self.assertEqual(created, [])
        self.assertEqual(skipped, ["ifreepr"])
        self.assertEqual(len(second["placements"]), 1)

    def test_unknown_id_fails(self):
        with self.assertRaisesRegex(ValueError, "unknown target id"):
            seed_records(self.registry, self.ledger, ["missing"])

    def test_duplicate_ids_in_registry_fail(self):
        self.registry["directories"] = [{"id": "ifreepr", "name": "duplicate", "url": "https://example.com"}]
        with self.assertRaisesRegex(ValueError, "duplicate target id"):
            seed_records(self.registry, self.ledger, ["ifreepr"])

    def test_generated_record_id_collision_fails(self):
        ledger = {"version": 1, "placements": [
            {"record_id": "target-ifreepr", "target_id": "different-target", "status": "candidate"}
        ]}
        with self.assertRaisesRegex(ValueError, "record_id already exists"):
            seed_records(self.registry, ledger, ["ifreepr"])

    def test_malformed_existing_target_id_fails_cleanly(self):
        ledger = {"version": 1, "placements": [
            {"record_id": "r1", "target_id": [], "status": "candidate"}
        ]}
        with self.assertRaisesRegex(ValueError, "target_id must be a string"):
            seed_records(self.registry, ledger, ["ifreepr"])

    def test_non_object_existing_placement_fails_cleanly(self):
        ledger = {"version": 1, "placements": ["bad-row"]}
        with self.assertRaisesRegex(ValueError, "must be an object"):
            seed_records(self.registry, ledger, ["ifreepr"])

    def test_invalid_ledger_shape_fails(self):
        with self.assertRaisesRegex(ValueError, "placements"):
            seed_records(self.registry, {"version": 1, "placements": None}, ["ifreepr"])


if __name__ == "__main__":
    unittest.main()
