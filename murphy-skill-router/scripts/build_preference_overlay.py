#!/usr/bin/env python3
"""Build a bounded, temporary Router preference overlay from sanitized outcomes."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from post_task_reflection import sanitize_event


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = SKILL_DIR / "references" / "route-feedback.jsonl"
DEFAULT_OVERLAY = SKILL_DIR / "references" / "router-preference-overlay.json"
TTL_DAYS = 30
LEARNABLE_FAILURE = "route_miss"
ELIGIBLE_SOURCES = {"explicit_user_correction", "agent_inference", "test_feedback"}


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _eligible(row: dict) -> bool:
    return (
        row["failure_class"] == LEARNABLE_FAILURE
        and row["outcome"] == "corrected_success"
        and row["verification_status"] == "verified_success"
        and row["availability_status"] == "available"
        and row["evidence_source"] in ELIGIBLE_SOURCES
    )


def build_overlay(rows: list[dict], *, now: str | None = None) -> dict:
    now_dt = parse_timestamp(now) if now else datetime.now(timezone.utc)
    unique: list[dict] = []
    seen: set[str] = set()
    duplicates = 0
    invalid = 0
    for raw in rows:
        try:
            row = sanitize_event(raw)
        except (ValueError, TypeError):
            invalid += 1
            continue
        if row["event_id"] in seen:
            duplicates += 1
            continue
        seen.add(row["event_id"])
        unique.append(row)

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in unique:
        if _eligible(row):
            grouped[row["context_key"]].append(row)

    active: dict[str, dict] = {}
    shadow: dict[str, dict] = {}
    quarantined: dict[str, dict] = {}
    for context_key, events in sorted(grouped.items()):
        by_target: dict[str, list[dict]] = defaultdict(list)
        for row in events:
            by_target[row["final_skill"]].append(row)
        if len(by_target) > 1:
            quarantined[context_key] = {
                "state": "quarantined",
                "reason_code": "conflicting_replacements",
                "candidate_skills": sorted(by_target),
                "evidence_count": sum(len(items) for items in by_target.values()),
            }
            continue

        target, evidence = next(iter(by_target.items()))
        evidence.sort(key=lambda row: (parse_timestamp(row["timestamp"]), row["event_id"]))
        latest = evidence[-1]
        explicit = [row for row in evidence if row["evidence_source"] == "explicit_user_correction"]
        inferred = [
            row for row in evidence if row["evidence_source"] in {"agent_inference", "test_feedback"}
        ]
        inferred_tasks = {row["task_id"] for row in inferred}
        can_activate = bool(explicit) or (len(inferred) >= 3 and len(inferred_tasks) >= 2)
        expires_at = parse_timestamp(latest["timestamp"]) + timedelta(days=TTL_DAYS)
        record = {
            "preferred_skill": target,
            "state": "active" if can_activate and expires_at > now_dt else "shadow_only",
            "reason_code": "threshold_met" if can_activate else "insufficient_evidence",
            "evidence_count": len(evidence),
            "task_count": len({row["task_id"] for row in evidence}),
            "evidence_source": "explicit_user_correction" if explicit else "inferred_evidence",
            "release_id": latest["release_id"],
            "catalog_fingerprint": latest["catalog_fingerprint"],
            "preferred_skill_fingerprint": latest["final_skill_fingerprint"],
            "created_at": latest["timestamp"],
            "expires_at": iso_z(expires_at),
        }
        if can_activate and expires_at > now_dt:
            active[context_key] = record
        else:
            if expires_at <= now_dt:
                record["reason_code"] = "expired"
            shadow[context_key] = record

    return {
        "version": 1,
        "mode": "shadow_preference_overlay",
        "enabled": True,
        "generated_at": iso_z(now_dt),
        "policy": {
            "ttl_days": TTL_DAYS,
            "explicit_verified_threshold": 1,
            "inferred_verified_threshold": 3,
            "inferred_min_tasks": 2,
            "model_advisory_activation": False,
            "auto_promote": False,
        },
        "active_preferences": active,
        "shadow_preferences": shadow,
        "quarantined": quarantined,
        "summary": {
            "events_seen": len(rows),
            "events_valid": len(unique),
            "duplicates_ignored": duplicates,
            "invalid_ignored": invalid,
            "active": len(active),
            "shadow_only": len(shadow),
            "quarantined": len(quarantined),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OVERLAY)
    args = parser.parse_args()
    overlay = build_overlay(read_jsonl(args.ledger))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(overlay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(overlay["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
