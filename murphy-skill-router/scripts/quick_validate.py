#!/usr/bin/env python3
"""Fast, read-only structural validation for a Router v2 candidate."""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path


REQUIRED = [
    "SKILL.md",
    "current-release.json",
    "references/skill-map.md",
    "references/capability-catalog.json",
    "references/capability-overrides.json",
    "references/router-v2-rules.json",
    "references/router-eval-train.json",
    "references/router-eval-heldout.json",
    "references/router-eval-safety.json",
    "references/router-eval-regression.json",
    "references/router-eval-ambiguity.json",
    "references/router-eval-feedback.json",
    "references/route-feedback.schema.json",
    "references/route-feedback.jsonl",
    "references/router-preference-overlay.json",
    "references/eval-freeze.json",
    "scripts/router_v2.py",
    "scripts/eval_router_v2.py",
    "scripts/shadow_route.py",
    "scripts/post_task_reflection.py",
    "scripts/build_preference_overlay.py",
]


def validate(root: Path) -> list[str]:
    errors = [f"missing: {rel}" for rel in REQUIRED if not (root / rel).exists()]
    if errors:
        return errors
    skill_text = (root / "SKILL.md").read_text(encoding="utf-8")
    if not skill_text.startswith("---\n"):
        errors.append("SKILL.md frontmatter opening missing")
    header = skill_text.split("---", 2)[1] if skill_text.count("---") >= 2 else ""
    if not re.search(r"^name:\s*murphy-skill-router\s*$", header, re.MULTILINE):
        errors.append("SKILL.md name mismatch")
    if not re.search(r"^description:\s*.+$", header, re.MULTILINE):
        errors.append("SKILL.md description missing")

    json_paths = list((root / "references").glob("*.json")) + [root / "current-release.json"]
    for path in json_paths:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON: {path.relative_to(root)}:{exc.lineno}")

    sys.path.insert(0, str(root / "scripts"))
    try:
        evaluator = importlib.import_module("eval_router_v2")
        parser = importlib.import_module("parse_router_eval_cases")
        suite_paths = {
            name: root / "references" / f"router-eval-{name}.json"
            for name in ("train", "heldout", "safety", "regression", "ambiguity", "feedback")
        }
        errors.extend(evaluator.validate_suite_isolation(suite_paths))
        markdown_cases = parser.parse_markdown_cases(root / "references" / "router-eval-cases.md")
        if len(markdown_cases) < 80:
            errors.append(f"multi-YAML case parse unexpectedly small: {len(markdown_cases)}")
    finally:
        sys.path.pop(0)

    catalog_path = root / "references" / "capability-catalog.json"
    catalog_text = catalog_path.read_text(encoding="utf-8")
    catalog = json.loads(catalog_text)
    if catalog.get("inventory_count") != len(catalog.get("capabilities", {})):
        errors.append("catalog inventory_count mismatch")
    for name in (
        "futu-supervisor-closer",
        "codex-network-lifeline-diagnoser",
        "interview-portfolio-evidence-packager",
        "notion-morning-evidence-coach",
    ):
        if name not in catalog.get("capabilities", {}):
            errors.append(f"catalog missing recent skill: {name}")
    if re.search(r"/Users/[^/\s]+", catalog_text):
        errors.append("catalog contains machine-specific home path")
    if re.search(r"sk-(?:proj-)?[A-Za-z0-9_-]{12,}", catalog_text):
        errors.append("catalog appears to contain a secret value")

    release = json.loads((root / "current-release.json").read_text(encoding="utf-8"))
    if release.get("strategy") != "manual_approval_after_gate":
        errors.append("release strategy is not manual_approval_after_gate")
    if release.get("runtime_mode") != "shadow_only":
        errors.append("runtime mode is not shadow_only")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        print("quick-validation: failed")
        for error in errors:
            print(f"- {error}")
        return 1
    print("quick-validation: ok")
    print("suites=train,heldout,safety,regression,ambiguity,feedback isolated")
    print("catalog=structured-and-sanitized")
    print("release=shadow-only-manual-approval")
    print("feedback=bounded-overlay-no-auto-promotion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
