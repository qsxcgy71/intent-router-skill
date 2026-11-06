#!/usr/bin/env python3
"""Offline, standard-library-only comparison of before/after review recorders."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRIPTS = REPO / "murphy-skill-router/scripts"
sys.path.insert(0, str(SCRIPTS))
from verification_evidence import run_check, fingerprint


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BEFORE = load("before_recorder", HERE / "fixtures/pre_upgrade_recorder.py")
AFTER = load("after_recorder", SCRIPTS / "task_retrospective.py")


def payload():
    return {
        "review_id": "synthetic-review", "task_id": "synthetic-task", "task_status": "completed",
        "category": "skill_gap", "selected_skill": "example-skill", "better_route": "none",
        "evidence_level": "verified", "evidence_ref": "receipt.json",
        "observation": "Synthetic evidence validation experiment.",
        "previous_assumption": "Reference text was sufficient.",
        "revised_understanding": "A current receipt binds the checked subject.",
        "change_target": "skill_body", "target_skill": "example-skill",
        "before": "Check declaration.", "after": "Check bound evidence.",
        "trigger_when": "A passing verification is recorded.",
        "do_not_trigger_when": "No change or passing claim exists.",
        "status": "validated", "change_ref": "synthetic-change",
        "verification": {"status": "passed", "positive_case": "Valid proof.",
            "negative_case": "Stale proof.", "preserved_case": "Legacy read.", "evidence_ref": "receipt.json"},
    }


def setup(root, case):
    (root / "subject.txt").write_text("synthetic checked content\n")
    command = [sys.executable, "-c", "raise SystemExit(7)" if case == "failed_command" else "pass"]
    check = run_check(root, ["subject.txt"], "receipt.json", command)
    item = payload()
    item["verification_bundle"] = {"version": 1, "checks": [check]}
    if case == "missing_receipt":
        (root / "receipt.json").unlink()
    elif case == "changed_subject":
        (root / "subject.txt").write_text("new version")
    elif case == "changed_receipt":
        (root / "receipt.json").write_text("replaced report")
    elif case == "unbound_pass":
        del item["verification_bundle"]
    elif case == "no_executed_checks":
        item["verification_bundle"]["checks"] = [{"kind": "automatic", "status": "not_run"}]
    elif case == "outside_root":
        check["receipt"] = "../receipt.json"
    elif case == "conflicting_summary":
        item["status"] = "proposed"
        item["verification"]["status"] = "not_run"
    elif case == "changed_ai_assessment":
        artifact = root / "assessment.md"
        artifact.write_text("Synthetic AI fixture; not an actual assessment.")
        receipt = json.loads((root / "receipt.json").read_text())
        receipt.update(kind="ai", assessment={"path": "assessment.md", "sha256": fingerprint(artifact)})
        (root / "receipt.json").write_text(json.dumps(receipt))
        check.update(kind="ai", sha256=fingerprint(root / "receipt.json"))
        artifact.write_text("Changed assessment")
    elif case == "legacy_proposal":
        del item["verification_bundle"]
        item.update(status="proposed", evidence_level="hypothesis")
        item["verification"]["status"] = "not_run"
    elif case == "sensitive_summary":
        item["observation"] = "cookie=synthetic-secret"
    return item


def adapt(item, version):
    # Same artifacts and claim; the old API has no bundle field. Passing an unknown
    # field would only test schema rejection, not the old verifier's behavior.
    return {k: v for k, v in item.items() if version == "after" or k != "verification_bundle"}


def attempt(module, item, ledger, dry_run=False):
    try:
        result = module.record_review(item, ledger, dry_run=dry_run)
        return True, result
    except (ValueError, OSError, TypeError):
        return False, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timing-repeats", type=int, default=100)
    args = parser.parse_args()
    if args.timing_repeats < 1:
        parser.error("timing repeats must be positive")
    cases = {
        "valid_pass": True, "legacy_proposal": True, "sensitive_summary": False,
        "missing_receipt": False, "changed_subject": False, "changed_receipt": False,
        "failed_command": False, "unbound_pass": False, "no_executed_checks": False,
        "outside_root": False, "conflicting_summary": False, "changed_ai_assessment": False,
    }
    rows, compatibility, drift, timing, trust_control = [], [], [], {}, []
    with tempfile.TemporaryDirectory(prefix="router-comparison-") as name:
        temp = Path(name)
        for case, expected in cases.items():
            row = {"case": case, "expected_accept": expected}
            for version, module in (("before", BEFORE), ("after", AFTER)):
                root = temp / f"{case}-{version}"
                root.mkdir()
                item = adapt(setup(root, case), version)
                accepted, _ = attempt(module, item, root / "reviews.jsonl")
                row[version + "_accept"] = accepted
                row[version + "_correct"] = accepted == expected
            rows.append(row)
        for version, module in (("before", BEFORE), ("after", AFTER)):
            root = temp / f"compat-{version}"
            root.mkdir()
            item = adapt(setup(root, "valid_pass"), version)
            ledger = root / "reviews.jsonl"
            accepted, result = attempt(module, item, ledger, dry_run=True)
            dry_ok = accepted and not result["recorded"] and not ledger.exists()
            module.record_review(item, ledger)
            original = ledger.read_bytes()
            duplicate = module.record_review(item, ledger)
            duplicate_ok = duplicate.get("duplicate") is True and ledger.read_bytes() == original
            old = payload()
            legacy = root / "legacy.jsonl"
            legacy.write_text(json.dumps(old) + "\n")
            old_bytes = legacy.read_bytes()
            read = module.recent_reviews(legacy, "example-skill")
            legacy_ok = read[0]["status"] == "validated" and legacy.read_bytes() == old_bytes
            compatibility.append({"version": version, "dry_run_no_write": dry_ok, "duplicate_idempotent": duplicate_ok, "legacy_read_preserved": legacy_ok})
            (root / "subject.txt").write_text("changed after recording")
            row = module.recent_reviews(ledger, "example-skill")[0]
            drift.append({"version": version, "changed_subject_flagged": row.get("verification_audit", {}).get("binding") == "unverifiable", "history_unchanged": ledger.read_bytes() == original})
            root = temp / f"timing-{version}"
            root.mkdir()
            item = adapt(setup(root, "valid_pass"), version)
            samples = []
            for _ in range(10):
                module.record_review(item, root / "reviews.jsonl", dry_run=True)
            for _ in range(args.timing_repeats):
                start = time.perf_counter_ns()
                module.record_review(item, root / "reviews.jsonl", dry_run=True)
                samples.append((time.perf_counter_ns() - start) / 1_000_000)
            timing[version] = {"repeats": len(samples), "median_ms": statistics.median(samples), "p95_ms": sorted(samples)[max(0, int(len(samples)*0.95)-1)]}
            # Negative control: no actual check command runs here. Hash binding
            # is not author authentication and must not be sold as such.
            root = temp / f"untrusted-{version}"
            root.mkdir()
            (root / "subject.txt").write_text("synthetic subject")
            fabricated = {"version": 1, "kind": "automatic", "status": "passed",
                "checked_at": "2026-11-07T00:00:00+08:00", "method": "fabricated-success",
                "exit_code": 0, "subjects": [{"path": "subject.txt", "sha256": fingerprint(root / "subject.txt")}]}
            (root / "receipt.json").write_text(json.dumps(fabricated))
            item = payload()
            item["verification_bundle"] = {"version": 1, "checks": [{"kind": "automatic", "status": "passed", "receipt": "receipt.json", "sha256": fingerprint(root / "receipt.json")}]}
            accepted, _ = attempt(module, adapt(item, version), root / "reviews.jsonl")
            trust_control.append({"version": version, "fabricated_consistent_receipt_accepted": accepted})
    checked = [HERE / "fixtures/pre_upgrade_recorder.py", SCRIPTS / "task_retrospective.py", SCRIPTS / "verification_evidence.py", Path(__file__)]
    result = {
        "method": "12 constructed scenarios, API-adapted inputs; not a random or production sample",
        "baseline": "Immediate pre-upgrade local recorder snapshot; not the older GitHub main version",
        "runtime": {"python": platform.python_version(), "os": platform.system(), "machine": platform.machine()},
        "source_sha256": {p.relative_to(REPO).as_posix(): fingerprint(p) for p in checked},
        "scenarios": rows, "compatibility": compatibility, "readback_drift": drift,
        "untrusted_receipt_control": trust_control,
        "timing_dry_run_one_subject_one_receipt": timing,
        "summary": {v: {"correct": sum(r[v+"_correct"] for r in rows), "total": len(rows), "invalid_accepts": sum(r[v+"_accept"] and not r["expected_accept"] for r in rows), "valid_rejects": sum(not r[v+"_accept"] and r["expected_accept"] for r in rows)} for v in ("before", "after")},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"summary": result["summary"], "timing": timing}, indent=2))
    return 0 if all(r["after_correct"] for r in rows) and all(all(value for key,value in r.items() if key != "version") for r in compatibility) and drift[1]["changed_subject_flagged"] and all(r["history_unchanged"] for r in drift) else 1


if __name__ == "__main__":
    raise SystemExit(main())
