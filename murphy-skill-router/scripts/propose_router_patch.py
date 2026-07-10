#!/usr/bin/env python3
"""Create a bounded router evolution candidate from pending cases."""

from __future__ import annotations

import argparse
import difflib
import json
import shutil
from pathlib import Path

from router_evolution_lib import CANDIDATES_DIR, SKILL_DIR, copy_core_tree, now_id, slugify, write_json


def load_cases(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("cases", [])


def merge_cases(existing: list[dict], additions: list[dict]) -> list[dict]:
    by_id = {case["id"]: case for case in existing}
    for case in additions:
        by_id.setdefault(case["id"], case)
    return list(by_id.values())


def append_trigger_to_route(skill_map: Path, route: str, trigger: str) -> bool:
    lines = skill_map.read_text(encoding="utf-8").splitlines()
    changed = False
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if not parts or parts[0].replace("`", "") != route.replace("`", ""):
            continue
        if trigger in parts[1]:
            return False
        parts[1] = f'{parts[1]}, "{trigger}"'
        lines[index] = "| " + " | ".join(parts) + " |"
        changed = True
        break
    if changed:
        skill_map.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


def unified_diff(before_root: Path, after_root: Path) -> str:
    output = []
    for rel in ["SKILL.md", "references/skill-map.md", "references/router-eval-regression.json"]:
        before = (before_root / rel).read_text(encoding="utf-8") if (before_root / rel).exists() else ""
        after = (after_root / rel).read_text(encoding="utf-8") if (after_root / rel).exists() else ""
        if before == after:
            continue
        output.extend(
            difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                fromfile=f"live/{rel}",
                tofile=f"candidate/{rel}",
                lineterm="",
            )
        )
    return "\n".join(output) + ("\n" if output else "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-file", type=Path, default=SKILL_DIR / "references" / "pending-router-eval-cases.json")
    parser.add_argument("--name", default="")
    parser.add_argument("--route", help="Route row to patch in references/skill-map.md")
    parser.add_argument("--trigger", help="Trigger phrase to append to the chosen route row")
    args = parser.parse_args()

    pending = load_cases(args.case_file)
    candidate_id = f"{now_id()}-{slugify(args.name or (args.route or 'router-evolution'))}"
    candidate = CANDIDATES_DIR / candidate_id
    copy_core_tree(SKILL_DIR, candidate, include_scripts=True)

    regression_path = candidate / "references" / "router-eval-regression.json"
    regression = json.loads(regression_path.read_text(encoding="utf-8"))
    regression["cases"] = merge_cases(regression.get("cases", []), pending)
    regression["source"] = "router-eval-regression plus pending evolution cases"
    write_json(regression_path, regression)

    changed_map = False
    if args.route and args.trigger:
        changed_map = append_trigger_to_route(candidate / "references" / "skill-map.md", args.route, args.trigger)

    diff = unified_diff(SKILL_DIR, candidate)
    (candidate / "proposed_patch.diff").write_text(diff, encoding="utf-8")
    write_json(
        candidate / "candidate-summary.json",
        {
            "id": candidate_id,
            "created_at": now_id(),
            "pending_cases_merged": len(pending),
            "route": args.route,
            "trigger": args.trigger,
            "skill_map_changed": changed_map,
            "bounded_edit_policy": "route trigger, anti-cue, ambiguity rule, first action, eval case only",
        },
    )
    print(f"candidate={candidate}")
    print(f"pending_cases_merged={len(pending)}")
    print(f"skill_map_changed={changed_map}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
