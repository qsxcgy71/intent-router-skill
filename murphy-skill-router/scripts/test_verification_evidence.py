"""Check real receipt execution, stale evidence, legacy reading and review boundaries."""
import json
import sys
import subprocess
from pathlib import Path

import pytest

import task_retrospective as review
from test_task_retrospective import finding
from verification_evidence import EvidenceError, fingerprint, run_check, verify_bundle


def passing(tmp_path):
    (tmp_path / "subject.txt").write_text("original")
    check = run_check(tmp_path, ["subject.txt"], "receipt.json", [sys.executable, "-c", "pass"])
    return {"version": 1, "checks": [check]}


def validated(bundle):
    data = finding(status="validated", change_ref="patch-a", evidence_level="verified")
    data["verification"].update(status="passed", evidence_ref="receipt.json")
    data.update(verification_bundle=bundle, feedback_scope="single_task")
    return data


def test_real_command_receipt_does_not_imply_ai_or_human_approval(tmp_path):
    bundle = passing(tmp_path)
    assert verify_bundle(bundle, tmp_path) == {"automatic": "passed", "ai": "not_run", "human": "not_run"}
    ledger = tmp_path / "reviews.jsonl"
    review.record_review(validated(bundle), ledger)
    assert review.recent_reviews(ledger, "example-skill")[0]["verification_audit"]["binding"] == "current"


@pytest.mark.parametrize("changed", ["subject.txt", "receipt.json"])
def test_changes_invalidate_evidence_and_block_new_claims(tmp_path, changed):
    bundle = passing(tmp_path)
    ledger = tmp_path / "reviews.jsonl"
    review.record_review(validated(bundle), ledger)
    original = ledger.read_bytes()
    (tmp_path / changed).write_text("changed")
    assert review.recent_reviews(ledger, "example-skill")[0]["verification_audit"]["binding"] == "unverifiable"
    with pytest.raises(review.ReviewValidationError):
        review.record_review(validated(bundle), ledger, dry_run=True)
    assert ledger.read_bytes() == original


def test_missing_receipt_rejected_and_no_ledger_created(tmp_path):
    bundle = passing(tmp_path)
    (tmp_path / "receipt.json").unlink()
    ledger = tmp_path / "new.jsonl"
    with pytest.raises(review.ReviewValidationError):
        review.record_review(validated(bundle), ledger)
    assert not ledger.exists()


def test_legacy_claims_read_without_retroactive_upgrade(tmp_path):
    data = finding(status="validated", change_ref="old-change", evidence_level="verified")
    data["verification"].update(status="passed", evidence_ref="old-report")
    ledger = tmp_path / "old.jsonl"
    ledger.write_text(json.dumps(data) + "\n")
    original = ledger.read_bytes()
    row = review.recent_reviews(ledger, "example-skill")[0]
    assert row["status"] == "validated"
    assert row["verification_audit"]["binding"] == "legacy_unbound"
    with pytest.raises(review.ReviewValidationError):
        review.record_review(data, tmp_path / "new.jsonl")
    assert ledger.read_bytes() == original


def test_failure_cannot_be_saved_as_passed(tmp_path):
    (tmp_path / "subject.txt").write_text("original")
    check = run_check(tmp_path, ["subject.txt"], "failure.json", [sys.executable, "-c", "raise SystemExit(3)"])
    bundle = {"version": 1, "checks": [check]}
    assert verify_bundle(bundle, tmp_path)["automatic"] == "failed"
    with pytest.raises(review.ReviewValidationError):
        review.record_review(validated(bundle), tmp_path / "reviews.jsonl")


@pytest.mark.parametrize("kind", ["ai", "human"])
def test_assessment_artifact_is_separate_and_bound(tmp_path, kind):
    bundle = passing(tmp_path)
    (tmp_path / "assessment.md").write_text("Synthetic assessment; no real user approval claimed.")
    receipt_path = tmp_path / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt.update(kind=kind, method="synthetic assessment fixture", assessment={"path": "assessment.md", "sha256": fingerprint(tmp_path / "assessment.md")})
    receipt_path.write_text(json.dumps(receipt))
    bundle["checks"][0].update(kind=kind, sha256=fingerprint(receipt_path))
    result = verify_bundle(bundle, tmp_path)
    assert result[kind] == "passed" and result["automatic"] == "not_run"
    (tmp_path / "assessment.md").write_text("revised judgment")
    with pytest.raises(EvidenceError):
        verify_bundle(bundle, tmp_path)


def test_receipt_cannot_escape_root_even_through_symlink(tmp_path):
    bundle = passing(tmp_path)
    bundle["checks"][0]["receipt"] = "../receipt.json"
    with pytest.raises(EvidenceError):
        verify_bundle(bundle, tmp_path)
    (tmp_path / "outside").symlink_to(tmp_path.parent, target_is_directory=True)
    bundle["checks"][0]["receipt"] = "outside/receipt.json"
    with pytest.raises(EvidenceError):
        verify_bundle(bundle, tmp_path)


def test_existing_receipt_is_not_overwritten(tmp_path):
    passing(tmp_path)
    old = (tmp_path / "receipt.json").read_bytes()
    with pytest.raises(EvidenceError):
        run_check(tmp_path, ["subject.txt"], "receipt.json", [sys.executable, "-c", "pass"])
    assert (tmp_path / "receipt.json").read_bytes() == old


def test_subject_changed_by_command_does_not_get_a_pass(tmp_path):
    (tmp_path / "subject.txt").write_text("original")
    with pytest.raises(EvidenceError):
        run_check(tmp_path, ["subject.txt"], "receipt.json", [sys.executable, "-c", "from pathlib import Path; Path('subject.txt').write_text('changed')"])
    assert not (tmp_path / "receipt.json").exists()


def test_timeout_is_failed(tmp_path):
    (tmp_path / "subject.txt").write_text("original")
    check = run_check(tmp_path, ["subject.txt"], "receipt.json", [sys.executable, "-c", "import time; time.sleep(1)"], timeout=0.01)
    assert check["status"] == "failed"


def test_explicit_root_and_dry_run_do_not_write_ledger(tmp_path):
    bundle = passing(tmp_path)
    ledger = tmp_path / "nested" / "reviews.jsonl"
    result = review.record_review(validated(bundle), ledger, evidence_root=tmp_path, dry_run=True)
    assert result["recorded"] is False and not ledger.parent.exists()


def test_one_task_feedback_not_silently_promoted_to_lasting_rule(tmp_path):
    bundle = passing(tmp_path)
    ledger = tmp_path / "reviews.jsonl"
    review.record_review(validated(bundle), ledger)
    assert review.recent_reviews(ledger, "example-skill")[0]["feedback_scope"] == "single_task"
    data = validated(bundle)
    data["feedback_scope"] = "automatic-global-rule"
    with pytest.raises(review.ReviewValidationError):
        review.record_review(data, ledger)


def test_cli_passed_review_requires_bound_evidence_with_explicit_root(tmp_path):
    bundle = passing(tmp_path)
    payload = tmp_path / "review.json"
    payload.write_text(json.dumps(validated(bundle)))
    script = Path(__file__).with_name("post_task_reflection.py")
    ledger = tmp_path / "nested" / "reviews.jsonl"
    command = [sys.executable, str(script), "--review", str(payload), "--ledger", str(ledger), "--evidence-root", str(tmp_path)]
    checked = subprocess.run(command + ["--dry-run"], capture_output=True, text=True, check=True)
    assert json.loads(checked.stdout)["recorded"] is False and not ledger.exists()
    subprocess.run(command, capture_output=True, text=True, check=True)
    reader = Path(__file__).with_name("task_retrospective.py")
    read = subprocess.run([sys.executable, str(reader), "--skill", "example-skill", "--ledger", str(ledger), "--evidence-root", str(tmp_path)], capture_output=True, text=True, check=True)
    assert json.loads(read.stdout)[0]["verification_audit"]["automatic"] == "passed"


def test_summary_cannot_disagree_with_dimensions(tmp_path):
    data = validated(passing(tmp_path))
    data.update(status="proposed")
    data["verification"]["status"] = "not_run"
    with pytest.raises(review.ReviewValidationError):
        review.record_review(data, tmp_path / "reviews.jsonl")
