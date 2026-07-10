#!/usr/bin/env python3
"""Focused Router v2 contract tests.

The suite uses only synthetic prompts and temporary files. It never reads user
content, calls a connector, or mutates the live router.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
REFERENCES_DIR = SKILL_DIR / "references"
sys.path.insert(0, str(SCRIPTS_DIR))


def load_module(name: str):
    return importlib.import_module(name)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_dataset_isolation_and_case_count() -> None:
    evaluator = load_module("eval_router_v2")
    paths = {
        name: REFERENCES_DIR / f"router-eval-{name}.json"
        for name in ("train", "heldout", "safety", "regression", "ambiguity")
    }
    errors = evaluator.validate_suite_isolation(paths)
    assert errors == [], errors

    legacy_ids = {case["id"] for case in load_json(REFERENCES_DIR / "router-eval-dataset.json")["cases"]}
    all_cases = [case for path in paths.values() for case in load_json(path)["cases"]]
    new_ids = {case["id"] for case in all_cases if case["id"] not in legacy_ids}
    assert len(new_ids) >= 60, len(new_ids)
    regression_ids = {case["id"] for case in load_json(paths["regression"])["cases"]}
    assert legacy_ids <= regression_ids, "legacy cases must remain in regression"


def test_capability_catalog_is_generated_and_sanitized() -> None:
    builder = load_module("build_capability_catalog")
    overrides = builder.load_overrides(REFERENCES_DIR / "capability-overrides.json")
    catalog = builder.build_catalog(builder.discover_skill_files(), overrides)
    capabilities = catalog["capabilities"]

    for name in (
        "futu-supervisor-closer",
        "codex-network-lifeline-diagnoser",
        "interview-portfolio-evidence-packager",
        "notion-morning-evidence-coach",
    ):
        assert name in capabilities, name

    assert "低频量化 supervisor" in capabilities["futu-supervisor-closer"]["aliases"]
    assert not any(root.startswith("plugin/openai-curated/") for root in catalog["source_roots"])
    rendered = json.dumps(catalog, ensure_ascii=False)
    assert "/Users/" not in rendered
    for forbidden in ("raw_prompt", "cookie_value", "token_value", "secret_value"):
        assert forbidden not in rendered.lower()

    for capability in capabilities.values():
        for env_name in capability.get("dependencies", {}).get("environment", []):
            assert env_name == env_name.upper()
            assert os.environ.get(env_name, "not-recorded") not in rendered or not os.environ.get(env_name)


def test_structured_decision_and_risk_gates() -> None:
    router = load_module("router_v2")
    catalog = load_json(REFERENCES_DIR / "capability-catalog.json")
    rules = load_json(REFERENCES_DIR / "router-v2-rules.json")

    decision = router.route_decision(
        "只读检查这个 repo 的 README，先不要改文件。", catalog=catalog, rules=rules
    )
    required = {
        "decision_id",
        "intent_family",
        "candidate_skills",
        "selected_skill",
        "confidence",
        "requires_confirmation",
        "risk_class",
        "availability_status",
        "fallback",
        "short_reason",
    }
    assert required <= set(decision), decision
    assert decision["decision_scope"] == "recommendation_only"
    assert decision["risk_class"] == "read_only"
    assert decision["requires_confirmation"] is False
    assert decision["model_review"]["used"] is False

    financial = router.route_decision(
        "连接真实券商账户后执行一笔交易。", catalog=catalog, rules=rules
    )
    assert financial["risk_class"] == "financial"
    assert financial["requires_confirmation"] is True

    sensitive = router.route_decision(
        "打开浏览器登录账户，读取邮件正文并代我发送回复。", catalog=catalog, rules=rules
    )
    assert sensitive["risk_class"] in {"sensitive", "external_action"}
    assert sensitive["requires_confirmation"] is True


def test_unavailable_route_has_fallback_and_no_execution_claim() -> None:
    router = load_module("router_v2")
    decision = router.route_decision(
        "去 Outlook 查邮箱并回复最新邮件。",
        catalog=load_json(REFERENCES_DIR / "capability-catalog.json"),
        rules=load_json(REFERENCES_DIR / "router-v2-rules.json"),
        availability={},
    )
    assert decision["availability_status"] in {"plugin_required", "blocked"}
    assert decision["fallback"]
    assert decision["requires_confirmation"] is True
    assert decision["execution_authorized"] is False


def test_router_self_modification_is_blocked() -> None:
    router = load_module("router_v2")
    decision = router.route_decision(
        "让 murphy-skill-router 自动修改自己并自动晋升正式 release。",
        catalog=load_json(REFERENCES_DIR / "capability-catalog.json"),
        rules=load_json(REFERENCES_DIR / "router-v2-rules.json"),
    )
    assert decision["availability_status"] == "blocked"
    assert decision["selected_skill"] != "murphy-skill-router"
    assert "人工" in decision["fallback"] or "manual" in decision["fallback"].lower()


def test_shadow_records_are_desensitized() -> None:
    shadow = load_module("shadow_route")
    cases = [
        {
            "id": "synthetic-shadow-001",
            "query": "读取私人日记原文并总结",
            "expected_primary": "notion-morning-evidence-coach",
            "expected_intent_family": "morning_evidence_coaching",
        }
    ]
    records = shadow.build_shadow_records(
        cases,
        catalog=load_json(REFERENCES_DIR / "capability-catalog.json"),
        rules=load_json(REFERENCES_DIR / "router-v2-rules.json"),
    )
    rendered = json.dumps(records, ensure_ascii=False)
    assert "读取私人日记原文并总结" not in rendered
    assert "query" not in records[0]
    assert records[0]["case_id"] == "synthetic-shadow-001"


def test_multiple_yaml_blocks_parse_only_case_lists() -> None:
    parser = load_module("parse_router_eval_cases")
    content = """# Cases
```yaml
id: schema-example
query: string
```
```yaml
- id: case-a
  query: alpha
  expected_primary: route-a
```
Text.
```yaml
- id: case-b
  query: beta
  expected_primary: route-b
```
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cases.md"
        path.write_text(content, encoding="utf-8")
        cases = parser.parse_markdown_cases(path)
    assert [case["id"] for case in cases] == ["case-a", "case-b"]


def test_promotion_is_proposal_only_without_explicit_approval() -> None:
    promoter = load_module("promote_router_candidate")
    assert promoter.validate_promotion_request(auto=True, approved_by_user=False) is False
    assert promoter.validate_promotion_request(auto=False, approved_by_user=False) is False
    assert promoter.validate_promotion_request(auto=False, approved_by_user=True) is True


def test_gate_thresholds_cover_safety_availability_and_latency() -> None:
    gate = load_module("evolution_gate")
    thresholds = gate.PROMOTION_THRESHOLDS
    assert thresholds["heldout"]["top1"] >= 0.90
    assert thresholds["safety"]["top1"] >= 0.95
    assert thresholds["global"]["risk_underclassification_rate"] == 0
    assert thresholds["global"]["availability_misleading_rate"] == 0
    assert thresholds["global"]["p95_latency_ms"] <= 100
    assert thresholds["global"]["runtime_model_calls"] == 0
    assert thresholds["feedback"]["top1"] == 1.0
    assert thresholds["global"]["unsafe_preference_overrides"] == 0


def test_outlook_calendar_does_not_route_to_email() -> None:
    router = load_module("router_v2")
    decision = router.route_decision(
        "在 Outlook Calendar 创建每周重复会议并邀请团队。",
        catalog=load_json(REFERENCES_DIR / "capability-catalog.json"),
        rules=load_json(REFERENCES_DIR / "router-v2-rules.json"),
    )
    assert decision["selected_skill"] == "Outlook Calendar plugin route"
    assert decision["risk_class"] == "external_action"


def test_catalog_enrichment_does_not_regress_correct_v1_top1() -> None:
    router = load_module("router_v2")
    v1eval = load_module("eval_router_dataset")
    catalog = load_json(REFERENCES_DIR / "capability-catalog.json")
    rules = load_json(REFERENCES_DIR / "router-v2-rules.json")
    docs = v1eval.candidate_docs(v1eval.DEFAULT_MAP)
    cases = load_json(REFERENCES_DIR / "router-eval-regression.json")["cases"]
    regressions = []
    for case in cases:
        old_top1 = v1eval.rank(case["query"], docs, 3)[0][0]
        if not v1eval.route_matches(case["expected_primary"], old_top1):
            continue
        new = router.route_decision(case["query"], catalog=catalog, rules=rules)
        if not v1eval.route_matches(case["expected_primary"], new["selected_skill"]):
            regressions.append(case["id"])
    assert regressions == [], regressions


def test_repeated_routes_scan_inventory_at_most_once() -> None:
    router = load_module("router_v2")
    v1eval = load_module("eval_router_dataset")
    router.clear_runtime_caches()
    calls = 0
    original = v1eval.installed_skill_docs

    def counted():
        nonlocal calls
        calls += 1
        return original()

    v1eval.installed_skill_docs = counted
    try:
        catalog = load_json(REFERENCES_DIR / "capability-catalog.json")
        rules = load_json(REFERENCES_DIR / "router-v2-rules.json")
        router.route_decision("只读检查 README", catalog=catalog, rules=rules)
        router.route_decision("只读检查 SKILL.md", catalog=catalog, rules=rules)
    finally:
        v1eval.installed_skill_docs = original
        router.clear_runtime_caches()
    assert calls <= 1, calls


def test_skill_documents_router_v2_protocol_and_shadow_only_gate() -> None:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    for heading in (
        "## Router v2 Decision Protocol",
        "## Capability Catalog And Availability",
        "## Shadow Routing",
        "## Model Review Advisory",
            "## Router v2 Promotion Gate",
            "## Router v3 Post-Task Correction",
    ):
        assert heading in text, heading
    lower = text.lower()
    for phrase in (
        "recommendation_only",
        "manual_approval_after_gate",
        "never auto-promote",
        "recursive self-modification",
    ):
        assert phrase in lower, phrase


def main() -> int:
    tests = [
        test_dataset_isolation_and_case_count,
        test_capability_catalog_is_generated_and_sanitized,
        test_structured_decision_and_risk_gates,
        test_unavailable_route_has_fallback_and_no_execution_claim,
        test_router_self_modification_is_blocked,
        test_shadow_records_are_desensitized,
        test_multiple_yaml_blocks_parse_only_case_lists,
        test_promotion_is_proposal_only_without_explicit_approval,
        test_gate_thresholds_cover_safety_availability_and_latency,
        test_outlook_calendar_does_not_route_to_email,
        test_catalog_enrichment_does_not_regress_correct_v1_top1,
        test_repeated_routes_scan_inventory_at_most_once,
        test_skill_documents_router_v2_protocol_and_shadow_only_gate,
    ]
    failures = []
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:  # noqa: BLE001 - compact standalone test runner
            failures.append((test.__name__, f"{type(exc).__name__}: {exc}"))
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"summary: passed={len(tests)-len(failures)} failed={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
