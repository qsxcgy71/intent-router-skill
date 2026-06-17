#!/usr/bin/env python3
"""Evaluate intent-router route-card recall against a golden dataset.

This intentionally simple scorer treats `references/skill-map.md` as a tiny
retrieval corpus. It checks whether the expected route appears within top-k. It
is not a full semantic evaluator; it is a cheap regression guard for stale
triggers, noisy comparison rows, and obvious rerank drift.
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
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "be",
    "for",
    "from",
    "give",
    "help",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "not",
    "of",
    "on",
    "or",
    "run",
    "the",
    "this",
    "to",
    "use",
    "with",
}


def normalize_route(route: str) -> str:
    route = route.strip().replace("`", "")
    route = re.sub(r"\s+", " ", route)
    return route


def ascii_words(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9][a-z0-9:_./+-]*", text.lower()) if word not in STOPWORDS}


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
    return name, desc


def installed_skill_docs() -> dict[str, str]:
    roots = [
        Path.home() / ".codex" / "skills",
        Path.home() / ".codex" / "superpowers" / "skills",
        Path.home() / ".agents" / "skills",
    ]
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
        "Ambiguity Rules",
        "Personalization Slots",
    }
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("## "):
            current_section = raw.lstrip("# ").strip()
            continue
        if current_section in skip_sections:
            continue
        if not raw.startswith("|") or raw.startswith("|---") or raw.startswith("| Route"):
            continue
        parts = [p.strip() for p in raw.strip().strip("|").split("|")]
        if len(parts) < 2:
            continue
        route = normalize_route(parts[0])
        if not route or route.lower() in {"route", "skill"}:
            continue
        docs.setdefault(route, "")
        docs[route] += f"\n{current_section} " + " ".join(parts)
    return docs


def candidate_docs(map_path: Path, include_installed_skills: bool = False) -> dict[str, str]:
    docs = map_route_docs(map_path)
    if not include_installed_skills:
        return docs
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--show-failures", action="store_true")
    parser.add_argument(
        "--include-installed-skills",
        action="store_true",
        help="Also score frontmatter from local ~/.codex and ~/.agents skills.",
    )
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    docs = candidate_docs(args.map, include_installed_skills=args.include_installed_skills)

    total = 0
    hit = 0
    top1 = 0
    failures = []

    for case in dataset["cases"]:
        total += 1
        top = rank(case["query"], docs, args.k)
        routes = [route for route, _ in top]
        expected = case["expected_primary"]
        must_not_top1 = set(case.get("must_not_top1", []))
        case_hit = any(route_matches(expected, route) for route in routes)
        case_top1 = bool(routes) and route_matches(expected, routes[0])
        blocked_top1 = bool(routes) and any(route_matches(blocked, routes[0]) for blocked in must_not_top1)
        hit += int(case_hit and not blocked_top1)
        top1 += int(case_top1 and not blocked_top1)
        if not case_hit or blocked_top1:
            reason = "blocked_top1" if blocked_top1 else "miss"
            failures.append((case["id"], expected, routes, reason))

    print(f"cases={total} top1={top1}/{total} hit@{args.k}={hit}/{total} ({hit/total:.1%})")
    if failures:
        print("failures:")
        for case_id, expected, routes, reason in failures:
            print(f"- {case_id}: expected={expected!r} got={routes} reason={reason}")
    elif args.show_failures:
        print("failures: none")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
