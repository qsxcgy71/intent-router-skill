#!/usr/bin/env python3
"""Deterministic, recommendation-only Router v2 decision engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import eval_router_dataset as v1


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = SKILL_DIR / "references" / "capability-catalog.json"
DEFAULT_RULES = SKILL_DIR / "references" / "router-v2-rules.json"
DEFAULT_MAP = SKILL_DIR / "references" / "skill-map.md"
DEFAULT_PREFERENCE_OVERLAY = SKILL_DIR / "references" / "router-preference-overlay.json"
RISK_SEVERITY = {
    "read_only": 0,
    "workspace_write": 1,
    "external_action": 2,
    "sensitive": 3,
    "financial": 4,
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def catalog_fingerprint(catalog: dict) -> str:
    """Fingerprint public capability metadata without time-dependent fields."""
    stable = {
        "version": catalog.get("version"),
        "source_roots": catalog.get("source_roots", []),
        "capabilities": catalog.get("capabilities", {}),
    }
    rendered = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def reflection_context_key(intent_family: str, matched_rule: dict | None, risk_class: str) -> str:
    """Create a non-content context key; never hash or retain the task prompt."""
    rule_id = (matched_rule or {}).get("id", "catalog-retrieval")
    return f"{intent_family}:{rule_id}:{risk_class}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return None


def _stricter_risk(left: str, right: str) -> str:
    return left if RISK_SEVERITY.get(left, 0) >= RISK_SEVERITY.get(right, 0) else right


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def term_present(query: str, term: str) -> bool:
    return normalized(term) in query


def rule_matches(query: str, rule: dict) -> bool:
    all_terms = rule.get("all_terms", [])
    any_terms = rule.get("any_terms", [])
    none_terms = rule.get("none_terms", [])
    if all_terms and not all(term_present(query, term) for term in all_terms):
        return False
    if any_terms and not any(term_present(query, term) for term in any_terms):
        return False
    if any(term_present(query, term) for term in none_terms):
        return False
    return bool(all_terms or any_terms)


def select_rule(query: str, rules: dict) -> dict | None:
    matches = [rule for rule in rules.get("intent_rules", []) if rule_matches(query, rule)]
    if not matches:
        return None
    matches.sort(
        key=lambda rule: (
            -int(rule.get("priority", 0)),
            -(len(rule.get("all_terms", [])) + len(rule.get("any_terms", []))),
            rule.get("id", ""),
        )
    )
    return matches[0]


def classify_risk(query: str, rules: dict, matched_rule: dict | None) -> str:
    if matched_rule and matched_rule.get("risk_class"):
        return matched_rule["risk_class"]
    terms = rules.get("risk_terms", {})
    if any(term_present(query, term) for term in terms.get("financial", [])):
        return "financial"
    if any(term_present(query, term) for term in terms.get("sensitive", [])):
        return "sensitive"
    if any(term_present(query, term) for term in terms.get("external_action", [])):
        return "external_action"
    if any(term_present(query, term) for term in terms.get("read_only", [])):
        return "read_only"
    if any(term_present(query, term) for term in terms.get("workspace_write", [])):
        return "workspace_write"
    return "read_only"


def capability_doc(capability: dict) -> str:
    return " ".join(
        [
            capability.get("name", ""),
            capability.get("description", ""),
            " ".join(capability.get("aliases", [])),
        ]
    )


@lru_cache(maxsize=8)
def _base_index(map_path_text: str, mtime_ns: int) -> dict[str, set[str]]:
    del mtime_ns  # part of the cache key; the path content is read below
    docs = v1.candidate_docs(Path(map_path_text))
    return {route: v1.tokens(route + "\n" + doc) for route, doc in docs.items()}


_CATALOG_INDEX: dict[int, dict[str, set[str]]] = {}


def _catalog_index(catalog: dict) -> dict[str, set[str]]:
    key = id(catalog)
    if key not in _CATALOG_INDEX:
        _CATALOG_INDEX[key] = {
            name: v1.tokens(name + "\n" + capability_doc(capability))
            for name, capability in catalog.get("capabilities", {}).items()
        }
    return _CATALOG_INDEX[key]


def clear_runtime_caches() -> None:
    _base_index.cache_clear()
    _CATALOG_INDEX.clear()


def token_score(query_tokens: set[str], route: str, doc_tokens: set[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    overlap = query_tokens & doc_tokens
    route_bonus = len(v1.tokens(route) & query_tokens) * 1.5
    return len(overlap) / math.sqrt(len(doc_tokens)) + route_bonus


def retrieval_scores(query: str, catalog: dict, map_path: Path) -> dict[str, float]:
    query_tokens = v1.tokens(query)
    base = _base_index(str(map_path.resolve()), map_path.stat().st_mtime_ns)
    scores = {route: token_score(query_tokens, route, doc_tokens) for route, doc_tokens in base.items()}
    for name, doc_tokens in _catalog_index(catalog).items():
        # Existing map routes keep their exact v1 score. The catalog adds
        # discoverability for missing routes but cannot silently rerank a
        # previously correct explicit map entry.
        if name in scores:
            continue
        scores[name] = token_score(query_tokens, name, doc_tokens) * 0.25
    return scores


def resolve_availability(
    selected_skill: str,
    catalog: dict,
    availability: dict | None = None,
    forced_status: str | None = None,
) -> tuple[str, str]:
    capability = catalog.get("capabilities", {}).get(selected_skill, {})
    fallback = capability.get("fallback", "")
    if forced_status:
        return forced_status, fallback
    availability = availability or {}
    policy = capability.get("availability", {"kind": "direct"})
    kind = policy.get("kind", "direct")
    dependency = policy.get("name", "")
    if kind in {"installed_skill", "direct"}:
        return "available", fallback
    if kind == "blocked":
        return "blocked", fallback
    if kind == "uninstalled_plugin":
        return "plugin_required", fallback
    if kind == "runtime_connector":
        return ("available" if availability.get(dependency) is True else "blocked"), fallback
    if kind == "environment":
        provided = availability.get(dependency)
        present = provided is True or (provided is None and bool(os.environ.get(dependency)))
        return ("available" if present else "missing_dependency"), fallback
    return "blocked", fallback


def inferred_intent(selected_skill: str) -> str:
    if selected_skill == "murphy-skill-router":
        return "route_explanation"
    if selected_skill.startswith("Direct:"):
        return "direct_route"
    if "plugin route" in selected_skill.lower() or "connector route" in selected_skill.lower():
        return "connector_route"
    return "skill_route"


def route_decision(
    query: str,
    *,
    catalog: dict | None = None,
    rules: dict | None = None,
    availability: dict | None = None,
    map_path: Path = DEFAULT_MAP,
    preference_profile: dict | None = None,
    runtime_release_id: str | None = None,
) -> dict:
    catalog = catalog or load_json(DEFAULT_CATALOG)
    rules = rules or load_json(DEFAULT_RULES)
    query_norm = normalized(query)
    matched_rule = select_rule(query_norm, rules)
    scores = retrieval_scores(query, catalog, map_path)

    if matched_rule:
        selected = matched_rule["selected_skill"]
        scores[selected] = max(scores.get(selected, 0.0), 100.0 + matched_rule.get("priority", 0) / 1000)
        for index, support in enumerate(matched_rule.get("support", [])):
            scores[support] = max(scores.get(support, 0.0), 20.0 - index)
    else:
        selected = max(scores, key=scores.get) if scores else "Direct: router advisory"

    self_mod_cues = ("自动修改自己", "自动晋升", "自动 promotion", "正式 release", "修改正式")
    if "router" in query_norm and any(cue in query_norm for cue in self_mod_cues):
        selected = "Manual router review route"
        matched_rule = matched_rule or {
            "intent_family": "router_self_modification",
            "availability_status": "blocked",
            "fallback": "生成候选变更包并等待 Murphy 明确人工批准；不得自动修改正式 router。",
            "short_reason": "Router 不能给自身 live 修改或晋升授权。",
            "confidence": 0.99,
            "requires_confirmation": True,
            "risk_class": "workspace_write",
        }
        scores[selected] = 100.0

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    ranked_names = [name for name, _ in ranked if name != selected]
    ordered_names = [selected, *ranked_names]
    unique_names = []
    for name in ordered_names:
        if name not in unique_names:
            unique_names.append(name)
        if len(unique_names) == 3:
            break

    risk_class = classify_risk(query_norm, rules, matched_rule)
    forced_status = matched_rule.get("availability_status") if matched_rule else None
    availability_status, capability_fallback = resolve_availability(
        selected, catalog, availability, forced_status
    )
    fallback = (matched_rule or {}).get("fallback") or capability_fallback
    if availability_status != "available" and not fallback:
        fallback = "报告缺失依赖或权限并请求人工处理；不得声称已经执行。"

    high_risk = risk_class in {"external_action", "sensitive", "financial"}
    confirmation = bool((matched_rule or {}).get("requires_confirmation", False) or high_risk)
    confidence = float((matched_rule or {}).get("confidence", 0.0))
    if not confidence:
        top = ranked[0][1] if ranked else 0.0
        second = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = top - second
        confidence = round(min(0.89, 0.50 + max(0.0, margin) / 4), 3)
    confidence = round(max(0.0, min(1.0, confidence)), 3)

    candidate_skills = []
    for name in unique_names:
        status, _ = resolve_availability(name, catalog, availability)
        if name == selected:
            status = availability_status
        candidate_skills.append(
            {
                "skill": name,
                "score": round(float(scores.get(name, 0.0)), 4),
                "availability_status": status,
            }
        )

    intent_family = (matched_rule or {}).get("intent_family") or inferred_intent(selected)
    context_key = reflection_context_key(intent_family, matched_rule, risk_class)
    decision_id = hashlib.sha256(
        json.dumps(
            {
                "context_key": context_key,
                "base_selected_skill": selected,
                "catalog_fingerprint": catalog_fingerprint(catalog),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:24]
    advisory = {
        "context_key": context_key,
        "base_selected_skill": selected,
        "suggested_skill": None,
        "evidence_count": 0,
        "applied": False,
        "reason_code": "no_preference",
    }

    if preference_profile is None:
        preference_profile = (
            load_json(DEFAULT_PREFERENCE_OVERLAY) if DEFAULT_PREFERENCE_OVERLAY.exists() else {}
        )
    preferences = preference_profile.get("active_preferences", {}) if preference_profile else {}
    preference = preferences.get(context_key) if preference_profile.get("enabled", True) else None
    if preference is not None:
        target = preference.get("preferred_skill")
        advisory["suggested_skill"] = target
        advisory["evidence_count"] = int(preference.get("evidence_count", 0))
        base_top3 = [item["skill"] for item in candidate_skills]
        expires_at = _parse_timestamp(preference.get("expires_at", ""))
        protected_intent = intent_family in {
            "router_self_modification",
            "account_action",
            "secret_handling",
        }
        target_status, target_fallback = resolve_availability(target or "", catalog, availability)
        target_capability = catalog.get("capabilities", {}).get(target or "", {})
        current_skill_fingerprint = target_capability.get("source_fingerprint", "")
        preference_skill_fingerprint = preference.get("preferred_skill_fingerprint", "")
        reason = "applied"
        if preference.get("state") != "active":
            reason = "preference_not_active"
        elif runtime_release_id and preference.get("release_id") != runtime_release_id:
            reason = "release_changed"
        elif preference.get("catalog_fingerprint") != catalog_fingerprint(catalog):
            reason = "catalog_changed"
        elif preference_skill_fingerprint != current_skill_fingerprint:
            reason = "skill_changed"
        elif not expires_at or expires_at <= _utc_now():
            reason = "preference_expired"
        elif protected_intent:
            reason = "protected_intent"
        elif risk_class in {"external_action", "sensitive", "financial"}:
            reason = "protected_risk"
        elif availability_status != "available":
            reason = "base_unavailable"
        elif target not in base_top3:
            reason = "target_not_in_base_top3"
        elif target_status != "available":
            reason = "target_unavailable"

        advisory["reason_code"] = reason
        if reason == "applied":
            base_selected = selected
            selected = target
            candidate_skills.sort(key=lambda item: item["skill"] != target)
            target_risk = target_capability.get("risk_class", "read_only")
            risk_class = _stricter_risk(risk_class, target_risk)
            confirmation = bool(
                confirmation or risk_class in {"external_action", "sensitive", "financial"}
            )
            availability_status = target_status
            fallback = target_fallback or fallback
            advisory["applied"] = True
            advisory["base_selected_skill"] = base_selected

    return {
        "protocol_version": "router-v3.0-shadow",
        "decision_id": decision_id,
        "intent_family": intent_family,
        "candidate_skills": candidate_skills,
        "selected_skill": selected,
        "confidence": confidence,
        "requires_confirmation": confirmation,
        "risk_class": risk_class,
        "availability_status": availability_status,
        "fallback": fallback or "",
        "short_reason": (matched_rule or {}).get("short_reason")
        or "Catalog and existing map retrieval agree on the strongest available route.",
        "decision_scope": "recommendation_only",
        "execution_authorized": False,
        "model_review": {
            "used": False,
            "review_recommended": confidence < 0.70,
            "version": None,
            "estimated_cost_usd": 0.0,
        },
        "reflection_advisory": advisory,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--availability", type=Path)
    args = parser.parse_args()
    availability = load_json(args.availability) if args.availability else {}
    decision = route_decision(
        args.query,
        catalog=load_json(args.catalog),
        rules=load_json(args.rules),
        availability=availability,
    )
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
