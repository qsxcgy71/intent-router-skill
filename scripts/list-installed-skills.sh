#!/usr/bin/env bash
set -euo pipefail

roots=(
  "${CODEX_HOME:-$HOME/.codex}/skills"
  "${CODEX_HOME:-$HOME/.codex}/plugins/cache"
  "$HOME/.codex/superpowers/skills"
  "$HOME/.agents/skills"
)

for root in "${roots[@]}"; do
  [ -d "$root" ] || continue
  find "$root" -maxdepth 8 -name SKILL.md -print
done | sort | while IFS= read -r file; do
  awk -v file="$file" '
    BEGIN { name=""; desc="" }
    /^name:/ && name=="" {
      name=$0
      sub(/^name:[[:space:]]*/, "", name)
    }
    /^description:/ && desc=="" {
      desc=$0
      sub(/^description:[[:space:]]*/, "", desc)
    }
    /^---$/ && NR>1 {
      if (name != "") print file "|" name "|" desc
      exit
    }
  ' "$file"
done
