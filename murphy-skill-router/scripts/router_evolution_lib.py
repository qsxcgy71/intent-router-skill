#!/usr/bin/env python3
"""Shared helpers for Murphy router self-evolution scripts."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


SKILL_DIR = Path(__file__).resolve().parents[1]
REFERENCES_DIR = SKILL_DIR / "references"
SCRIPTS_DIR = SKILL_DIR / "scripts"
BASELINES_DIR = SKILL_DIR / "baselines"
RELEASES_DIR = SKILL_DIR / "releases"
CANDIDATES_DIR = SKILL_DIR / "candidates"
REPORTS_DIR = REFERENCES_DIR / "evolution-reports"
CURRENT_RELEASE = SKILL_DIR / "current-release.json"
DECISIONS_LOG = REFERENCES_DIR / "evolution-decisions.jsonl"
EVOLUTION_LOG = REFERENCES_DIR / "evolution-log.jsonl"

FAILURE_TYPES = {
    "facet_miss",
    "retrieval_miss",
    "evidence_miss",
    "rerank_miss",
    "threshold_miss",
    "dependency_miss",
    "mode_miss",
    "map_stale",
    "tool_name_stale",
    "safety_gate_miss",
    "plugin_callability_miss",
    "cost_gate_miss",
    "external_side_effect_miss",
}

PROMOTABLE_REFERENCE_FILES = {
    "baseline-2026-07-10.json",
    "capability-catalog.json",
    "capability-overrides.json",
    "eval-freeze.json",
    "evolution-system.md",
    "router-v2-architecture.md",
    "router-v2-maintenance.md",
    "router-v3-feedback-loop.md",
    "router-v2-rules.json",
    "router-v3-feedback-loop.md",
    "router-eval-ambiguity.json",
    "skill-map.md",
    "router-eval-cases.md",
    "router-eval-dataset.json",
    "router-eval-train.json",
    "router-eval-heldout.json",
    "router-eval-safety.json",
    "router-eval-regression.json",
    "router-eval-feedback.json",
    "route-feedback.schema.json",
    "router-preference-overlay.json",
}

V2_REFERENCE_FILES = {
    "baseline-2026-07-10.json",
    "capability-catalog.json",
    "capability-overrides.json",
    "eval-freeze.json",
    "router-v2-architecture.md",
    "router-v2-maintenance.md",
    "router-v2-rules.json",
    "router-eval-ambiguity.json",
    "router-eval-feedback.json",
    "route-feedback.schema.json",
    "router-preference-overlay.json",
}

V2_SCRIPT_FILES = {
    "build_capability_catalog.py",
    "eval_router_v2.py",
    "parse_router_eval_cases.py",
    "router_v2.py",
    "shadow_route.py",
    "test_router_v2.py",
    "post_task_reflection.py",
    "build_preference_overlay.py",
    "test_router_feedback.py",
}

GUARD_SCRIPT_FILES = {
    "eval_router_dataset.py",
    "evolution_gate.py",
    "promote_router_candidate.py",
    "router_evolution_lib.py",
}


def now_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slugify(value: str, fallback: str = "candidate") -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-").lower()
    return slug or fallback


def ensure_runtime_dirs(root: Path = SKILL_DIR) -> None:
    for path in [
        root / "baselines",
        root / "releases",
        root / "candidates",
        root / "references" / "evolution-reports",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_no}: invalid jsonl: {exc}") from exc
    return rows


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_core_files(root: Path) -> Iterable[Path]:
    for rel in ["SKILL.md"]:
        path = root / rel
        if path.exists():
            yield path
    for name in sorted(PROMOTABLE_REFERENCE_FILES):
        path = root / "references" / name
        if path.exists():
            yield path
    scripts = root / "scripts"
    if scripts.exists():
        for path in sorted(scripts.glob("*.py")):
            yield path


def relative_to_root(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def copy_core_tree(source: Path, dest: Path, include_scripts: bool = True) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    if (source / "SKILL.md").exists():
        shutil.copy2(source / "SKILL.md", dest / "SKILL.md")
    ref_dest = dest / "references"
    ref_dest.mkdir(exist_ok=True)
    for name in sorted(PROMOTABLE_REFERENCE_FILES):
        src = source / "references" / name
        if src.exists():
            shutil.copy2(src, ref_dest / name)
    if include_scripts and (source / "scripts").exists():
        scripts_dest = dest / "scripts"
        scripts_dest.mkdir(exist_ok=True)
        for src in sorted((source / "scripts").glob("*.py")):
            shutil.copy2(src, scripts_dest / src.name)


def copy_promoted_files(
    candidate: Path, live_root: Path = SKILL_DIR, *, prune_v2_extras: bool = False
) -> None:
    shutil.copy2(candidate / "SKILL.md", live_root / "SKILL.md")
    (live_root / "references").mkdir(exist_ok=True)
    for name in sorted(PROMOTABLE_REFERENCE_FILES):
        src = candidate / "references" / name
        if src.exists():
            shutil.copy2(src, live_root / "references" / name)
    scripts_src = candidate / "scripts"
    scripts_dest = live_root / "scripts"
    scripts_dest.mkdir(exist_ok=True)
    if scripts_src.exists():
        for src in sorted(scripts_src.glob("*.py")):
            shutil.copy2(src, scripts_dest / src.name)
    if prune_v2_extras:
        for name in sorted(V2_REFERENCE_FILES):
            if not (candidate / "references" / name).exists():
                path = live_root / "references" / name
                if path.exists():
                    path.unlink()
        for name in sorted(V2_SCRIPT_FILES):
            if not (candidate / "scripts" / name).exists():
                path = scripts_dest / name
                if path.exists():
                    path.unlink()


def current_release_state(root: Path = SKILL_DIR) -> dict:
    return read_json(root / "current-release.json", default={}) or {}


def file_checksums(root: Path) -> dict[str, str]:
    return {relative_to_root(path, root): sha256_file(path) for path in iter_core_files(root)}
