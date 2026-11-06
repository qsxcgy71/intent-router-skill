#!/usr/bin/env python3
"""Record bounded task lessons; never execute their proposed changes."""

from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import re


DEFAULT_LEDGER = Path(__file__).resolve().parents[1] / "references" / "task-retrospectives.jsonl"
CATEGORIES = {
    "skill_misunderstanding", "retrieval_miss", "rerank_miss", "skill_gap",
    "overconstraint", "overtrigger", "undertrigger", "dependency_miss",
    "execution_failure", "success_pattern",
}
ENUMS = {
    "task_status": {"completed", "failed", "blocked", "cancelled"},
    "category": CATEGORIES,
    "evidence_level": {"hypothesis", "observed", "verified"},
    "change_target": {"none", "skill_description", "skill_body", "router_map", "router_rule", "dependency"},
    "status": {"proposed", "applied", "validated", "deferred", "rolled_back"},
}
IDENTIFIER_FIELDS = {
    "review_id", "task_id", "selected_skill", "better_route", "target_skill",
    "evidence_ref", "change_ref",
}
SUMMARY_FIELDS = {
    "observation", "previous_assumption", "revised_understanding",
    "before", "after", "trigger_when", "do_not_trigger_when",
}
FIELDS = set(ENUMS) | IDENTIFIER_FIELDS | SUMMARY_FIELDS | {"verification"}
OPTIONAL_FIELDS = {"verification_bundle", "feedback_scope"}
CHECK_FIELDS = {"status", "positive_case", "negative_case", "preserved_case", "evidence_ref"}
IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:@/+\-]{1,200}$")
SENSITIVE_PATTERN = re.compile(
    r"\bsk-(?:proj-)?[A-Za-z0-9_-]{12,}|\bgh[pousr]_[A-Za-z0-9]{20,}|"
    r"Bearer\s+\S+|-----BEGIN .*PRIVATE KEY-----|"
    r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|/Users/|/home/|"
    r"(?:api[_-]?key|password|cookie|secret|token)\s*[:=]\s*\S+",
    re.IGNORECASE,
)


class ReviewValidationError(ValueError):
    """Malformed evidence, unsupported state, or obviously private content."""


def _shape(value: object, fields: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise ReviewValidationError(f"{label} has missing or unknown fields")


def _text(value: object, field: str, *, identifier: bool = False) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 800:
        raise ReviewValidationError(f"{field} must be a bounded non-empty string")
    if any(ord(char) < 32 for char in value) or SENSITIVE_PATTERN.search(value):
        raise ReviewValidationError(f"{field} must contain sanitized single-line evidence")
    if identifier and not IDENTIFIER.fullmatch(value):
        raise ReviewValidationError(f"{field} must be a bounded identifier or relative reference")


def sanitize_review(payload: dict) -> dict:
    if not isinstance(payload, dict) or not FIELDS <= set(payload) or set(payload) - FIELDS - OPTIONAL_FIELDS:
        raise ReviewValidationError("review has missing or unknown fields")
    for field, value in payload.items():
        if field in {"verification", "verification_bundle"}:
            continue
        _text(value, field, identifier=field in IDENTIFIER_FIELDS)
        if field in ENUMS and value not in ENUMS[field]:
            raise ReviewValidationError(f"invalid {field}")
    if payload.get("feedback_scope", "single_task") not in {"single_task", "lasting_rule"}:
        raise ReviewValidationError("invalid feedback_scope")
    if "verification_bundle" in payload:
        rendered = json.dumps(payload["verification_bundle"], ensure_ascii=False)
        if len(rendered) > 16000 or SENSITIVE_PATTERN.search(rendered):
            raise ReviewValidationError("verification bundle must be bounded and sanitized")
    checks = payload["verification"]
    _shape(checks, CHECK_FIELDS, "verification")
    for field, value in checks.items():
        _text(value, f"verification.{field}", identifier=field == "evidence_ref")
    if checks["status"] not in {"not_run", "passed", "failed"}:
        raise ReviewValidationError("invalid verification status")
    if checks["status"] != "not_run" and checks["evidence_ref"] == "none":
        raise ReviewValidationError("executed checks need an evidence reference")
    if payload["evidence_level"] != "hypothesis" and payload["evidence_ref"] == "none":
        raise ReviewValidationError("observed or verified findings need an evidence reference")
    if payload["change_target"] != "none":
        needed = ["target_skill", "after", "trigger_when", "do_not_trigger_when"]
        if any(payload[field] == "none" for field in needed) or payload["before"] == payload["after"]:
            raise ReviewValidationError("a correction needs a target, changed rule, trigger, and exclusion")
        if any(checks[field] == "none" for field in ("positive_case", "negative_case", "preserved_case")):
            raise ReviewValidationError("a correction needs positive, negative, and preserved cases")
    if payload["status"] in {"applied", "validated", "rolled_back"}:
        if payload["change_ref"] == "none" or payload["change_target"] == "none":
            raise ReviewValidationError("a changed state needs a target and a change/rollback reference")
        if payload["evidence_level"] == "hypothesis":
            raise ReviewValidationError("an unverified hypothesis cannot be recorded as applied")
    if payload["status"] == "validated":
        if checks["status"] != "passed" or payload["evidence_level"] != "verified":
            raise ReviewValidationError("validated requires verified evidence and passing checks")
    return {**payload, "verification": dict(checks)}


def audit_verification(payload: dict, evidence_root: Path) -> dict:
    """Derived current state; never rewrite the historical claim."""
    from verification_evidence import verify_bundle

    if "verification_bundle" not in payload:
        return {"binding": "legacy_unbound", "automatic": "not_run", "ai": "not_run", "human": "not_run"}
    try:
        states = verify_bundle(payload["verification_bundle"], evidence_root)
        return {"binding": "current", **states}
    except (ValueError, OSError, TypeError) as exc:
        return {"binding": "unverifiable", "reason": str(exc), "automatic": "not_run", "ai": "not_run", "human": "not_run"}


def record_review(payload: dict, ledger: Path = DEFAULT_LEDGER, *, dry_run: bool = False,
                  evidence_root: Path | None = None) -> dict:
    clean = sanitize_review(payload)
    audit = audit_verification(clean, evidence_root or ledger.parent)
    if "verification_bundle" in clean and audit["binding"] != "current":
        raise ReviewValidationError("verification evidence is missing, changed, or invalid")
    if audit["binding"] == "current":
        dimensions = [audit[k] for k in ("automatic", "ai", "human")]
        expected = "failed" if "failed" in dimensions else "passed" if "passed" in dimensions else "not_run"
        if clean["verification"]["status"] != expected:
            raise ReviewValidationError("verification summary conflicts with bound dimensions")
    if clean["verification"]["status"] == "passed":
        dimensions = [audit[k] for k in ("automatic", "ai", "human")]
        if audit["binding"] != "current" or "passed" not in dimensions or "failed" in dimensions:
            raise ReviewValidationError("new passing claims require current bound evidence without failed dimensions")
    result = {"review_id": clean["review_id"], "status": clean["status"], "recorded": False}
    if dry_run:
        return {**result, "dry_run": True}
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.seek(0)
        for line in handle:
            if not line.strip():
                continue
            try:
                previous = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ReviewValidationError("invalid retrospective ledger; preserve it before repair") from exc
            if not isinstance(previous, dict):
                raise ReviewValidationError("invalid retrospective ledger record")
            if previous.get("review_id") == clean["review_id"]:
                comparable = {key: value for key, value in previous.items() if key != "recorded_at"}
                if comparable != clean:
                    raise ReviewValidationError("review_id already exists with different content; use a follow-up ID")
                return {**result, "duplicate": True}
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        handle.write(json.dumps({**clean, "recorded_at": timestamp}, ensure_ascii=False, sort_keys=True) + "\n")
    return {**result, "recorded": True}


def recent_reviews(ledger: Path, skill: str, limit: int = 5, *, evidence_root: Path | None = None) -> list[dict]:
    _text(skill, "skill", identifier=True)
    if not 1 <= limit <= 20:
        raise ReviewValidationError("limit must be between 1 and 20")
    if not ledger.exists():
        return []
    found: deque = deque(maxlen=limit)
    with ledger.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if skill in (row.get("selected_skill"), row.get("target_skill"), row.get("better_route")):
                found.append(row)
    return [{**row, "verification_audit": audit_verification(row, evidence_root or ledger.parent)} for row in found]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", required=True, help="exact skill identifier for recent matching lessons")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--evidence-root", type=Path, help="root for relative subject and receipt paths; defaults to ledger parent")
    args = parser.parse_args()
    print(json.dumps(recent_reviews(args.ledger, args.skill, args.limit, evidence_root=args.evidence_root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
