import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from datetime import datetime, timedelta, timezone
from pathlib import Path

from publisher.policy import evaluate_target
from publisher.links import normalize_public_target
from publisher.cli import main as publisher_main
from publisher.service import PublisherService
from publisher.storage import PublisherStore


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = PublisherStore(str(Path(self.tmp.name) / "publisher.db"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_public_telegram_link_normalization(self):
        self.assertEqual(normalize_public_target("@CryptoPing_RU"), "@cryptoping_ru")
        self.assertEqual(normalize_public_target("https://t.me/CryptoPing_RU/"), "@cryptoping_ru")
        self.assertEqual(normalize_public_target("t.me/s/CryptoPing_RU"), "@cryptoping_ru")

    def test_private_invite_and_non_telegram_links_are_rejected(self):
        for value in ("https://t.me/+privateInvite", "https://example.com/group", "not a link"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_public_target(value)

    def test_add_target_normalizes_and_deduplicates(self):
        first_id = self.store.add_target("group", "https://t.me/CryptoPing_RU")
        second_id = self.store.add_target("group", "@cryptoping_ru")
        self.assertEqual(first_id, second_id)
        self.assertEqual(len(self.store.list_targets()), 1)

    def test_csv_import_adds_deduplicates_and_rejects_invites(self):
        csv_path = Path(self.tmp.name) / "candidates.csv"
        csv_path.write_text(
            "kind,handle,rules_url\n"
            "group,https://t.me/example_group,https://t.me/example_group\n"
            "group,@example_group,\n"
            "channel,https://t.me/+privateInvite,\n",
            encoding="utf-8",
        )
        output = StringIO()
        with redirect_stdout(output):
            publisher_main([
                "--db", str(self.store.db_path),
                "import-candidates", "--csv", str(csv_path),
            ])
        self.assertIn("added=1, duplicates=1, rejected=1", output.getvalue())
        self.assertEqual(len(self.store.list_targets()), 1)

    def test_import_existing_distribution_catalog_preserves_metadata_and_pending_status(self):
        catalog_path = Path(self.tmp.name) / "targets.json"
        catalog_path.write_text(json.dumps({
            "communities": [{
                "id": "sample-pr",
                "name": "Sample PR group",
                "url": "https://t.me/sample_pr_group",
                "kind": "public_self_promotion_group",
                "language": "ru",
                "audience_topics": ["promotion", "crypto"],
                "publicly_stated_permission": "Description says free PR.",
                "observed_members": 1234,
                "checked_at": "2026-10-28",
                "automation_status": "discovered_not_joined",
                "evidence_url": "https://t.me/sample_pr_group"
            }]
        }), encoding="utf-8")
        output = StringIO()
        with redirect_stdout(output):
            publisher_main(["--db", str(self.store.db_path), "import-catalog", "--json", str(catalog_path)])
        self.assertIn("processed=1, rejected=0", output.getvalue())
        targets = self.store.list_targets()
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["display_name"], "Sample PR group")
        self.assertEqual(targets[0]["source_status"], "discovered_not_joined")
        self.assertEqual(targets[0]["status"], "pending")
        self.assertEqual(targets[0]["promotion_policy"], "unknown")

    def test_catalog_reimport_updates_metadata_without_duplicates(self):
        catalog_path = Path(self.tmp.name) / "targets.json"
        first = {
            "communities": [{
                "id": "sample-pr",
                "name": "Original name",
                "url": "https://t.me/sample_pr_group",
                "kind": "public_self_promotion_group",
                "language": "ru",
                "audience_topics": ["promotion"],
                "checked_at": "2026-10-28",
                "automation_status": "discovered_not_joined",
            }]
        }
        catalog_path.write_text(json.dumps(first), encoding="utf-8")
        with redirect_stdout(StringIO()):
            publisher_main(["--db", str(self.store.db_path), "import-catalog", "--json", str(catalog_path)])

        first_id = self.store.list_targets()[0]["id"]
        first["communities"][0]["name"] = "Updated name"
        catalog_path.write_text(json.dumps(first), encoding="utf-8")
        with redirect_stdout(StringIO()):
            publisher_main(["--db", str(self.store.db_path), "import-catalog", "--json", str(catalog_path)])

        targets = self.store.list_targets()
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["id"], first_id)
        self.assertEqual(targets[0]["display_name"], "Updated name")
        self.assertEqual(targets[0]["status"], "pending")
        self.assertEqual(targets[0]["promotion_policy"], "unknown")

    def test_new_target_is_pending_and_ineligible(self):
        target_id = self.store.add_target("group", "@example")
        target = self.store.get_target(target_id)
        self.assertEqual(target["status"], "pending")
        self.assertFalse(evaluate_target(target)[0])

    def test_approval_requires_explicit_allowed_policy_and_evidence(self):
        target_id = self.store.add_target("group", "@example")
        with self.assertRaises(ValueError):
            self.store.review_target(target_id, "approve", "approval_required", "rules")
        with self.assertRaises(ValueError):
            self.store.review_target(target_id, "approve", "allowed", "")
        self.store.review_target(target_id, "approve", "allowed", "Rules permit one relevant post")
        self.assertTrue(evaluate_target(self.store.get_target(target_id))[0])

    def test_rejected_target_is_ineligible(self):
        target_id = self.store.add_target("channel", "@example")
        self.store.review_target(target_id, "reject", "prohibited", "Rules prohibit promotion")
        self.assertFalse(evaluate_target(self.store.get_target(target_id))[0])

    def test_stale_review_is_ineligible(self):
        old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        target = {
            "status": "approved",
            "promotion_policy": "allowed",
            "permission_evidence": "rules URL",
            "reviewed_at": old,
            "last_posted_at": None,
        }
        self.assertEqual(evaluate_target(target), (False, "permission review is stale"))

    def test_cooldown_blocks_recent_target(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        target = {
            "status": "approved",
            "promotion_policy": "allowed",
            "permission_evidence": "explicit moderator approval",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "last_posted_at": recent,
        }
        self.assertFalse(evaluate_target(target)[0])

    def test_dry_run_requires_approved_draft_and_never_sends(self):
        draft_id = self.store.add_draft("Useful guide", "A useful CryptoPing RU guide.")
        with self.assertRaises(ValueError):
            PublisherService(self.store).build_plan(draft_id)
        self.store.approve_draft(draft_id)
        draft, plan = PublisherService(self.store).build_plan(draft_id)
        self.assertEqual(draft["title"], "Useful guide")
        self.assertEqual(plan, [])


if __name__ == "__main__":
    unittest.main()
