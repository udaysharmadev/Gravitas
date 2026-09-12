#!/usr/bin/env bash
# Build the tracked Antigravity plugin bundle from canonical sources.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bundle="$repo_root/dist/gravitas-antigravity"

if [[ "$bundle" != "$repo_root/dist/gravitas-antigravity" ]]; then
  echo "Refusing unexpected bundle path: $bundle" >&2
  exit 1
fi

rm -rf "$bundle"
mkdir -p "$bundle/scripts" "$bundle/skills" "$bundle/agents"

cp "$repo_root/plugins/gravitas-antigravity/plugin.json" "$bundle/plugin.json"
cp "$repo_root/plugins/gravitas-antigravity/hooks.json" "$bundle/hooks.json"
cp -R "$repo_root/plugins/gravitas-antigravity/scripts/." "$bundle/scripts/"
cp -R "$repo_root/skills/gravitas" "$bundle/skills/gravitas"
cp -R "$repo_root/plugins/gravitas-antigravity/agents/." "$bundle/agents/"

find "$bundle" -type d -name '__pycache__' -prune -exec rm -rf {} +
echo "Built $bundle"
