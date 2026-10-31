#!/usr/bin/env python3
"""Audit the free-distribution target registry without contacting any target."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "distribution" / "targets.json"
GROUP_FIELDS = {
    "networks": "setup_status",
    "communities": "automation_status",
    "directories": "submission_status",
}


def audit_registry(data: dict[str, Any], as_of: date, max_age_days: int = 14) -> dict[str, Any]:
    if max_age_days < 0:
        raise ValueError("max_age_days must be non-negative")
    errors: list[str] = []
    warnings: list[str] = []
    groups: dict[str, Any] = {}
    seen_ids: set[str] = set()

    for group, status_field in GROUP_FIELDS.items():
        records = data.get(group, [])
        if not isinstance(records, list):
            errors.append(f"{group}: expected a list")
            continue
        statuses: Counter[str] = Counter()
        stale = 0
        missing_dates = 0
        missing_evidence = 0
        missing_permission = 0
        for index, record in enumerate(records):
            label = f"{group}[{index}]"
            if not isinstance(record, dict):
                errors.append(f"{label}: expected an object")
                continue
            for field in ("id", "name", "url"):
                if not record.get(field):
                    errors.append(f"{label}: missing {field}")
            record_id = record.get("id")
            if record_id:
                if record_id in seen_ids:
                    errors.append(f"{label}: duplicate id {record_id}")
                seen_ids.add(record_id)

            status = record.get(status_field)
            if status:
                statuses[str(status)] += 1
            else:
                warnings.append(f"{label}: missing {status_field}")

            if not record.get("evidence_url"):
                missing_evidence += 1
            checked = record.get("checked_at")
            if not checked:
                missing_dates += 1
            else:
                try:
                    checked_date = date.fromisoformat(str(checked))
                    if checked_date < as_of - timedelta(days=max_age_days):
                        stale += 1
                except ValueError:
                    errors.append(f"{label}: invalid checked_at date {checked!r}")

            if group == "communities" and not record.get("publicly_stated_permission"):
                missing_permission += 1

        if missing_evidence:
            warnings.append(f"{group}: {missing_evidence} records lack evidence_url")
        if missing_dates:
            warnings.append(f"{group}: {missing_dates} records lack checked_at")
        if stale:
            warnings.append(f"{group}: {stale} records have evidence older than {max_age_days} days")
        if missing_permission:
            warnings.append(f"{group}: {missing_permission} records lack a public permission description")

        groups[group] = {
            "count": len(records),
            "statuses": dict(sorted(statuses.items())),
            "missing_checked_at": missing_dates,
            "stale_checked_at": stale,
            "missing_evidence_url": missing_evidence,
            "missing_public_permission": missing_permission,
        }

    return {
        "checked_at": as_of.isoformat(),
        "max_age_days": max_age_days,
        "total_records": sum(item["count"] for item in groups.values()),
        "groups": groups,
        "errors": errors,
        "warnings": warnings,
        "ok": not errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--max-age-days", type=int, default=14)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.registry.read_text(encoding="utf-8"))
        report = audit_registry(data, args.as_of, args.max_age_days)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Registry audit failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
