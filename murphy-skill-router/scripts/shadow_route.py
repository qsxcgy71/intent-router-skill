#!/usr/bin/env python3
"""Compare v1 and Router v3 shadow recommendations without raw task text."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import eval_router_dataset as v1
import eval_router_v2 as v2eval
import router_v2


SKILL_DIR = Path(__file__).resolve().parents[1]


def build_shadow_records(cases: list[dict], *, catalog: dict, rules: dict) -> list[dict]:
    v1_docs = v1.candidate_docs(v1.DEFAULT_MAP)
    records = []
    for case in cases:
        v1_ranked = [name for name, _ in v1.rank(case["query"], v1_docs, 3)]
        decision = router_v2.route_decision(case["query"], catalog=catalog, rules=rules)
        v2_ranked = v2eval.candidate_names(decision)[:3]
        expected = case.get("expected_primary", "")
        records.append(
            {
                "case_id": case["id"],
                "abstract_intent": case.get("expected_intent_family") or decision["intent_family"],
                "expected_primary": expected,
                "v1_candidates": v1_ranked,
                "v2_candidates": v2_ranked,
                "v1_selected": v1_ranked[0] if v1_ranked else "",
                "v2_selected": decision["selected_skill"],
                "v1_top1_correct": bool(v1_ranked and v1.route_matches(expected, v1_ranked[0])),
                "v2_top1_correct": v1.route_matches(expected, decision["selected_skill"]),
                "v1_hit_at_3": any(v1.route_matches(expected, route) for route in v1_ranked),
                "v2_hit_at_3": any(v1.route_matches(expected, route) for route in v2_ranked),
                "confidence": decision["confidence"],
                "risk_class": decision["risk_class"],
                "requires_confirmation": decision["requires_confirmation"],
                "availability_status": decision["availability_status"],
                "fallback_present": bool(decision["fallback"]),
                "model_review_used": decision["model_review"]["used"],
                "model_review_recommended": decision["model_review"]["review_recommended"],
                "feedback_context_key": decision["reflection_advisory"]["context_key"],
                "feedback_preference_applied": decision["reflection_advisory"]["applied"],
                "feedback_reason_code": decision["reflection_advisory"]["reason_code"],
            }
        )
    return records


def confusion_summary(records: list[dict]) -> dict:
    disagreements = [row["case_id"] for row in records if row["v1_selected"] != row["v2_selected"]]
    candidate_intents = sorted(
        {
            row["abstract_intent"]
            for row in records
            if row["v2_selected"].startswith("Direct:")
            or row["v2_selected"] in {"External-state-blocked route", "Manual router review route"}
            or row["model_review_recommended"]
        }
    )
    return {
        "case_count": len(records),
        "v1_top1": sum(row["v1_top1_correct"] for row in records),
        "v2_top1": sum(row["v2_top1_correct"] for row in records),
        "v1_hit_at_3": sum(row["v1_hit_at_3"] for row in records),
        "v2_hit_at_3": sum(row["v2_hit_at_3"] for row in records),
        "disagreement_count": len(disagreements),
        "disagreement_case_ids": disagreements,
        "v1_top1_error_case_ids": [row["case_id"] for row in records if not row["v1_top1_correct"]],
        "v2_top1_error_case_ids": [row["case_id"] for row in records if not row["v2_top1_correct"]],
        "v1_top3_miss_case_ids": [row["case_id"] for row in records if not row["v1_hit_at_3"]],
        "v2_top3_miss_case_ids": [row["case_id"] for row in records if not row["v2_hit_at_3"]],
        "nonavailable_case_ids": [
            row["case_id"] for row in records if row["availability_status"] != "available"
        ],
        "missing_fallback_case_ids": [
            row["case_id"]
            for row in records
            if row["availability_status"] != "available" and not row["fallback_present"]
        ],
        "candidate_intents_for_new_or_merged_capability": candidate_intents,
        "model_review_used_count": sum(row["model_review_used"] for row in records),
        "feedback_preference_applied_count": sum(
            row["feedback_preference_applied"] for row in records
        ),
    }


def render_markdown(summary: dict) -> str:
    lines = [
        "# Router v3 Shadow Confusion Report",
        "",
        "This report contains case ids and abstract intent labels only; raw prompts are not persisted.",
        "",
        "## Metrics",
        "",
        f"- Cases: {summary['case_count']}",
        f"- v1 Top-1: {summary['v1_top1']}/{summary['case_count']}",
        f"- v2 Top-1: {summary['v2_top1']}/{summary['case_count']}",
        f"- v1 Hit@3: {summary['v1_hit_at_3']}/{summary['case_count']}",
        f"- v2 Hit@3: {summary['v2_hit_at_3']}/{summary['case_count']}",
        f"- v1/v2 disagreements: {summary['disagreement_count']}",
        f"- Runtime model calls: {summary['model_review_used_count']}",
        f"- Feedback preferences applied: {summary['feedback_preference_applied_count']}",
        "",
        "## Confusion",
        "",
        f"- Disagreement case ids: {', '.join(summary['disagreement_case_ids']) or 'none'}",
        f"- v1 Top-1 errors: {', '.join(summary['v1_top1_error_case_ids']) or 'none'}",
        f"- v2 Top-1 errors: {', '.join(summary['v2_top1_error_case_ids']) or 'none'}",
        f"- v1 Top-3 misses: {', '.join(summary['v1_top3_miss_case_ids']) or 'none'}",
        f"- v2 Top-3 misses: {', '.join(summary['v2_top3_miss_case_ids']) or 'none'}",
        "",
        "## Availability and Capability Gaps",
        "",
        f"- Non-available case ids: {', '.join(summary['nonavailable_case_ids']) or 'none'}",
        f"- Missing fallback case ids: {', '.join(summary['missing_fallback_case_ids']) or 'none'}",
        "- Candidate intents for a new or merged capability: "
        + (", ".join(summary["candidate_intents_for_new_or_merged_capability"]) or "none"),
        "",
        "Shadow results do not change the default route or any release pointer.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=[*v2eval.SUITE_DATASETS, "all"], default="all")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    names = list(v2eval.SUITE_DATASETS) if args.suite == "all" else [args.suite]
    catalog = router_v2.load_json(v2eval.DEFAULT_CATALOG)
    rules = router_v2.load_json(v2eval.DEFAULT_RULES)
    cases = [case for name in names for case in v2eval.load_cases(v2eval.SUITE_DATASETS[name])]
    records = build_shadow_records(cases, catalog=catalog, rules=rules)
    summary = confusion_summary(records)
    payload = {
        "version": 3,
        "privacy_policy": "case ids and abstract intents only; no raw prompt persistence",
        "mode": "shadow_only",
        "summary": summary,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_markdown(summary), encoding="utf-8")
    print(f"cases={summary['case_count']} v1_top1={summary['v1_top1']} v2_top1={summary['v2_top1']}")
    print(f"output={args.output}")
    print(f"report={args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
