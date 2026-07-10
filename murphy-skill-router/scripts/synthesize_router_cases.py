#!/usr/bin/env python3
"""Turn desensitized router failure logs into pending eval cases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from router_evolution_lib import EVOLUTION_LOG, FAILURE_TYPES, REFERENCES_DIR, now_id, slugify, write_json


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def synthesize(rows: list[dict]) -> list[dict]:
    cases = []
    seen = set()
    for row in rows:
        prompt = row.get("prompt_summary")
        expected = row.get("final_route")
        if not prompt or not expected:
            continue
        failure_type = row.get("failure_type", "unclassified")
        chosen = row.get("chosen_primary")
        key = (prompt, expected)
        if key in seen:
            continue
        seen.add(key)
        case = {
            "id": f"evolution-{slugify(expected)}-{len(cases)+1:03d}",
            "query": prompt,
            "expected_primary": expected,
            "expected_support": row.get("expected_support", []),
            "must_not_top1": [chosen] if chosen and chosen != expected else [],
            "rationale": row.get("user_correction_summary") or "Synthesized from desensitized router failure log.",
            "failure_type": failure_type if failure_type in FAILURE_TYPES else "unclassified",
            "source": "evolution-log",
        }
        cases.append(case)
    return cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=EVOLUTION_LOG)
    parser.add_argument("--output", type=Path, default=REFERENCES_DIR / "pending-router-eval-cases.json")
    args = parser.parse_args()

    cases = synthesize(load_jsonl(args.input))
    data = {
        "version": 1,
        "generated_at": now_id(),
        "description": "Pending eval cases synthesized from desensitized router evolution logs.",
        "cases": cases,
    }
    write_json(args.output, data)
    print(f"wrote {len(cases)} cases to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
