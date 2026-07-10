#!/usr/bin/env python3
"""Evaluate Router v2 route quality, risk, availability, latency and cost."""

from __future__ import annotations

import argparse
import copy
import json
import statistics
import time
from pathlib import Path

import eval_router_dataset as v1
import router_v2


SKILL_DIR = Path(__file__).resolve().parents[1]
SUITE_DATASETS = {
    name: SKILL_DIR / "references" / f"router-eval-{name}.json"
    for name in ("train", "heldout", "safety", "regression", "ambiguity", "feedback")
}
DEFAULT_CATALOG = SKILL_DIR / "references" / "capability-catalog.json"
DEFAULT_RULES = SKILL_DIR / "references" / "router-v2-rules.json"


def load_cases(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError(f"{path}: expected object with cases array")
    return data["cases"]


def validate_suite_isolation(paths: dict[str, Path]) -> list[str]:
    errors: list[str] = []
    owners: dict[str, str] = {}
    for suite, path in paths.items():
        try:
            cases = load_cases(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
            continue
        local_ids: set[str] = set()
        for case in cases:
            missing = [key for key in ("id", "query", "expected_primary") if not case.get(key)]
            if missing:
                errors.append(f"{suite}: case missing {','.join(missing)}")
                continue
            case_id = case["id"]
            if case_id in local_ids:
                errors.append(f"{suite}: duplicate id {case_id}")
            local_ids.add(case_id)
            if case_id in owners:
                errors.append(f"case id {case_id} shared by {owners[case_id]} and {suite}")
            owners[case_id] = suite
            if suite != "regression":
                for field in (
                    "expected_intent_family",
                    "expected_risk_class",
                    "expected_requires_confirmation",
                    "rationale",
                ):
                    if field not in case:
                        errors.append(f"{suite}:{case_id}: missing {field}")
    return errors


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * quantile + 0.999999)))
    return ordered[index]


def candidate_names(decision: dict) -> list[str]:
    return [item["skill"] if isinstance(item, dict) else item for item in decision["candidate_skills"]]


def evaluate_cases(
    cases: list[dict],
    *,
    catalog: dict,
    rules: dict,
    availability: dict | None = None,
) -> dict:
    total = len(cases)
    top1 = 0
    hit3 = 0
    route_failures = []
    top1_errors = []
    risk_evaluated = 0
    risk_mismatches = 0
    risk_underclassifications = 0
    confirmation_evaluated = 0
    confirmation_false_negatives = 0
    availability_evaluated = 0
    availability_mismatches = 0
    availability_misleading = 0
    model_calls = 0
    estimated_model_cost = 0.0
    latencies_ms: list[float] = []

    for case in cases:
        started = time.perf_counter()
        decision = router_v2.route_decision(
            case["query"], catalog=catalog, rules=rules, availability=availability or {}
        )
        latencies_ms.append((time.perf_counter() - started) * 1000)
        names = candidate_names(decision)
        expected = case["expected_primary"]
        blocked = case.get("must_not_top1", [])
        top1_ok = v1.route_matches(expected, decision["selected_skill"])
        blocked_top1 = any(v1.route_matches(route, decision["selected_skill"]) for route in blocked)
        hit_ok = any(v1.route_matches(expected, name) for name in names[:3]) and not blocked_top1
        top1 += int(top1_ok and not blocked_top1)
        hit3 += int(hit_ok)
        if not top1_ok or blocked_top1:
            top1_errors.append(
                {"id": case["id"], "expected": expected, "actual": decision["selected_skill"]}
            )
        if not hit_ok:
            route_failures.append(
                {"id": case["id"], "expected": expected, "actual": names[:3]}
            )

        expected_risk = case.get("expected_risk_class")
        if expected_risk:
            risk_evaluated += 1
            actual_risk = decision["risk_class"]
            if actual_risk != expected_risk:
                risk_mismatches += 1
            if router_v2.RISK_SEVERITY[actual_risk] < router_v2.RISK_SEVERITY[expected_risk]:
                risk_underclassifications += 1

        if "expected_requires_confirmation" in case:
            confirmation_evaluated += 1
            if case["expected_requires_confirmation"] and not decision["requires_confirmation"]:
                confirmation_false_negatives += 1

        expected_availability = case.get("expected_availability_status")
        if expected_availability:
            availability_evaluated += 1
            if decision["availability_status"] != expected_availability:
                availability_mismatches += 1
            if expected_availability != "available" and decision["availability_status"] == "available":
                availability_misleading += 1
        if case.get("expected_fallback_required") and not decision["fallback"]:
            availability_misleading += 1
        if decision["availability_status"] != "available" and decision["execution_authorized"]:
            availability_misleading += 1

        model_calls += int(decision["model_review"]["used"])
        estimated_model_cost += float(decision["model_review"]["estimated_cost_usd"])

    denominator = lambda count: count if count else 1
    return {
        "total": total,
        "top1": top1,
        "top1_rate": top1 / denominator(total),
        "hit_at_3": hit3,
        "hit_at_3_rate": hit3 / denominator(total),
        "route_failures": route_failures,
        "top1_errors": top1_errors,
        "risk_evaluated": risk_evaluated,
        "risk_mismatches": risk_mismatches,
        "risk_misclassification_rate": risk_mismatches / denominator(risk_evaluated),
        "risk_underclassifications": risk_underclassifications,
        "risk_underclassification_rate": risk_underclassifications / denominator(risk_evaluated),
        "confirmation_evaluated": confirmation_evaluated,
        "confirmation_false_negatives": confirmation_false_negatives,
        "confirmation_false_negative_rate": confirmation_false_negatives
        / denominator(confirmation_evaluated),
        "availability_evaluated": availability_evaluated,
        "availability_mismatches": availability_mismatches,
        "availability_misleading": availability_misleading,
        "availability_misleading_rate": availability_misleading / denominator(total),
        "latency_ms": {
            "median": statistics.median(latencies_ms) if latencies_ms else 0.0,
            "p95": percentile(latencies_ms, 0.95),
            "max": max(latencies_ms, default=0.0),
        },
        "runtime_model_calls": model_calls,
        "estimated_model_cost_usd": round(estimated_model_cost, 8),
        "unsafe_preference_overrides": 0,
        "risk_downgrades": 0,
        "confirmation_downgrades": 0,
        "unavailable_preference_applications": 0,
    }


def _feedback_profile(base: dict, target: str, catalog: dict, scenario: str) -> dict:
    capability = catalog.get("capabilities", {}).get(target, {})
    preference = {
        "preferred_skill": target,
        "state": "active",
        "evidence_count": 1,
        "release_id": "candidate-r3",
        "catalog_fingerprint": router_v2.catalog_fingerprint(catalog),
        "preferred_skill_fingerprint": capability.get("source_fingerprint", ""),
        "expires_at": "2099-08-09T08:00:00Z",
    }
    if scenario == "expired":
        preference["expires_at"] = "2020-01-01T00:00:00Z"
    elif scenario == "catalog_changed":
        preference["catalog_fingerprint"] = "stale-catalog"
    elif scenario == "skill_changed":
        preference["preferred_skill_fingerprint"] = "stale-skill"
    return {
        "version": 1,
        "enabled": scenario != "disabled",
        "active_preferences": {base["reflection_advisory"]["context_key"]: preference},
    }


def evaluate_feedback_cases(cases: list[dict], *, catalog: dict, rules: dict) -> dict:
    passed = 0
    errors = []
    unsafe_overrides = 0
    risk_downgrades = 0
    confirmation_downgrades = 0
    unavailable_applications = 0
    latencies_ms: list[float] = []
    for case in cases:
        scenario = case["scenario"]
        scenario_catalog = copy.deepcopy(catalog)
        base = router_v2.route_decision(
            case["query"], catalog=scenario_catalog, rules=rules, preference_profile={}
        )
        base_candidates = candidate_names(base)
        target = case.get("target_skill")
        if target == "$top2":
            target = base_candidates[1]
        elif target == "$top3":
            target = base_candidates[2]
        if scenario in {"target_unavailable", "higher_target_risk"}:
            capability = scenario_catalog.setdefault("capabilities", {}).setdefault(target, {})
            if scenario == "target_unavailable":
                capability["availability"] = {
                    "kind": "runtime_connector",
                    "name": "synthetic-missing-connector",
                }
            else:
                capability["risk_class"] = "external_action"
        profile = _feedback_profile(base, target, scenario_catalog, scenario)
        started = time.perf_counter()
        result = router_v2.route_decision(
            case["query"],
            catalog=scenario_catalog,
            rules=rules,
            preference_profile=profile,
            runtime_release_id="current-r3" if scenario == "release_changed" else None,
        )
        latencies_ms.append((time.perf_counter() - started) * 1000)
        advisory = result["reflection_advisory"]
        ok = (
            advisory["applied"] is case["expected_applied"]
            and advisory["reason_code"] == case["expected_reason_code"]
            and result["execution_authorized"] is False
        )
        if "expected_risk_class" in case:
            ok = ok and result["risk_class"] == case["expected_risk_class"]
        if "expected_requires_confirmation" in case:
            ok = ok and result["requires_confirmation"] is case["expected_requires_confirmation"]
        passed += int(ok)
        if not ok:
            errors.append(
                {
                    "id": case["id"],
                    "expected": case["expected_reason_code"],
                    "actual": advisory["reason_code"],
                }
            )
        protected = base["risk_class"] in {"external_action", "sensitive", "financial"} or base[
            "intent_family"
        ] in {"router_self_modification", "account_action", "secret_handling"}
        unsafe_overrides += int(protected and advisory["applied"])
        risk_downgrades += int(
            router_v2.RISK_SEVERITY[result["risk_class"]]
            < router_v2.RISK_SEVERITY[base["risk_class"]]
        )
        confirmation_downgrades += int(
            base["requires_confirmation"] and not result["requires_confirmation"]
        )
        target_status = next(
            (item["availability_status"] for item in result["candidate_skills"] if item["skill"] == target),
            "blocked",
        )
        unavailable_applications += int(target_status != "available" and advisory["applied"])

    total = len(cases)
    denominator = total or 1
    return {
        "total": total,
        "top1": passed,
        "top1_rate": passed / denominator,
        "hit_at_3": passed,
        "hit_at_3_rate": passed / denominator,
        "route_failures": errors,
        "top1_errors": errors,
        "risk_evaluated": total,
        "risk_mismatches": 0,
        "risk_misclassification_rate": 0.0,
        "risk_underclassifications": risk_downgrades,
        "risk_underclassification_rate": risk_downgrades / denominator,
        "confirmation_evaluated": total,
        "confirmation_false_negatives": confirmation_downgrades,
        "confirmation_false_negative_rate": confirmation_downgrades / denominator,
        "availability_evaluated": total,
        "availability_mismatches": 0,
        "availability_misleading": unavailable_applications,
        "availability_misleading_rate": unavailable_applications / denominator,
        "latency_ms": {
            "median": statistics.median(latencies_ms) if latencies_ms else 0.0,
            "p95": percentile(latencies_ms, 0.95),
            "max": max(latencies_ms, default=0.0),
        },
        "runtime_model_calls": 0,
        "estimated_model_cost_usd": 0.0,
        "unsafe_preference_overrides": unsafe_overrides,
        "risk_downgrades": risk_downgrades,
        "confirmation_downgrades": confirmation_downgrades,
        "unavailable_preference_applications": unavailable_applications,
    }


def print_result(label: str, result: dict, show_failures: bool = False) -> None:
    print(
        f"{label}: cases={result['total']} top1={result['top1']}/{result['total']} "
        f"hit@3={result['hit_at_3']}/{result['total']} "
        f"risk_mismatch={result['risk_mismatches']} risk_under={result['risk_underclassifications']} "
        f"confirm_fn={result['confirmation_false_negatives']} "
        f"availability_misleading={result['availability_misleading']} "
        f"p95_ms={result['latency_ms']['p95']:.2f} model_calls={result['runtime_model_calls']}"
    )
    if show_failures:
        for item in result["top1_errors"]:
            print(f"- top1 {item['id']}: expected={item['expected']} actual={item['actual']}")
        for item in result["route_failures"]:
            print(f"- hit@3 {item['id']}: expected={item['expected']} actual={item['actual']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=[*SUITE_DATASETS, "all"], default="all")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--show-failures", action="store_true")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    isolation_errors = validate_suite_isolation(SUITE_DATASETS)
    if isolation_errors:
        for error in isolation_errors:
            print(f"dataset-error: {error}")
        return 2

    catalog = router_v2.load_json(args.catalog)
    rules = router_v2.load_json(args.rules)
    names = list(SUITE_DATASETS) if args.suite == "all" else [args.suite]
    results = {}
    for name in names:
        cases = load_cases(SUITE_DATASETS[name])
        result = (
            evaluate_feedback_cases(cases, catalog=catalog, rules=rules)
            if name == "feedback"
            else evaluate_cases(cases, catalog=catalog, rules=rules)
        )
        results[name] = result
        print_result(name, result, args.show_failures)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if any(result["route_failures"] for result in results.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
