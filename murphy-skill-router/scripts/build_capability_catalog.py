#!/usr/bin/env python3
"""Build a sanitized capability catalog from installed SKILL.md metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OVERRIDES = SKILL_DIR / "references" / "capability-overrides.json"
DEFAULT_OUTPUT = SKILL_DIR / "references" / "capability-catalog.json"
ACTIVE_PLUGIN_PROVIDERS = {
    "openai-bundled",
    "openai-curated-remote",
    "openai-primary-runtime",
    "personal",
}


def now_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_skill_roots(home: Path | None = None) -> list[tuple[str, Path, str]]:
    home = home or Path.home()
    roots: list[tuple[str, Path, str]] = [
        ("local", home / ".codex" / "skills", ""),
        ("agents", home / ".agents" / "skills", ""),
        ("superpowers", home / ".codex" / "superpowers" / "skills", "superpowers"),
    ]
    cache = home / ".codex" / "plugins" / "cache"
    if cache.exists():
        for provider in sorted(path for path in cache.iterdir() if path.is_dir()):
            if provider.name not in ACTIVE_PLUGIN_PROVIDERS:
                continue
            for package in sorted(path for path in provider.iterdir() if path.is_dir()):
                versions = sorted(path for path in package.iterdir() if path.is_dir())
                for version in versions[-1:]:
                    skill_root = version / "skills"
                    if skill_root.is_dir():
                        roots.append((f"plugin/{provider.name}/{package.name}", skill_root, package.name))
    return roots


def parse_frontmatter(path: Path) -> dict[str, str] | None:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    metadata: dict[str, str] = {}
    for line in lines[1:128]:
        if line.strip() == "---":
            break
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip("\"'")
    return metadata if metadata.get("name") else None


def logical_name(raw_name: str, namespace: str) -> str:
    if not namespace or ":" in raw_name:
        return raw_name
    return f"{namespace}:{raw_name}"


def source_ref(kind: str, root: Path, skill_file: Path) -> str:
    relative = skill_file.relative_to(root).as_posix()
    return f"{kind}/{relative}"


def discover_skill_files(
    roots: list[tuple[str, Path, str]] | None = None,
) -> list[dict]:
    discovered = []
    for kind, root, namespace in roots or default_skill_roots():
        if not root.exists():
            continue
        for skill_file in sorted(root.glob("*/SKILL.md")):
            discovered.append(
                {
                    "path": skill_file,
                    "kind": kind,
                    "root": root,
                    "namespace": namespace,
                }
            )
    return discovered


def load_overrides(path: Path) -> dict:
    if not path.exists():
        return {"capability_overrides": {}, "virtual_capabilities": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def inferred_risk(name: str, description: str) -> str:
    text = f"{name} {description}".lower()
    if any(term in text for term in ("trading", "broker", "stock", "financial", "futu", "equity")):
        return "financial"
    if any(term in text for term in ("email", "gmail", "notion", "account", "cookie", "credential")):
        return "sensitive"
    if any(term in text for term in ("deploy", "publish", "send", "calendar", "automation", "generate")):
        return "external_action"
    if any(term in text for term in ("create", "edit", "build", "write", "implement", "install")):
        return "workspace_write"
    return "read_only"


def sanitize_description(description: str) -> str:
    """Remove machine-specific home paths while preserving routing cues."""
    description = description.replace(str(Path.home()), "$HOME")
    return re.sub(r"/Users/[^/\s`]+", "$HOME", description)


def empty_dependencies() -> dict[str, list[str]]:
    return {"environment": [], "connectors": [], "plugins": [], "permissions": []}


def merge_capability(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if key == "dependencies":
            dependencies = empty_dependencies()
            dependencies.update(base.get("dependencies", {}))
            dependencies.update(value)
            merged[key] = {name: sorted(set(items)) for name, items in dependencies.items()}
        elif key == "aliases":
            merged[key] = sorted(set(base.get("aliases", [])) | set(value))
        else:
            merged[key] = value
    return merged


def build_catalog(discovered: list[dict], overrides: dict) -> dict:
    capabilities: dict[str, dict] = {}
    for item in discovered:
        path: Path = item["path"]
        metadata = parse_frontmatter(path)
        if not metadata:
            continue
        name = logical_name(metadata["name"], item["namespace"])
        description = sanitize_description(metadata.get("description", ""))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        capability = {
            "name": name,
            "description": description,
            "capability_type": "plugin_skill" if item["kind"].startswith("plugin/") else "local_skill",
            "source": source_ref(item["kind"], item["root"], path),
            "source_fingerprint": digest,
            "aliases": [],
            "risk_class": inferred_risk(name, description),
            "dependencies": empty_dependencies(),
            "availability": {"kind": "installed_skill"},
            "fallback": "",
        }
        capabilities.setdefault(name, capability)

    for name, data in overrides.get("virtual_capabilities", {}).items():
        base = {
            "name": name,
            "description": data.get("description", "Manually maintained route capability."),
            "capability_type": data.get("capability_type", "direct_route"),
            "source": "manual/explicit-route",
            "source_fingerprint": hashlib.sha256(
                json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "aliases": [],
            "risk_class": "read_only",
            "dependencies": empty_dependencies(),
            "availability": {"kind": "direct"},
            "fallback": "",
        }
        capabilities[name] = merge_capability(base, data)

    for name, override in overrides.get("capability_overrides", {}).items():
        if name not in capabilities:
            continue
        capabilities[name] = merge_capability(capabilities[name], override)

    return {
        "version": 2,
        "generated_at": now_id(),
        "generation_policy": "SKILL.md frontmatter plus bounded manual overrides; no secret values or user content",
        "source_roots": sorted({item["kind"] for item in discovered}),
        "inventory_count": len(capabilities),
        "capabilities": dict(sorted(capabilities.items())),
    }


def write_catalog(path: Path, catalog: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    overrides = load_overrides(args.overrides)
    catalog = build_catalog(discover_skill_files(), overrides)
    write_catalog(args.output, catalog)
    print(f"capabilities={catalog['inventory_count']}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
