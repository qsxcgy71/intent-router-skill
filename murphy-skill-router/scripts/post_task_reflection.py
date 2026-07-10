#!/usr/bin/env python3
"""Validate and record privacy-preserving Router post-task outcomes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = SKILL_DIR / "references" / "route-feedback.jsonl"

ALLOWED_FIELDS = {
    "event_id",
    "decision_id",
    "context_key",
    "task_id",
    "intent_family",
    "recommended_skill",
    "final_skill",
    "outcome",
    "failure_class",
    "evidence_source",
    "verification_status",
    "risk_class",
    "availability_status",
    "release_id",
    "catalog_fingerprint",
    "final_skill_fingerprint",
    "timestamp",
}
REQUIRED_FIELDS = ALLOWED_FIELDS
ENUMS = {
    "outcome": {"success", "corrected_success", "failed", "abandoned"},
    "failure_class": {
        "none",
        "route_miss",
        "dependency_miss",
        "execution_failure",
        "intent_changed",
        "ambiguous",
    },
    "evidence_source": {
        "explicit_user_correction",
        "agent_inference",
        "test_feedback",
        "model_advisory",
    },
    "verification_status": {"verified_success", "unverified", "failed"},
    "risk_class": {"read_only", "workspace_write", "external_action", "sensitive", "financial"},
    "availability_status": {"available", "missing_dependency", "plugin_required", "blocked"},
}
IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:@/+\-]{1,200}$")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class FeedbackValidationError(ValueError):
    """Raised when feedback contains unsafe or malformed data."""


def sanitize_event(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise FeedbackValidationError("feedback must be an object")
    unknown = set(payload) - ALLOWED_FIELDS
    missing = REQUIRED_FIELDS - set(payload)
    if unknown:
        raise FeedbackValidationError(f"unknown or forbidden fields: {','.join(sorted(unknown))}")
    if missing:
        raise FeedbackValidationError(f"missing fields: {','.join(sorted(missing))}")

    clean: dict[str, str] = {}
    for field in sorted(ALLOWED_FIELDS):
        value = payload[field]
        if not isinstance(value, str) or not value:
            raise FeedbackValidationError(f"{field} must be a non-empty string")
        if field in ENUMS:
            if value not in ENUMS[field]:
                raise FeedbackValidationError(f"invalid {field}: {value}")
        elif field == "timestamp":
            if not TIMESTAMP.fullmatch(value):
                raise FeedbackValidationError("timestamp must be UTC ISO-8601")
        elif not IDENTIFIER.fullmatch(value):
            raise FeedbackValidationError(f"{field} must be a bounded identifier, not free text")
        clean[field] = value

    if clean["failure_class"] == "route_miss":
        if clean["recommended_skill"] == clean["final_skill"]:
            raise FeedbackValidationError("route_miss requires a different final skill")
    if clean["outcome"] == "corrected_success" and clean["verification_status"] != "verified_success":
        raise FeedbackValidationError("corrected_success must be verified")
    return clean


def record_event(payload: dict, ledger: Path = DEFAULT_LEDGER) -> dict:
    clean = sanitize_event(payload)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(clean, ensure_ascii=False, sort_keys=True) + "\n")
    return clean


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", type=Path, required=True, help="JSON file with structured fields only")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args()
    payload = json.loads(args.event.read_text(encoding="utf-8"))
    clean = record_event(payload, args.ledger)
    print(json.dumps({"recorded": True, "event_id": clean["event_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
