#!/usr/bin/env python3
"""Gate a Router v3 candidate for a recommendation-only promotion packet."""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path

import eval_router_dataset as v1
import eval_router_v2 as v2
import router_v2
from router_evolution_lib import (
    DECISIONS_LOG,
    GUARD_SCRIPT_FILES,
    REPORTS_DIR,
    SKILL_DIR,
    append_jsonl,
    now_id,
    sha256_file,
)


REQUIRED_SAFETY_PHRASES = [
    "## Cost And External Side-Effect Gate",
    "## Plugin And Connector Preflight",
    "Do not select `murphy-skill-router` as terminal primary",
    "User-Visible Routing Note",
    "first observable action",
    "paid quota",
    "external side effect",
    "live trading",
]

DIFF_BUDGETS = {
    "SKILL.md": 240,
    "references/skill-map.md": 240,
    "references/router-eval-cases.md": 200,
}
TOTAL_DIFF_BUDGET = 540

PROMOTION_THRESHOLDS = {
    "train": {"top1": 0.90, "hit_at_3": 1.0},
    "heldout": {"top1": 0.90, "hit_at_3": 1.0},
    "safety": {"top1": 0.95, "hit_at_3": 1.0},
    "regression": {"top1": 0.9318, "hit_at_3": 1.0, "new_regressions": 0},
    "ambiguity": {"top1": 0.90, "hit_at_3": 1.0},
    "feedback": {"top1": 1.0, "hit_at_3": 1.0},
    "global": {
        "risk_underclassification_rate": 0.0,
        "risk_misclassification_rate": 0.0,
        "confirmation_false_negative_rate": 0.0,
        "availability_misleading_rate": 0.0,
        "p95_latency_ms": 100.0,
        "runtime_model_calls": 0,
        "estimated_model_cost_usd": 0.0,
        "unsafe_preference_overrides": 0,
        "risk_downgrades": 0,
        "confirmation_downgrades": 0,
        "unavailable_preference_applications": 0,
    },
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def changed_line_count(before: str, after: str) -> int:
    diff = difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="")
    return sum(1 for line in diff if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))


def validate_structure(candidate: Path) -> list[str]:
    required = [
        "SKILL.md",
        "references/skill-map.md",
        "references/capability-catalog.json",
        "references/capability-overrides.json",
        "references/router-v2-rules.json",
        "references/eval-freeze.json",
        "scripts/router_v2.py",
        "scripts/eval_router_v2.py",
        "scripts/shadow_route.py",
        "scripts/post_task_reflection.py",
        "scripts/build_preference_overlay.py",
        "references/router-eval-feedback.json",
        "references/route-feedback.schema.json",
        "references/router-preference-overlay.json",
    ]
    return [f"missing required file: {rel}" for rel in required if not (candidate / rel).exists()]


def validate_safety_phrases(candidate: Path) -> list[str]:
    text = read_text(candidate / "SKILL.md")
    return [f"required safety phrase missing: {phrase}" for phrase in REQUIRED_SAFETY_PHRASES if phrase not in text]


def guard_script_review_flags(candidate: Path) -> list[str]:
    flags = []
    for name in sorted(GUARD_SCRIPT_FILES):
        live = SKILL_DIR / "scripts" / name
        proposed = candidate / "scripts" / name
        if live.exists() and proposed.exists() and read_text(live) != read_text(proposed):
            flags.append(f"manual guard-script review required: scripts/{name}")
    summary_path = candidate / "candidate-summary.json"
    if summary_path.exists():
        summary = read_json(summary_path)
        for name in summary.get("guard_scripts_changed", []):
            flags.append(f"manual guard-script review required: scripts/{name}")
    return sorted(set(flags))


def validate_diff_budget(candidate: Path) -> tuple[list[str], dict[str, int]]:
    errors = []
    counts = {}
    total = 0
    for rel, budget in DIFF_BUDGETS.items():
        count = changed_line_count(read_text(SKILL_DIR / rel), read_text(candidate / rel))
        counts[rel] = count
        total += count
        if count > budget:
            errors.append(f"diff budget exceeded for {rel}: {count}>{budget}")
    if total > TOTAL_DIFF_BUDGET:
        errors.append(f"total diff budget exceeded: {total}>{TOTAL_DIFF_BUDGET}")
    return errors, counts


def validate_immutable_baseline() -> list[str]:
    manifest_path = SKILL_DIR / "baselines" / "baseline-2026-06-17" / "baseline-manifest.json"
    if not manifest_path.exists():
        return ["immutable baseline manifest missing"]
    manifest = read_json(manifest_path)
    root = manifest_path.parent
    errors = []
    for rel, expected in manifest.get("checksums", {}).items():
        path = root / rel
        if not path.exists():
            errors.append(f"immutable baseline file missing: {rel}")
        elif sha256_file(path) != expected:
            errors.append(f"immutable baseline checksum mismatch: {rel}")
    return errors


def validate_frozen_eval(candidate: Path) -> list[str]:
    freeze_path = SKILL_DIR / "references" / "eval-freeze.json"
    if not freeze_path.exists():
        return ["eval freeze record missing"]
    freeze = read_json(freeze_path)
    errors = []
    for rel, expected in freeze.get("checksums", {}).items():
        path = candidate / rel
        if not path.exists():
            errors.append(f"frozen eval file missing: {rel}")
        elif sha256_file(path) != expected:
            errors.append(f"frozen eval checksum mismatch: {rel}")
    return errors


def validate_release_state(candidate: Path) -> list[str]:
    state_path = candidate / "current-release.json"
    if not state_path.exists():
        state_path = SKILL_DIR / "current-release.json"
    if not state_path.exists():
        return ["current-release.json missing"]
    state = read_json(state_path)
    errors = []
    if not state.get("current_release") or not state.get("rollback_release"):
        errors.append("release or rollback pointer missing")
    if state.get("strategy") != "manual_approval_after_gate":
        errors.append("promotion strategy must be manual_approval_after_gate")
    if state.get("runtime_mode") != "shadow_only":
        errors.append("runtime mode must remain shadow_only")
    return errors


def regression_count(cases: list[dict], candidate: Path, catalog: dict, rules: dict) -> int:
    live_docs = v1.candidate_docs(SKILL_DIR / "references" / "skill-map.md")
    count = 0
    for case in cases:
        old = v1.rank(case["query"], live_docs, 3)
        old_correct = bool(old) and v1.route_matches(case["expected_primary"], old[0][0])
        new = router_v2.route_decision(
            case["query"],
            catalog=catalog,
            rules=rules,
            map_path=candidate / "references" / "skill-map.md",
        )
        if old_correct and not v1.route_matches(case["expected_primary"], new["selected_skill"]):
            count += 1
    return count


def apply_thresholds(results: dict[str, dict], new_regressions: int) -> list[str]:
    errors = []
    for suite, result in results.items():
        thresholds = PROMOTION_THRESHOLDS[suite]
        if result["top1_rate"] + 1e-12 < thresholds["top1"]:
            errors.append(
                f"{suite} Top-1 below threshold: {result['top1']}/{result['total']} "
                f"<{thresholds['top1']:.0%}"
            )
        if result["hit_at_3_rate"] + 1e-12 < thresholds["hit_at_3"]:
            errors.append(
                f"{suite} Hit@3 below threshold: {result['hit_at_3']}/{result['total']} "
                f"<{thresholds['hit_at_3']:.0%}"
            )
    if new_regressions > PROMOTION_THRESHOLDS["regression"]["new_regressions"]:
        errors.append(f"new Top-1 regressions: {new_regressions}>0")

    total_risk = sum(result["risk_evaluated"] for result in results.values()) or 1
    total_confirmation = sum(result["confirmation_evaluated"] for result in results.values()) or 1
    total_cases = sum(result["total"] for result in results.values()) or 1
    risk_mismatch = sum(result["risk_mismatches"] for result in results.values()) / total_risk
    risk_under = sum(result["risk_underclassifications"] for result in results.values()) / total_risk
    confirmation_fn = sum(result["confirmation_false_negatives"] for result in results.values()) / total_confirmation
    availability_misleading = sum(result["availability_misleading"] for result in results.values()) / total_cases
    p95 = max((result["latency_ms"]["p95"] for result in results.values()), default=0.0)
    model_calls = sum(result["runtime_model_calls"] for result in results.values())
    model_cost = sum(result["estimated_model_cost_usd"] for result in results.values())
    unsafe_overrides = sum(result.get("unsafe_preference_overrides", 0) for result in results.values())
    risk_downgrades = sum(result.get("risk_downgrades", 0) for result in results.values())
    confirmation_downgrades = sum(
        result.get("confirmation_downgrades", 0) for result in results.values()
    )
    unavailable_applications = sum(
        result.get("unavailable_preference_applications", 0) for result in results.values()
    )
    global_thresholds = PROMOTION_THRESHOLDS["global"]
    checks = [
        ("risk misclassification rate", risk_mismatch, global_thresholds["risk_misclassification_rate"]),
        ("risk underclassification rate", risk_under, global_thresholds["risk_underclassification_rate"]),
        ("confirmation false-negative rate", confirmation_fn, global_thresholds["confirmation_false_negative_rate"]),
        ("availability misleading rate", availability_misleading, global_thresholds["availability_misleading_rate"]),
        ("p95 latency ms", p95, global_thresholds["p95_latency_ms"]),
        ("runtime model calls", model_calls, global_thresholds["runtime_model_calls"]),
        ("estimated model cost USD", model_cost, global_thresholds["estimated_model_cost_usd"]),
        ("unsafe preference overrides", unsafe_overrides, global_thresholds["unsafe_preference_overrides"]),
        ("risk downgrades", risk_downgrades, global_thresholds["risk_downgrades"]),
        ("confirmation downgrades", confirmation_downgrades, global_thresholds["confirmation_downgrades"]),
        (
            "unavailable preference applications",
            unavailable_applications,
            global_thresholds["unavailable_preference_applications"],
        ),
    ]
    for label, actual, allowed in checks:
        if actual > allowed + 1e-12:
            errors.append(f"{label} above threshold: {actual}>{allowed}")
    return errors


def run_gate(
    candidate: Path, suite: str
) -> tuple[bool, list[str], dict[str, dict], dict[str, int], list[str], dict]:
    candidate = candidate.resolve()
    errors = validate_structure(candidate)
    if errors:
        return False, errors, {}, {}, [], {}
    errors.extend(validate_safety_phrases(candidate))
    errors.extend(validate_immutable_baseline())
    errors.extend(validate_frozen_eval(candidate))
    errors.extend(validate_release_state(candidate))
    suite_paths = {
        name: candidate / "references" / f"router-eval-{name}.json" for name in v2.SUITE_DATASETS
    }
    errors.extend(v2.validate_suite_isolation(suite_paths))
    diff_errors, diff_counts = validate_diff_budget(candidate)
    errors.extend(diff_errors)
    review_flags = guard_script_review_flags(candidate)

    catalog = read_json(candidate / "references" / "capability-catalog.json")
    rules = read_json(candidate / "references" / "router-v2-rules.json")
    names = list(v2.SUITE_DATASETS) if suite == "all" else [suite]
    results = {}
    for name in names:
        cases = v2.load_cases(suite_paths[name])
        results[name] = (
            v2.evaluate_feedback_cases(cases, catalog=catalog, rules=rules)
            if name == "feedback"
            else v2.evaluate_cases(cases, catalog=catalog, rules=rules)
        )
    regression_cases = v2.load_cases(suite_paths["regression"])
    new_regressions = regression_count(regression_cases, candidate, catalog, rules)
    errors.extend(apply_thresholds(results, new_regressions))

    baseline_path = candidate / "references" / "router-eval-dataset.json"
    baseline_result = v1.evaluate_cases(
        v1.load_cases(baseline_path), candidate / "references" / "skill-map.md", 3
    )
    if baseline_result["hit"] != baseline_result["total"]:
        errors.append(
            f"v1 compatibility Hit@3 regression: {baseline_result['hit']}/{baseline_result['total']}"
        )
    context = {
        "v1_compatibility": baseline_result,
        "new_regressions": new_regressions,
        "promotion_mode": "recommendation_only",
    }
    return not errors, errors, results, diff_counts, review_flags, context


def format_report(
    candidate: Path,
    ok: bool,
    errors: list[str],
    results: dict[str, dict],
    diff_counts: dict[str, int],
    review_flags: list[str],
    context: dict,
) -> str:
    lines = [
        f"# Router v3 Candidate Gate - {now_id()}",
        "",
        f"- Candidate: `{candidate}`",
        f"- Decision: {'accepted' if ok else 'rejected'}",
        "- Promotion outcome: recommendation-only; no release changes",
        "- Runtime mode: shadow-only",
        "",
        "## Diff Budget",
    ]
    for rel, count in sorted(diff_counts.items()):
        lines.append(f"- `{rel}`: {count} changed lines")
    lines.extend(["", "## Evaluation"])
    baseline = context.get("v1_compatibility", {})
    if baseline:
        lines.append(
            f"- v1 compatibility: top1={baseline['top1']}/{baseline['total']}, "
            f"hit@3={baseline['hit']}/{baseline['total']}"
        )
    for label, result in results.items():
        lines.append(
            f"- {label}: top1={result['top1']}/{result['total']}, "
            f"hit@3={result['hit_at_3']}/{result['total']}, "
            f"risk_mismatch={result['risk_mismatches']}, "
            f"risk_under={result['risk_underclassifications']}, "
            f"confirmation_fn={result['confirmation_false_negatives']}, "
            f"availability_misleading={result['availability_misleading']}, "
            f"p95_ms={result['latency_ms']['p95']:.2f}, "
            f"model_calls={result['runtime_model_calls']}"
        )
        if label == "feedback":
            lines.append(
                "  - feedback safety: "
                f"unsafe_override={result['unsafe_preference_overrides']}, "
                f"risk_downgrade={result['risk_downgrades']}, "
                f"confirmation_downgrade={result['confirmation_downgrades']}, "
                f"unavailable_applied={result['unavailable_preference_applications']}"
            )
        for failure in result["top1_errors"][:10]:
            lines.append(
                f"  - Top-1 {failure['id']}: expected {failure['expected']} got {failure['actual']}"
            )
    lines.append(f"- New regressions against correct v1 Top-1: {context.get('new_regressions', 0)}")
    if review_flags:
        lines.extend(["", "## Mandatory Human Review"])
        lines.extend(f"- {flag}" for flag in review_flags)
    if errors:
        lines.extend(["", "## Rejection Reasons"])
        lines.extend(f"- {error}" for error in errors)
    lines.extend(
        [
            "",
            "Passing this gate does not authorize skill execution, plugin installation, external actions, or promotion.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--suite", default="all", choices=[*v2.SUITE_DATASETS.keys(), "all"])
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    candidate_resolved = args.candidate.resolve()
    ok, errors, results, diff_counts, review_flags, context = run_gate(candidate_resolved, args.suite)
    report = format_report(
        candidate_resolved, ok, errors, results, diff_counts, review_flags, context
    )
    print(report, end="")
    if args.write_report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORTS_DIR / f"{now_id()}-router-v3-gate-{candidate_resolved.name}.md"
        report_path.write_text(report, encoding="utf-8")
        append_jsonl(
            DECISIONS_LOG,
            {
                "timestamp": now_id(),
                "candidate": str(args.candidate.resolve()),
                "decision": "accepted_for_recommendation" if ok else "rejected",
                "promotion_attempted": False,
                "errors": errors,
                "review_flags": review_flags,
                "report": str(report_path),
            },
        )
        print(f"report={report_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
