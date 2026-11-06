"""Behavioral checks for review evidence and CLI compatibility, not prompt wording."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

import task_retrospective as review


def finding(**changes):
    data = {
        "review_id": "review-a-01", "task_id": "task-a", "task_status": "completed",
        "category": "overconstraint", "selected_skill": "example-skill", "better_route": "direct-route",
        "evidence_level": "observed", "evidence_ref": "rule-inspection",
        "observation": "A full intake was required for an explicit local edit.",
        "previous_assumption": "Every edit needs an interview.",
        "revised_understanding": "Clarification depends on consequential uncertainty.",
        "change_target": "skill_body", "target_skill": "example-skill",
        "before": "Always interview.", "after": "Ask only for missing consequential details.",
        "trigger_when": "An unknown requirement changes the action.",
        "do_not_trigger_when": "The requested local change is explicit.",
        "status": "proposed", "change_ref": "none",
        "verification": {
            "status": "not_run", "positive_case": "Ambiguous target needs clarification.",
            "negative_case": "An exact typo edit proceeds.", "preserved_case": "Read-only remains read-only.",
            "evidence_ref": "none",
        },
    }
    data.update(changes)
    return data


@pytest.mark.parametrize("category", sorted(review.CATEGORIES))
def test_review_covers_different_causes_without_changing_route_or_skill(tmp_path, category):
    skill = tmp_path / "SKILL.md"
    skill.write_text("original rule")
    ledger = tmp_path / "reviews.jsonl"
    result = review.record_review(finding(category=category), ledger)
    assert result["recorded"] is True
    assert skill.read_text() == "original rule"
    assert json.loads(ledger.read_text())["status"] == "proposed"


def test_untried_outside_top3_alternative_is_retained_as_hypothesis(tmp_path):
    data = finding(category="retrieval_miss", better_route="previously-missed-skill", evidence_level="hypothesis")
    review.record_review(data, tmp_path / "reviews.jsonl")
    found = review.recent_reviews(tmp_path / "reviews.jsonl", "previously-missed-skill")
    assert found[0]["evidence_level"] == "hypothesis"
    assert found[0]["status"] == "proposed"


def test_ordinary_task_retrospective_word_is_not_misread_as_an_api_key():
    data = finding(before="No dedicated deterministic task-retrospective route.")
    assert review.sanitize_review(data)["before"] == data["before"]


@pytest.mark.parametrize("changes", [
    {"raw_prompt": "private"}, {"observation": "cookie=session-value"},
    {"observation": "sk-proj-123456789012345678901234"}, {"evidence_ref": "/Users/person/private"},
    {"observation": "contact person@example.com"}, {"observation": "first line\nsecond line"},
    {"status": "validated"}, {"status": "applied"},
    {"status": "applied", "change_ref": "patch-a", "evidence_level": "hypothesis"},
    {"trigger_when": "none"}, {"do_not_trigger_when": "none"}, {"after": "Always interview."},
])
def test_invalid_evidence_does_not_create_ledger(tmp_path, changes):
    ledger = tmp_path / "absent" / "reviews.jsonl"
    with pytest.raises(review.ReviewValidationError):
        review.record_review(finding(**changes), ledger)
    assert not ledger.parent.exists()


def test_passing_checks_and_change_reference_required_for_validated(tmp_path):
    from verification_evidence import run_check

    data = finding(status="validated", change_ref="patch-a", evidence_level="verified")
    data["verification"].update(status="passed", evidence_ref="check-report-a")
    (tmp_path / "subject.txt").write_text("checked version")
    check = run_check(tmp_path, ["subject.txt"], "receipt.json", [sys.executable, "-c", "pass"])
    data["verification_bundle"] = {"version": 1, "checks": [check]}
    assert review.record_review(data, tmp_path / "reviews.jsonl")["status"] == "validated"
    data["verification"]["status"] = "failed"
    with pytest.raises(review.ReviewValidationError):
        review.sanitize_review(data)


def test_duplicate_review_is_idempotent_and_conflict_preserves_history(tmp_path):
    ledger = tmp_path / "reviews.jsonl"
    data = finding()
    review.record_review(data, ledger)
    original = ledger.read_bytes()
    assert review.record_review(data, ledger)["duplicate"] is True
    with pytest.raises(review.ReviewValidationError):
        review.record_review(finding(observation="Different finding."), ledger)
    assert ledger.read_bytes() == original


def test_followup_keeps_history_and_reader_filters_and_limits(tmp_path):
    ledger = tmp_path / "reviews.jsonl"
    review.record_review(finding(), ledger)
    review.record_review(finding(review_id="review-a-02", status="deferred"), ledger)
    rows = review.recent_reviews(ledger, "example-skill", 1)
    assert rows[0]["status"] == "deferred"
    assert len(ledger.read_text().splitlines()) == 2
    assert review.recent_reviews(ledger, "unrelated-skill") == []


def test_dry_run_has_no_filesystem_side_effects(tmp_path):
    ledger = tmp_path / "absent" / "reviews.jsonl"
    result = review.record_review(finding(), ledger, dry_run=True)
    assert result["recorded"] is False
    assert result["dry_run"] is True
    assert not ledger.parent.exists()


def test_cli_review_can_write_then_validate_without_writing(tmp_path):
    script = Path(__file__).with_name("post_task_reflection.py")
    event = tmp_path / "review.json"
    event.write_text(json.dumps(finding()))
    ledger = tmp_path / "reviews.jsonl"
    command = [sys.executable, str(script), "--review", str(event), "--ledger", str(ledger)]
    checked = subprocess.run(command + ["--dry-run"], text=True, capture_output=True, check=True)
    assert json.loads(checked.stdout)["recorded"] is False
    assert not ledger.exists()
    saved = subprocess.run(command, text=True, capture_output=True, check=True)
    assert json.loads(saved.stdout)["recorded"] is True


def test_cli_legacy_feedback_contract_unchanged(tmp_path):
    from test_router_feedback import event

    script = Path(__file__).with_name("post_task_reflection.py")
    payload = tmp_path / "event.json"
    payload.write_text(json.dumps(event()))
    ledger = tmp_path / "legacy.jsonl"
    command = [sys.executable, str(script), "--event", str(payload), "--ledger", str(ledger)]
    subprocess.run(command + ["--dry-run"], text=True, capture_output=True, check=True)
    assert not ledger.exists()
    result = subprocess.run(command, text=True, capture_output=True, check=True)
    assert json.loads(result.stdout)["recorded"] is True
    assert json.loads(ledger.read_text()) == event()
