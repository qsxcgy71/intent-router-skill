#!/usr/bin/env python3
"""Focused Router v3 post-task feedback safety tests."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
REFERENCES_DIR = SKILL_DIR / "references"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_preference_overlay as overlay_builder
import post_task_reflection as reflection
import router_v2


def load_json(name: str) -> dict:
    return json.loads((REFERENCES_DIR / name).read_text(encoding="utf-8"))


def event(**changes) -> dict:
    base = {
        "event_id": "event-001",
        "decision_id": "decision-001",
        "context_key": "frontend_design:frontend-design-explicit:workspace_write",
        "task_id": "task-001",
        "intent_family": "frontend_design",
        "recommended_skill": "frontend-design",
        "final_skill": "superpowers:writing-skills",
        "outcome": "corrected_success",
        "failure_class": "route_miss",
        "evidence_source": "explicit_user_correction",
        "verification_status": "verified_success",
        "risk_class": "workspace_write",
        "availability_status": "available",
        "release_id": "candidate-r3",
        "catalog_fingerprint": "catalog-a",
        "final_skill_fingerprint": "skill-a",
        "timestamp": "2026-07-10T08:00:00Z",
    }
    base.update(changes)
    return base


@pytest.mark.parametrize(
    "forbidden",
    ["query", "raw_prompt", "notes", "email_body", "diary_body", "cookie", "token", "secret"],
)
def test_feedback_rejects_raw_or_sensitive_fields(forbidden: str) -> None:
    payload = event(**{forbidden: "private material"})
    with pytest.raises(reflection.FeedbackValidationError):
        reflection.sanitize_event(payload)


def test_non_route_failures_and_model_advice_never_activate() -> None:
    rows = [
        event(event_id="dep", failure_class="dependency_miss"),
        event(event_id="exec", failure_class="execution_failure"),
        event(event_id="changed", failure_class="intent_changed"),
        event(event_id="amb", failure_class="ambiguous"),
        event(event_id="model", evidence_source="model_advisory"),
    ]
    profile = overlay_builder.build_overlay(rows, now="2026-07-10T09:00:00Z")
    assert profile["active_preferences"] == {}
    assert profile["summary"]["active"] == 0


def test_explicit_verified_correction_activates_for_30_days() -> None:
    profile = overlay_builder.build_overlay([event()], now="2026-07-10T09:00:00Z")
    pref = profile["active_preferences"][event()["context_key"]]
    assert pref["preferred_skill"] == "superpowers:writing-skills"
    assert pref["state"] == "active"
    assert pref["evidence_count"] == 1
    assert pref["expires_at"] == "2026-08-09T08:00:00Z"


def test_agent_inference_needs_three_unique_events_across_two_tasks() -> None:
    rows = [
        event(event_id="a1", task_id="t1", evidence_source="agent_inference"),
        event(event_id="a2", task_id="t1", evidence_source="agent_inference"),
    ]
    shadow = overlay_builder.build_overlay(rows, now="2026-07-10T09:00:00Z")
    assert shadow["active_preferences"] == {}
    rows.append(event(event_id="a3", task_id="t2", evidence_source="agent_inference"))
    active = overlay_builder.build_overlay(rows, now="2026-07-10T09:00:00Z")
    assert event()["context_key"] in active["active_preferences"]


def test_duplicates_do_not_add_evidence_and_conflicts_quarantine() -> None:
    duplicate = event()
    duplicate_again = dict(duplicate)
    other = event(event_id="other", final_skill="frontend-ui-engineering", final_skill_fingerprint="skill-b")
    profile = overlay_builder.build_overlay(
        [duplicate, duplicate_again, other], now="2026-07-10T09:00:00Z"
    )
    assert profile["summary"]["duplicates_ignored"] == 1
    assert event()["context_key"] in profile["quarantined"]
    assert profile["active_preferences"] == {}


def test_feedback_log_contains_only_schema_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "feedback.jsonl"
        clean = reflection.record_event(event(), path)
        rendered = path.read_text(encoding="utf-8")
    assert json.loads(rendered) == clean
    assert set(clean) == reflection.ALLOWED_FIELDS
    assert "private material" not in rendered


def _route(query: str, **kwargs) -> dict:
    return router_v2.route_decision(
        query,
        catalog=load_json("capability-catalog.json"),
        rules=load_json("router-v2-rules.json"),
        **kwargs,
    )


def _profile_for(base: dict, target: str, **changes) -> dict:
    catalog = load_json("capability-catalog.json")
    target_doc = catalog.get("capabilities", {}).get(target, {})
    pref = {
        "preferred_skill": target,
        "state": "active",
        "evidence_count": 1,
        "task_count": 1,
        "evidence_source": "explicit_user_correction",
        "release_id": "candidate-r3",
        "catalog_fingerprint": router_v2.catalog_fingerprint(catalog),
        "preferred_skill_fingerprint": target_doc.get("source_fingerprint", ""),
        "created_at": "2026-07-10T08:00:00Z",
        "expires_at": "2026-08-09T08:00:00Z",
    }
    pref.update(changes)
    return {
        "version": 1,
        "mode": "shadow_preference_overlay",
        "active_preferences": {base["reflection_advisory"]["context_key"]: pref},
    }


def test_empty_or_disabled_overlay_preserves_v2_core_decision() -> None:
    query = "这个页面不像能上线，请重做视觉方向。"
    base = _route(query, preference_profile={"active_preferences": {}})
    disabled = _route(
        query,
        preference_profile={"enabled": False, "active_preferences": {base["reflection_advisory"]["context_key"]: {}}},
    )
    core = [
        "intent_family",
        "candidate_skills",
        "selected_skill",
        "confidence",
        "requires_confirmation",
        "risk_class",
        "availability_status",
        "fallback",
        "short_reason",
        "execution_authorized",
    ]
    assert {key: base[key] for key in core} == {key: disabled[key] for key in core}
    assert disabled["reflection_advisory"]["applied"] is False


def test_overlay_only_reranks_available_existing_top3() -> None:
    query = "这个页面不像能上线，请重做视觉方向。"
    base = _route(query, preference_profile={"active_preferences": {}})
    target = base["candidate_skills"][1]["skill"]
    applied = _route(query, preference_profile=_profile_for(base, target))
    assert applied["selected_skill"] == target
    assert applied["reflection_advisory"]["applied"] is True
    assert applied["execution_authorized"] is False

    outside = _route(query, preference_profile=_profile_for(base, "security-and-hardening"))
    assert outside["selected_skill"] == base["selected_skill"]
    assert outside["reflection_advisory"]["reason_code"] == "target_not_in_base_top3"


def test_stale_or_expired_preference_fails_closed() -> None:
    query = "这个页面不像能上线，请重做视觉方向。"
    base = _route(query, preference_profile={"active_preferences": {}})
    target = base["candidate_skills"][1]["skill"]
    expired = _profile_for(base, target, expires_at="2026-07-09T00:00:00Z")
    stale = _profile_for(base, target, catalog_fingerprint="wrong")
    assert _route(query, preference_profile=expired)["selected_skill"] == base["selected_skill"]
    assert _route(query, preference_profile=stale)["selected_skill"] == base["selected_skill"]


def test_overlay_cannot_override_protected_routes_or_lower_safety() -> None:
    protected_query = "连接真实券商账户后执行一笔交易。"
    base = _route(protected_query, preference_profile={"active_preferences": {}})
    target = base["candidate_skills"][1]["skill"]
    result = _route(protected_query, preference_profile=_profile_for(base, target))
    assert result["selected_skill"] == base["selected_skill"]
    assert result["risk_class"] == "financial"
    assert result["requires_confirmation"] is True
    assert result["reflection_advisory"]["reason_code"] == "protected_risk"


def test_overlay_target_unavailable_is_not_applied() -> None:
    query = "这个页面不像能上线，请重做视觉方向。"
    base = _route(query, preference_profile={"active_preferences": {}})
    target = base["candidate_skills"][1]["skill"]
    catalog = load_json("capability-catalog.json")
    catalog.setdefault("capabilities", {}).setdefault(target, {})["availability"] = {
        "kind": "runtime_connector",
        "name": "missing-test-connector",
    }
    profile = _profile_for(base, target)
    profile["active_preferences"][base["reflection_advisory"]["context_key"]][
        "catalog_fingerprint"
    ] = router_v2.catalog_fingerprint(catalog)
    result = router_v2.route_decision(
        query,
        catalog=catalog,
        rules=load_json("router-v2-rules.json"),
        availability={},
        preference_profile=profile,
    )
    assert result["selected_skill"] == base["selected_skill"]
    assert result["reflection_advisory"]["reason_code"] == "target_unavailable"
