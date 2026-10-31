"""Command-line interface for reviewing targets and creating dry-run plans."""
import argparse
import csv
import json
import sqlite3

from .links import normalize_public_target
from .service import PublisherService
from .storage import PublisherStore


def build_parser():
    parser = argparse.ArgumentParser(prog="publisher")
    parser.add_argument("--db", help="SQLite path (defaults to data/publisher.db)")
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add-target", help="register a candidate community")
    add.add_argument("--kind", choices=("group", "channel"), required=True)
    add.add_argument("--handle", required=True, help="@username or public t.me URL")
    add.add_argument("--rules-url")

    review = commands.add_parser("review-target", help="record a human permission review")
    review.add_argument("--id", type=int, required=True)
    review.add_argument("--decision", choices=("approve", "reject"), required=True)
    review.add_argument("--policy", choices=("allowed", "approval_required", "prohibited", "unknown"), required=True)
    review.add_argument("--evidence", help="rules URL or a concise record of explicit moderator permission")

    importer = commands.add_parser("import-candidates", help="import public community candidates from CSV")
    importer.add_argument("--csv", required=True, dest="csv_path")

    catalog = commands.add_parser("import-catalog", help="import public communities from distribution/targets.json")
    catalog.add_argument("--json", dest="json_path", default="distribution/targets.json")

    pause = commands.add_parser("pause-target", help="pause a target without deleting its review history")
    pause.add_argument("--id", type=int, required=True)

    show = commands.add_parser("show-target", help="show full candidate metadata and permission evidence")
    show.add_argument("--id", type=int, required=True)

    commands.add_parser("list-targets", help="list registered communities")

    draft = commands.add_parser("add-draft", help="save a draft; it is not published")
    draft.add_argument("--title", required=True)
    draft.add_argument("--text", required=True)

    approve_draft = commands.add_parser("approve-draft", help="approve a draft for dry-run planning")
    approve_draft.add_argument("--id", type=int, required=True)

    plan = commands.add_parser("plan", help="show eligible targets without sending")
    plan.add_argument("--draft-id", type=int, required=True)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    store = PublisherStore(args.db)

    if args.command == "add-target":
        target_id = store.add_target(args.kind, args.handle, args.rules_url)
        print(f"Candidate registered: id={target_id}, status=pending")
    elif args.command == "review-target":
        store.review_target(args.id, args.decision, args.policy, args.evidence)
        print(f"Target {args.id}: {args.decision} recorded")
    elif args.command == "import-candidates":
        imported = 0
        duplicates = 0
        rejected = 0
        known = {target["handle"] for target in store.list_targets()}
        with open(args.csv_path, "r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            required = {"kind", "handle"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise ValueError("CSV must contain kind and handle columns")
            for line_number, row in enumerate(reader, start=2):
                try:
                    handle = normalize_public_target(row.get("handle", ""))
                    if handle in known:
                        duplicates += 1
                        continue
                    store.add_target(row.get("kind", "").strip().lower(), handle, row.get("rules_url", "").strip() or None)
                    known.add(handle)
                    imported += 1
                except (ValueError, sqlite3.Error) as exc:
                    rejected += 1
                    print(f"CSV line {line_number}: rejected ({exc})")
        print(f"Import complete: added={imported}, duplicates={duplicates}, rejected={rejected}")
    elif args.command == "import-catalog":
        with open(args.json_path, "r", encoding="utf-8") as source:
            catalog = json.load(source)
        communities = catalog.get("communities")
        if not isinstance(communities, list):
            raise ValueError("catalog JSON must contain a communities array")
        imported = 0
        rejected = 0
        for item in communities:
            try:
                store.import_catalog_community(item)
                imported += 1
            except (ValueError, sqlite3.Error, TypeError) as exc:
                rejected += 1
                item_id = item.get("id", "<unknown>") if isinstance(item, dict) else "<unknown>"
                print("Rejected catalog item " + str(item_id) + ": " + str(exc))
        print("Catalog import complete: processed=" + str(imported) + ", rejected=" + str(rejected))
    elif args.command == "pause-target":
        store.pause_target(args.id)
        print(f"Target {args.id}: paused")
    elif args.command == "show-target":
        target = store.get_target(args.id)
        if not target:
            raise LookupError(f"target {args.id} not found")
        topics = target.get("audience_topics_json") or "[]"
        print(f"Target #{target['id']}: {target.get('display_name') or target['handle']}")
        print(f"Handle: {target['handle']}")
        print(f"Kind: {target['kind']} (catalog: {target.get('source_kind') or 'manual'})")
        print(f"Status: {target['status']} | policy: {target['promotion_policy']}")
        print(f"Language: {target.get('language') or 'unknown'}")
        print(f"Topics: {topics}")
        print(f"Observed members: {target.get('observed_members') if target.get('observed_members') is not None else 'unknown'}")
        print(f"Discovery status: {target.get('source_status') or 'manual'}")
        print(f"Catalog checked: {target.get('source_checked_at') or 'unknown'}")
        print(f"Rules URL: {target.get('rules_url') or 'not set'}")
        print(f"Catalog evidence URL: {target.get('evidence_url') or 'not set'}")
        print(f"Publicly stated permission: {target.get('publicly_stated_permission') or 'not recorded'}")
        print(f"Permission evidence: {target.get('permission_evidence') or 'not recorded'}")
        print(f"Reviewed at: {target.get('reviewed_at') or 'not reviewed'}")
        print(f"Notes: {target.get('notes') or 'none'}")
    elif args.command == "list-targets":
        for target in store.list_targets():
            name = target.get("display_name") or target["handle"]
            language = target.get("language") or "?"
            source_status = target.get("source_status") or "manual"
            topics = target.get("audience_topics_json") or "[]"
            print(
                f"#{target['id']} {name} ({target['handle']}) [{target['kind']}] "
                f"status={target['status']} policy={target['promotion_policy']} "
                f"catalog_id={target.get('catalog_id') or '-'} "
                f"language={language} source={source_status} topics={topics}"
            )
    elif args.command == "add-draft":
        draft_id = store.add_draft(args.title, args.text)
        print(f"Draft saved: id={draft_id}, status=draft")
    elif args.command == "approve-draft":
        store.approve_draft(args.id)
        print(f"Draft {args.id}: approved for planning")
    elif args.command == "plan":
        draft, items = PublisherService(store).build_plan(args.draft_id)
        print(f"DRY RUN for draft #{draft['id']}: {draft['title']}")
        for item in items:
            state = "ELIGIBLE" if item.eligible else "SKIP"
            print(f"{state}: {item.handle} - {item.reason}")
        print("No messages were sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
