#!/usr/bin/env bash
# Build the tracked Antigravity plugin bundle from canonical sources.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bundle="$repo_root/dist/gravitas-antigravity"

if [[ "$bundle" != "$repo_root/dist/gravitas-antigravity" ]]; then
  echo "Refusing unexpected bundle path: $bundle" >&2
  exit 1
fi

# Resolve the interpreter before touching the bundle: a missing or too-old
# Python must fail before the tracked tree is deleted.
probe='import sys; print("%d.%d" % sys.version_info[:2]); sys.exit(0 if sys.version_info >= (3, 9) else 1)'
py=""
rejected=""
for candidate in python3 python py; do
  command -v "$candidate" >/dev/null 2>&1 || continue
  if "$candidate" -c "$probe" >/dev/null 2>&1; then
    py="$candidate"
    break
  fi
  rejected="${rejected}${candidate} "
done
if [[ -z "$py" ]]; then
  if [[ -n "$rejected" ]]; then
    echo "No usable Python interpreter: ${rejected}did not satisfy the Python 3.9+ requirement" >&2
  else
    echo "No python interpreter found (need python3, python or py, version 3.9+)" >&2
  fi
  exit 1
fi

rm -rf "$bundle"
mkdir -p "$bundle/scripts" "$bundle/skills" "$bundle/agents" "$bundle/rules"

cp "$repo_root/plugins/gravitas-antigravity/plugin.json" "$bundle/plugin.json"
cp "$repo_root/plugins/gravitas-antigravity/hooks.json" "$bundle/hooks.json"
cp -R "$repo_root/plugins/gravitas-antigravity/scripts/." "$bundle/scripts/"
cp -R "$repo_root/skills/gravitas" "$bundle/skills/gravitas"
cp -R "$repo_root/skills/gravitas-highstakes" "$bundle/skills/gravitas-highstakes"
cp -R "$repo_root/plugins/gravitas-antigravity/agents/." "$bundle/agents/"
cp -R "$repo_root/plugins/gravitas-antigravity/rules/." "$bundle/rules/"

find "$bundle" -type d -name '__pycache__' -prune -exec rm -rf {} +

# Deterministic content manifest: LF-normalized sha256 over POSIX-sorted
# relative paths, so drift review distinguishes real changes from rebuild
# noise. The generator lives in scripts/bundle_manifest.py so the build and
# its regression test share one implementation.
"$py" "$repo_root/scripts/bundle_manifest.py" "$bundle"
echo "Built $bundle"
