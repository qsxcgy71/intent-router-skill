#!/usr/bin/env python3
"""Evaluate Murphy router map recall against a small golden dataset.

This is intentionally dumb: it treats the router as a RAG surface and checks
whether route cards / installed skill descriptions retrieve the expected route
within top-k. It is not a substitute for human judgment, but it catches stale
triggers and obvious rerank drift.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = SKILL_DIR / "references" / "router-eval-dataset.json"
DEFAULT_MAP = SKILL_DIR / "references" / "skill-map.md"
SUITE_DATASETS = {
    "train": SKILL_DIR / "references" / "router-eval-train.json",
    "heldout": SKILL_DIR / "references" / "router-eval-heldout.json",
    "safety": SKILL_DIR / "references" / "router-eval-safety.json",
    "regression": SKILL_DIR / "references" / "router-eval-regression.json",
}


def normalize_route(route: str) -> str:
    route = route.strip().replace("`", "")
    route = re.sub(r"\s+", " ", route)
    return route


def ascii_words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9:_./+-]*", text.lower()))


def cjk_ngrams(text: str) -> set[str]:
    chars = re.findall(r"[\u4e00-\u9fff]", text)
    grams: set[str] = set()
    # Single CJK characters are too noisy for routing; keep phrases only.
    grams.update("".join(chars[i : i + 2]) for i in range(max(0, len(chars) - 1)))
    grams.update("".join(chars[i : i + 3]) for i in range(max(0, len(chars) - 2)))
    return grams


def tokens(text: str) -> set[str]:
    return ascii_words(text) | cjk_ngrams(text)


def parse_skill_frontmatter(path: Path) -> tuple[str, str] | None:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    name = ""
    desc = ""
    for line in lines[1:80]:
        if line.strip() == "---":
            break
        if line.startswith("name:") and not name:
            name = line.split(":", 1)[1].strip().strip("\"'")
        if line.startswith("description:") and not desc:
            desc = line.split(":", 1)[1].strip().strip("\"'")
    if not name:
        return None
    if "/.codex/superpowers/skills/" in str(path) and not name.startswith("superpowers:"):
        name = f"superpowers:{name}"
    return name, desc


def installed_skill_docs() -> dict[str, str]:
    home = Path.home()
    roots = [home / ".codex" / "skills", home / ".codex" / "superpowers" / "skills"]
    docs: dict[str, str] = {}
    for root in roots:
        if not root.exists():
            continue
        for skill_file in root.glob("*/SKILL.md"):
            parsed = parse_skill_frontmatter(skill_file)
            if not parsed:
                continue
            name, desc = parsed
            docs.setdefault(name, "")
            docs[name] += f"\n{name} {desc} {skill_file.parent.name}"
    return docs


def map_route_docs(path: Path) -> dict[str, str]:
    docs: dict[str, str] = {}
    current_section = ""
    skip_sections = {
        "RAG Mental Model For Routing",
        "Plugin, Connector, Cost, And Side-Effect Rules",
        "Murphy Recurring Workflows",
        "Ambiguity Rules",
    }
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("## "):
            current_section = raw.lstrip("# ").strip()
            continue
        if current_section in skip_sections:
            continue
        if not raw.startswith("|") or raw.startswith("|---") or raw.startswith("| Skill"):
            continue
        parts = [p.strip() for p in raw.strip().strip("|").split("|")]
        if len(parts) < 2:
            continue
        raw_route = parts[0]
        # Ignore comparison/metadata table rows. Route rows either name a skill
        # with backticks or explicitly say route/plugin/connector/direct.
        routeish = (
            "`" in raw_route
            or "route" in raw_route.lower()
            or "plugin" in raw_route.lower()
            or "connector" in raw_route.lower()
            or raw_route.startswith("Direct:")
        )
        if not routeish:
            continue
        route = normalize_route(raw_route)
        if not route or route.lower() in {"route", "skill"}:
            continue
        docs.setdefault(route, "")
        docs[route] += f"\n{current_section} " + " ".join(parts)
    return docs


def candidate_docs(map_path: Path) -> dict[str, str]:
    docs = map_route_docs(map_path)
    for route, doc in installed_skill_docs().items():
        docs.setdefault(route, "")
        docs[route] += "\n" + doc
    return docs


def score(query: str, route: str, doc: str) -> float:
    q = tokens(query)
    d = tokens(route + "\n" + doc)
    if not q or not d:
        return 0.0
    overlap = q & d
    # Short route-name matches should matter, but document evidence dominates.
    route_bonus = len(tokens(route) & q) * 1.5
    return len(overlap) / math.sqrt(len(d)) + route_bonus


def route_variants(route: str) -> set[str]:
    route = normalize_route(route)
    variants = {route}
    for part in re.split(r"\s+/\s+|,\s*", route):
        part = normalize_route(part)
        if part:
            variants.add(part)
    return variants


def route_matches(expected: str, actual: str) -> bool:
    expected_variants = route_variants(expected)
    actual_variants = route_variants(actual)
    if expected_variants & actual_variants:
        return True
    for exp in expected_variants:
        for act in actual_variants:
            if exp and act and (exp in act or act in exp):
                return True
    return False


def rank(query: str, docs: dict[str, str], limit: int) -> list[tuple[str, float]]:
    scored = [(route, score(query, route, doc)) for route, doc in docs.items()]
    scored.sort(key=lambda item: (-item[1], item[0]))
    return scored[:limit]


def load_cases(dataset_path: Path) -> list[dict]:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    return list(dataset["cases"])


def load_suite_cases(suite: str) -> list[tuple[str, list[dict]]]:
    if suite == "all":
        return [(name, load_cases(path)) for name, path in SUITE_DATASETS.items()]
    if suite not in SUITE_DATASETS:
        raise SystemExit(f"unknown suite {suite!r}; expected one of: {', '.join(SUITE_DATASETS)} or all")
    return [(suite, load_cases(SUITE_DATASETS[suite]))]


def evaluate_cases(cases: list[dict], map_path: Path, k: int = 3) -> dict:
    docs = candidate_docs(map_path)
    total = 0
    hit = 0
    top1 = 0
    failures = []

    for case in cases:
        total += 1
        top = rank(case["query"], docs, k)
        routes = [route for route, _ in top]
        expected = case["expected_primary"]
        must_not_top1 = set(case.get("must_not_top1", []))
        case_hit = any(route_matches(expected, route) for route in routes)
        case_top1 = bool(routes) and route_matches(expected, routes[0])
        blocked_top1 = bool(routes) and any(route_matches(blocked, routes[0]) for blocked in must_not_top1)
        hit += int(case_hit and not blocked_top1)
        top1 += int(case_top1 and not blocked_top1)
        if not case_hit or blocked_top1:
            failures.append(
                {
                    "id": case["id"],
                    "expected": expected,
                    "routes": routes,
                    "reason": "blocked_top1" if blocked_top1 else "miss",
                }
            )

    return {"total": total, "top1": top1, "hit": hit, "k": k, "failures": failures}


def print_result(label: str, result: dict, show_failures: bool) -> None:
    total = result["total"]
    hit = result["hit"]
    top1 = result["top1"]
    k = result["k"]
    prefix = f"{label}: " if label else ""
    print(f"{prefix}cases={total} top1={top1}/{total} hit@{k}={hit}/{total} ({hit/total:.1%})")
    failures = result["failures"]
    if failures:
        print("failures:")
        for failure in failures:
            print(
                f"- {failure['id']}: expected={failure['expected']!r} "
                f"got={failure['routes']} reason={failure['reason']}"
            )
    elif show_failures:
        print("failures: none")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--suite", choices=[*SUITE_DATASETS.keys(), "all"])
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--show-failures", action="store_true")
    args = parser.parse_args()

    if args.dataset and args.suite:
        raise SystemExit("--dataset and --suite are mutually exclusive")

    if args.suite:
        suite_results = []
        for suite_name, cases in load_suite_cases(args.suite):
            result = evaluate_cases(cases, args.map, args.k)
            suite_results.append((suite_name, result))
            print_result(suite_name, result, args.show_failures)
        failures = [failure for _, result in suite_results for failure in result["failures"]]
        if len(suite_results) > 1:
            total = sum(result["total"] for _, result in suite_results)
            top1 = sum(result["top1"] for _, result in suite_results)
            hit = sum(result["hit"] for _, result in suite_results)
            aggregate = {"total": total, "top1": top1, "hit": hit, "k": args.k, "failures": failures}
            print_result("all", aggregate, args.show_failures)
        return 1 if failures else 0

    dataset_path = args.dataset or DEFAULT_DATASET
    result = evaluate_cases(load_cases(dataset_path), args.map, args.k)
    print_result("", result, args.show_failures)
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
