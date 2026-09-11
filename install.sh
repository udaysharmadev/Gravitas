#!/usr/bin/env bash
set -e

echo "Installing Gravitas for Antigravity..."

# Default installation directory for workspace-local
TARGET_DIR=".agents/skills"
mkdir -p "$TARGET_DIR"

echo "Downloading Gravitas skills..."
TMP_DIR=$(mktemp -d)
git clone --depth 1 https://github.com/udaysharmadev/Gravitas.git "$TMP_DIR" > /dev/null 2>&1

cp -r "$TMP_DIR/skills/"* "$TARGET_DIR/"
rm -rf "$TMP_DIR"

echo "✅ Gravitas successfully installed in $TARGET_DIR/"
echo "Available skills:"
ls -1 "$TARGET_DIR"

echo ""
echo "To activate the Antigravity runtime hooks, run:"
echo "agy plugin install udaysharmadev/Gravitas"
