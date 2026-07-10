#!/usr/bin/env bash
set -euo pipefail

roots=(
  "${CODEX_HOME:-$HOME/.codex}/skills"
  "$HOME/.codex/superpowers/skills"
)

for root in "${roots[@]}"; do
  [ -d "$root" ] || continue
  find "$root" -maxdepth 2 -name SKILL.md -print
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
      if (file ~ "/\\.codex/superpowers/skills/" && name !~ /^superpowers:/) {
        name="superpowers:" name
      }
      if (name != "") print file "|" name "|" desc
      exit
    }
  ' "$file"
done
