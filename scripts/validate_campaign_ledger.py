#!/usr/bin/env python3
"""Validate evidence and approval gates in the organic distribution ledger."""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

STATUSES = {"candidate", "rules_checked", "permission_confirmed", "published", "measured"}
DECISIONS = {"approved_for_manual_post", "not_allowed", "needs_clarification"}
METRICS = {"views_24h", "views_7d", "attributed_joins", "observed_leaves", "d7_retained"}
URL_RE = re.compile(r"^https?://\S+$")


def is_date(value):
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def is_url(value):
    return isinstance(value, str) and bool(URL_RE.match(value))


def validate_ledger(data):
    errors = []
    if not isinstance(data, dict) or data.get("version") != 1:
        return ["root must be an object with version=1"]
    placements = data.get("placements")
    if not isinstance(placements, list):
        return ["placements must be a list"]

    seen_ids = set()
    for index, row in enumerate(placements):
        prefix = f"placements[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        target_id = row.get("target_id")
        if not isinstance(target_id, str) or not target_id.strip():
            errors.append(f"{prefix}.target_id is required")
        record_id = row.get("record_id")
        if not isinstance(record_id, str) or not record_id.strip():
            errors.append(f"{prefix}.record_id is required")
        elif record_id in seen_ids:
            errors.append(f"{prefix}.record_id duplicates {record_id}")
        else:
            seen_ids.add(record_id)

        status = row.get("status")
        if status not in STATUSES:
            errors.append(f"{prefix}.status must be one of {', '.join(sorted(STATUSES))}")
            continue
        decision = row.get("permission_decision")
        if decision is not None and decision not in DECISIONS:
            errors.append(f"{prefix}.permission_decision is invalid")
        if status == "rules_checked" and decision not in DECISIONS:
            errors.append(f"{prefix}.permission_decision is required for rules_checked status")

        if status in {"rules_checked", "permission_confirmed", "published", "measured"}:
            if not is_date(row.get("rules_checked_at")):
                errors.append(f"{prefix}.rules_checked_at must be YYYY-MM-DD")

        if status in {"permission_confirmed", "published", "measured"}:
            if decision != "approved_for_manual_post":
                errors.append(f"{prefix} requires permission_decision=approved_for_manual_post")
            if not is_url(row.get("permission_evidence_url")):
                errors.append(f"{prefix}.permission_evidence_url must be an http(s) URL")
            if not isinstance(row.get("approved_by"), str) or not row["approved_by"].strip():
                errors.append(f"{prefix}.approved_by is required")
            if not is_date(row.get("approved_at")):
                errors.append(f"{prefix}.approved_at must be YYYY-MM-DD")

        if status in {"published", "measured"}:
            if not is_url(row.get("post_url")):
                errors.append(f"{prefix}.post_url must be an http(s) URL")
            if not is_date(row.get("posted_at")):
                errors.append(f"{prefix}.posted_at must be YYYY-MM-DD")
            if not isinstance(row.get("campaign_source"), str) or not row["campaign_source"].strip():
                errors.append(f"{prefix}.campaign_source is required")
            if not is_url(row.get("invite_link")):
                errors.append(f"{prefix}.invite_link must be an http(s) URL")

        for field in METRICS:
            value = row.get(field)
            if field in row and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                errors.append(f"{prefix}.{field} must be a non-negative integer")

        if status == "measured":
            for field in ("views_24h", "attributed_joins", "observed_leaves"):
                if field not in row:
                    errors.append(f"{prefix}.{field} is required for measured status")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", default="distribution/campaign_ledger.json")
    args = parser.parse_args()
    path = Path(args.ledger)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read valid JSON from {path}: {exc}", file=sys.stderr)
        return 1
    errors = validate_ledger(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {len(data['placements'])} placement record(s) validated; no publishing action was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
