#!/usr/bin/env python3
"""Mine desensitized router evolution logs for failure signals."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from router_evolution_lib import EVOLUTION_LOG, FAILURE_TYPES, read_jsonl, write_json


def parse_since(value: str) -> datetime | None:
    match = re.fullmatch(r"(\d+)([dhw])", value.strip())
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    delta = {"d": timedelta(days=amount), "h": timedelta(hours=amount), "w": timedelta(weeks=amount)}[unit]
    return datetime.now(timezone.utc) - delta


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y%m%dT%H%M%SZ"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def is_failure(row: dict) -> bool:
    failure_type = row.get("failure_type")
    return bool(
        row.get("user_correction_summary")
        or row.get("success_signal") is False
        or (failure_type and failure_type in FAILURE_TYPES)
    )


def mine(rows: list[dict], since: datetime | None) -> dict:
    filtered = []
    for row in rows:
        ts = parse_timestamp(row.get("timestamp", ""))
        if since and ts and ts < since:
            continue
        if is_failure(row):
            filtered.append(row)
    failures = Counter(row.get("failure_type", "unclassified") for row in filtered)
    routes = Counter(row.get("final_route") or row.get("chosen_primary") or "unknown" for row in filtered)
    examples = []
    for row in filtered[:20]:
        examples.append(
            {
                "timestamp": row.get("timestamp"),
                "prompt_summary": row.get("prompt_summary"),
                "chosen_primary": row.get("chosen_primary"),
                "final_route": row.get("final_route"),
                "failure_type": row.get("failure_type", "unclassified"),
                "user_correction_summary": row.get("user_correction_summary"),
            }
        )
    return {
        "total_rows": len(rows),
        "failure_rows": len(filtered),
        "failure_types": dict(failures.most_common()),
        "routes": dict(routes.most_common()),
        "examples": examples,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=EVOLUTION_LOG)
    parser.add_argument("--since", default="7d")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    since = parse_since(args.since)
    rows = read_jsonl(args.input)
    summary = mine(rows, since)
    if args.output:
        write_json(args.output, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
