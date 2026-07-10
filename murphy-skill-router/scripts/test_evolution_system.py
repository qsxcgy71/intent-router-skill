#!/usr/bin/env python3
"""Smoke tests for the router self-evolution toolchain.

These tests copy the skill into a temporary directory and exercise the public
CLI scripts. They avoid touching the live skill directory.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def copy_skill() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="router-evolution-test-"))
    dst = tmp / "skill"
    ignore = shutil.ignore_patterns("releases", "candidates", "__pycache__")
    shutil.copytree(SKILL_DIR, dst, ignore=ignore)
    return dst


def make_candidate(skill: Path, name: str) -> Path:
    candidate = skill / "candidates" / name
    candidate.mkdir(parents=True, exist_ok=True)
    shutil.copy2(skill / "SKILL.md", candidate / "SKILL.md")
    shutil.copytree(skill / "references", candidate / "references")
    shutil.copytree(skill / "scripts", candidate / "scripts")
    return candidate


def test_v2_suite_eval_all() -> None:
    skill = copy_skill()
    result = run(["scripts/eval_router_v2.py", "--suite", "all", "--show-failures"], skill)
    assert result.returncode == 0, result.stdout
    assert "safety: cases=20 top1=19/20 hit@3=20/20" in result.stdout, result.stdout


def test_gate_rejects_deleted_cost_gate() -> None:
    skill = copy_skill()
    candidate = make_candidate(skill, "bad-delete-cost-gate")
    skill_md = candidate / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    text = text.replace("## Cost And External Side-Effect Gate", "## Cost Gate Removed")
    skill_md.write_text(text, encoding="utf-8")

    result = run(["scripts/evolution_gate.py", "--candidate", str(candidate), "--suite", "all"], skill)
    assert result.returncode != 0, result.stdout
    assert "required safety phrase missing" in result.stdout, result.stdout


def test_gate_accepts_noop_v2_candidate() -> None:
    skill = copy_skill()
    candidate = make_candidate(skill, "noop-good")

    gate = run(["scripts/evolution_gate.py", "--candidate", str(candidate), "--suite", "all"], skill)
    assert gate.returncode == 0, gate.stdout
    assert "Decision: accepted" in gate.stdout, gate.stdout
    assert "recommendation-only" in gate.stdout, gate.stdout


def test_gate_rejects_frozen_heldout_tamper() -> None:
    skill = copy_skill()
    candidate = make_candidate(skill, "bad-heldout-tamper")
    path = candidate / "references" / "router-eval-heldout.json"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    gate = run(["scripts/evolution_gate.py", "--candidate", str(candidate), "--suite", "all"], skill)
    assert gate.returncode != 0, gate.stdout
    assert "frozen eval checksum mismatch" in gate.stdout, gate.stdout


def test_auto_promotion_is_disabled_and_pointer_unchanged() -> None:
    skill = copy_skill()
    candidate = make_candidate(skill, "noop-no-auto")
    before = (skill / "current-release.json").read_text(encoding="utf-8")

    promote = run(["scripts/promote_router_candidate.py", "--candidate", str(candidate), "--auto"], skill)
    assert promote.returncode != 0, promote.stdout
    assert "automatic promotion disabled" in promote.stdout, promote.stdout
    assert (skill / "current-release.json").read_text(encoding="utf-8") == before


def test_copy_core_tree_keeps_v2_runtime_files() -> None:
    skill = copy_skill()
    sys.path.insert(0, str(skill / "scripts"))
    try:
        import router_evolution_lib as lib

        destination = skill / "releases" / "copy-check"
        lib.copy_core_tree(skill, destination, include_scripts=True)
    finally:
        sys.path.pop(0)
    for rel in (
        "references/capability-catalog.json",
        "references/capability-overrides.json",
        "references/router-v2-rules.json",
        "references/router-eval-ambiguity.json",
        "references/router-eval-feedback.json",
        "references/route-feedback.schema.json",
        "references/router-preference-overlay.json",
        "scripts/router_v2.py",
        "scripts/eval_router_v2.py",
        "scripts/shadow_route.py",
        "scripts/post_task_reflection.py",
        "scripts/build_preference_overlay.py",
    ):
        assert (destination / rel).exists(), rel
    assert not (destination / "references" / "route-feedback.jsonl").exists()


def test_manual_promotion_and_rollback_use_full_snapshot_in_temp() -> None:
    skill = copy_skill()
    candidate = make_candidate(skill, "manual-approved")
    promoted = run(
        [
            "scripts/promote_router_candidate.py",
            "--candidate",
            str(candidate),
            "--approved-by-user",
        ],
        skill,
    )
    assert promoted.returncode == 0, promoted.stdout
    state = json.loads((skill / "current-release.json").read_text(encoding="utf-8"))
    assert state["strategy"] == "manual_approval_after_gate"
    assert state["rollback_release"] != "baseline-2026-06-17"
    assert (skill / "releases" / state["rollback_release"] / "scripts" / "evolution_gate.py").exists()

    target = state["rollback_release"]
    rolled_back = run(["scripts/promote_router_candidate.py", "--rollback"], skill)
    assert rolled_back.returncode == 0, rolled_back.stdout
    after = json.loads((skill / "current-release.json").read_text(encoding="utf-8"))
    assert after["current_release"] == target


def test_promotion_initializes_empty_runtime_feedback_ledger() -> None:
    skill = copy_skill()
    ledger = skill / "references" / "route-feedback.jsonl"
    ledger.unlink()
    candidate = make_candidate(skill, "feedback-ledger")
    promoted = run(
        [
            "scripts/promote_router_candidate.py",
            "--candidate",
            str(candidate),
            "--approved-by-user",
        ],
        skill,
    )
    assert promoted.returncode == 0, promoted.stdout
    assert ledger.exists()
    assert ledger.read_text(encoding="utf-8") == ""


def test_quick_validate_candidate() -> None:
    skill = copy_skill()
    result = run(["scripts/quick_validate.py", str(skill)], skill)
    assert result.returncode == 0, result.stdout
    assert "quick-validation: ok" in result.stdout, result.stdout


def test_gate_surfaces_declared_guard_script_review() -> None:
    skill = copy_skill()
    candidate = make_candidate(skill, "guard-review")
    (candidate / "candidate-summary.json").write_text(
        json.dumps({"guard_scripts_changed": ["evolution_gate.py", "promote_router_candidate.py"]}),
        encoding="utf-8",
    )
    gate = run(["scripts/evolution_gate.py", "--candidate", str(candidate), "--suite", "all"], skill)
    assert gate.returncode == 0, gate.stdout
    assert "manual guard-script review required: scripts/evolution_gate.py" in gate.stdout
    assert "manual guard-script review required: scripts/promote_router_candidate.py" in gate.stdout


def test_gate_dot_candidate_report_has_nonempty_name() -> None:
    skill = copy_skill()
    gate = run(
        ["scripts/evolution_gate.py", "--candidate", ".", "--suite", "all", "--write-report"],
        skill,
    )
    assert gate.returncode == 0, gate.stdout
    assert "router-v3-gate-.md" not in gate.stdout, gate.stdout
    assert f"router-v3-gate-{skill.name}.md" in gate.stdout, gate.stdout


def main() -> int:
    tests = [
        test_v2_suite_eval_all,
        test_gate_rejects_deleted_cost_gate,
        test_gate_accepts_noop_v2_candidate,
        test_gate_rejects_frozen_heldout_tamper,
        test_auto_promotion_is_disabled_and_pointer_unchanged,
        test_copy_core_tree_keeps_v2_runtime_files,
        test_manual_promotion_and_rollback_use_full_snapshot_in_temp,
        test_promotion_initializes_empty_runtime_feedback_ledger,
        test_quick_validate_candidate,
        test_gate_surfaces_declared_guard_script_review,
        test_gate_dot_candidate_report_has_nonempty_name,
    ]
    failures = []
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures.append((test.__name__, str(exc)))
    if failures:
        for name, detail in failures:
            print(f"FAIL {name}\n{detail}\n")
        return 1
    print(f"{len(tests)} tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
