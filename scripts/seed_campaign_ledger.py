#!/usr/bin/env python3
"""Seed candidate-only campaign records from the distribution target registry."""
import argparse
import json
import sys
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def seed_records(registry, ledger, target_ids):
    if not isinstance(registry, dict) or not isinstance(ledger, dict):
        raise ValueError("registry and ledger roots must be JSON objects")
    if registry.get("version") != 1 or ledger.get("version") != 1:
        raise ValueError("registry and ledger must both have version=1")
    placements = ledger.get("placements")
    if not isinstance(placements, list):
        raise ValueError("ledger.placements must be a list")

    index = {}
    for section in ("networks", "communities", "directories"):
        rows = registry.get(section, [])
        if not isinstance(rows, list):
            raise ValueError(f"registry.{section} must be a list")
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                if row["id"] in index:
                    raise ValueError(f"duplicate target id in registry: {row['id']}")
                index[row["id"]] = (section, row)

    existing = set()
    existing_record_ids = set()
    for position, row in enumerate(placements):
        if not isinstance(row, dict):
            raise ValueError(f"ledger.placements[{position}] must be an object")
        target_id = row.get("target_id")
        record_id = row.get("record_id")
        if target_id is not None and not isinstance(target_id, str):
            raise ValueError(f"ledger.placements[{position}].target_id must be a string")
        if record_id is not None and not isinstance(record_id, str):
            raise ValueError(f"ledger.placements[{position}].record_id must be a string")
        if target_id is not None:
            existing.add(target_id)
        if record_id is not None:
            existing_record_ids.add(record_id)
    created, skipped = [], []
    for target_id in target_ids:
        if target_id in existing:
            skipped.append(target_id)
            continue
        if target_id not in index:
            raise ValueError(f"unknown target id: {target_id}")
        section, target = index[target_id]
        record_id = f"target-{target_id}"
        if record_id in existing_record_ids:
            raise ValueError(f"record_id already exists in ledger: {record_id}")
        record = {
            "record_id": record_id,
            "target_id": target_id,
            "target_name": target.get("name"),
            "target_url": target.get("url"),
            "registry_section": section,
            "status": "candidate",
        }
        evidence = target.get("evidence_url")
        if isinstance(evidence, str) and evidence.startswith(("http://", "https://")):
            record["discovery_evidence_url"] = evidence
        placements.append(record)
        existing.add(target_id)
        existing_record_ids.add(record_id)
        created.append(record)
    return ledger, created, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-id", action="append", required=True, help="Registry ID; repeat for multiple targets")
    parser.add_argument("--registry", default="distribution/targets.json")
    parser.add_argument("--ledger", default="distribution/campaign_ledger.json")
    parser.add_argument("--write", action="store_true", help="Persist the updated ledger; default is dry-run")
    args = parser.parse_args()
    try:
        registry = load_json(args.registry)
        ledger = load_json(args.ledger)
        updated, created, skipped = seed_records(registry, ledger, args.target_id)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Candidates to add: {len(created)}; already present: {len(skipped)}")
    for row in created:
        print(f"  {row['target_id']}: {row['target_name']} [{row['status']}]")
    if args.write and created:
        Path(args.ledger).write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Updated {args.ledger}")
    elif created:
        print("Dry run only. Re-run with --write to persist; no permissions or posts were created.")
    else:
        print("No changes required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
