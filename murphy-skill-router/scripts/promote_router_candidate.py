#!/usr/bin/env python3
"""Promote or rollback Murphy router self-evolution releases."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from router_evolution_lib import (
    BASELINES_DIR,
    CURRENT_RELEASE,
    DECISIONS_LOG,
    RELEASES_DIR,
    REPORTS_DIR,
    SKILL_DIR,
    append_jsonl,
    copy_core_tree,
    copy_promoted_files,
    current_release_state,
    now_id,
    slugify,
    write_json,
)


def run_gate(candidate: Path, suite: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SKILL_DIR / "scripts" / "evolution_gate.py"),
            "--candidate",
            str(candidate),
            "--suite",
            suite,
            "--write-report",
        ],
        cwd=SKILL_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def release_source_for(release_id: str, live_root: Path) -> Path:
    release = live_root / "releases" / release_id
    if release.exists():
        return release
    baseline = live_root / "baselines" / release_id
    if baseline.exists():
        return baseline
    raise SystemExit(f"release not found: {release_id}")


def validate_promotion_request(*, auto: bool, approved_by_user: bool) -> bool:
    """Promotion is never automatic; an explicit user-approval flag is required."""
    return bool(approved_by_user and not auto)


def promote(
    candidate: Path,
    suite: str,
    auto: bool,
    approved_by_user: bool,
    live_root: Path = SKILL_DIR,
    rollback_release_override: str | None = None,
) -> int:
    if not validate_promotion_request(auto=auto, approved_by_user=approved_by_user):
        raise SystemExit(
            "automatic promotion disabled; rerun only after explicit user approval "
            "with --approved-by-user and without --auto"
        )
    candidate = candidate.resolve()
    live_root = live_root.resolve()
    gate = run_gate(candidate, suite)
    print(gate.stdout, end="")
    if gate.returncode != 0:
        print("promotion blocked: gate failed")
        return gate.returncode

    previous = current_release_state(live_root).get("current_release") or "baseline-2026-06-17"
    rollback_release = rollback_release_override or f"{now_id()}-pre-promotion-live-snapshot"
    rollback_path = live_root / "releases" / rollback_release
    if rollback_release_override:
        if not rollback_path.exists():
            raise SystemExit(f"requested rollback snapshot not found: {rollback_path}")
    else:
        copy_core_tree(live_root, rollback_path, include_scripts=True)
    release_id = f"{now_id()}-{slugify(candidate.name)}"
    release_path = live_root / "releases" / release_id
    copy_core_tree(candidate, release_path, include_scripts=True)
    copy_promoted_files(candidate, live_root, prune_v2_extras=True)
    # Runtime feedback is deliberately excluded from release snapshots. Create
    # an empty local ledger so a promoted Router can begin shadow feedback
    # without inheriting task outcomes from any candidate or older release.
    (live_root / "references" / "route-feedback.jsonl").touch(exist_ok=True)

    write_json(
        live_root / "current-release.json",
        {
            "current_release": release_id,
            "current_path": f"releases/{release_id}",
            "rollback_release": rollback_release,
            "previous_declared_release": previous,
            "updated_at": now_id(),
            "strategy": "manual_approval_after_gate",
            "runtime_mode": "shadow_only",
            "candidate": str(candidate),
        },
    )
    append_jsonl(
        live_root / "references" / "evolution-decisions.jsonl",
        {
            "timestamp": now_id(),
            "candidate": str(candidate),
            "decision": "promoted",
            "release": release_id,
            "rollback_release": rollback_release,
            "previous_declared_release": previous,
        },
    )

    post = subprocess.run(
        [sys.executable, str(live_root / "scripts" / "eval_router_v2.py"), "--suite", "all", "--show-failures"],
        cwd=live_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(post.stdout, end="")
    if post.returncode != 0:
        print("warning: post-promotion suite failed; run rollback immediately")
        return post.returncode
    print(f"promoted={release_id}")
    return 0


def rollback(live_root: Path = SKILL_DIR) -> int:
    live_root = live_root.resolve()
    state = current_release_state(live_root)
    target = state.get("rollback_release")
    current = state.get("current_release")
    if not target:
        raise SystemExit("no rollback_release recorded")
    source = release_source_for(target, live_root)
    copy_promoted_files(source, live_root, prune_v2_extras=True)
    (live_root / "references" / "route-feedback.jsonl").touch(exist_ok=True)
    write_json(
        live_root / "current-release.json",
        {
            "current_release": target,
            "current_path": str(source.relative_to(live_root)),
            "rollback_release": current,
            "updated_at": now_id(),
            "strategy": "manual_approval_after_gate",
            "runtime_mode": "shadow_only",
            "operation": "rollback",
        },
    )
    append_jsonl(
        live_root / "references" / "evolution-decisions.jsonl",
        {
            "timestamp": now_id(),
            "decision": "rollback",
            "from_release": current,
            "to_release": target,
        },
    )
    print(f"rolled_back_to={target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--suite", default="all")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--approved-by-user", action="store_true")
    parser.add_argument("--live-root", type=Path, default=SKILL_DIR)
    parser.add_argument("--rollback-release", help="existing full snapshot to retain as rollback target")
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args()

    if args.rollback:
        return rollback(args.live_root)
    if not args.candidate:
        raise SystemExit("--candidate is required unless --rollback is used")
    return promote(
        args.candidate,
        args.suite,
        args.auto,
        args.approved_by_user,
        args.live_root,
        args.rollback_release,
    )


if __name__ == "__main__":
    raise SystemExit(main())
