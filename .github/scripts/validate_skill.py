#!/usr/bin/env python3
"""Minimal dependency-free validation for the portable Gravitas skill in CI."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/gravitas/SKILL.md"


def main() -> int:
    text = SKILL.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        print("FAIL SKILL.md must begin with YAML frontmatter")
        return 1
    frontmatter, _, body = text[4:].partition("\n---\n")
    if not body:
        print("FAIL SKILL.md frontmatter must be closed")
        return 1
    for field in ("name:", "description:"):
        if field not in frontmatter:
            print(f"FAIL SKILL.md frontmatter is missing {field}")
            return 1
    if len(text.splitlines()) > 500:
        print("FAIL SKILL.md exceeds the 500-line skill guidance limit")
        return 1
    print("PASS Gravitas skill structure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
