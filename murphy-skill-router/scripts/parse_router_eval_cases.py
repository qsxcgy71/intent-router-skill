#!/usr/bin/env python3
"""Extract all YAML case-list blocks from router-eval-cases Markdown.

The parser deliberately ignores schema/example blocks that are mappings. It
supports the scalar and list shapes used by the router case reference without
adding a YAML dependency.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path


FENCE = re.compile(r"```ya?ml\s*\n(.*?)```", re.IGNORECASE | re.DOTALL)


def scalar(value: str):
    value = value.strip()
    if not value:
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    if value.startswith(("[", "{", "'", '"')):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            pass
    return value.strip("\"'")


def parse_case_list(block: str) -> list[dict]:
    lines = block.splitlines()
    first = next((line.strip() for line in lines if line.strip()), "")
    if not first.startswith("- id:"):
        return []
    cases: list[dict] = []
    current: dict | None = None
    list_key: str | None = None
    for raw in lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        stripped = raw.strip()
        if raw.startswith("- id:"):
            if current:
                cases.append(current)
            current = {"id": scalar(raw.split(":", 1)[1])}
            list_key = None
            continue
        if current is None:
            continue
        if raw.startswith("  ") and not raw.startswith("    - ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            parsed = scalar(value)
            current[key] = parsed
            list_key = key if parsed == "" else None
            continue
        if raw.startswith("    - ") and list_key:
            if not isinstance(current.get(list_key), list):
                current[list_key] = []
            current[list_key].append(scalar(stripped[2:]))
    if current:
        cases.append(current)
    return cases


def parse_markdown_cases(path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8")
    cases = []
    for match in FENCE.finditer(content):
        cases.extend(parse_case_list(match.group(1)))
    return cases


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print(json.dumps(parse_markdown_cases(args.path), ensure_ascii=False, indent=2))
