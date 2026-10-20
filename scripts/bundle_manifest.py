#!/usr/bin/env python3
"""Generate the deterministic content manifest for the tracked plugin bundle.

The manifest lists every bundled file as ``<sha256>  <posix-relative-path>``.
Two properties keep it reproducible across operating systems, so that
``git diff --exit-code -- dist/gravitas-antigravity`` reports real drift
instead of checkout noise:

- Digests cover LF-normalized content, so a CRLF checkout (Windows with
  ``core.autocrlf=true``) hashes identically to an LF checkout. Lone CR
  endings are normalized the same way, so all three common newline forms
  produce one digest.
- Entries are ordered by the POSIX relative path as a plain string. Sorting
  ``Path`` objects instead would be case-insensitive on Windows and
  case-sensitive on POSIX, which reorders uppercase filenames.

Only the manifest at the bundle root is excluded from its own listing, so a
nested file that happens to share the name stays covered.

The manifest file itself is written with LF bytes so the tracked artifact
does not change shape between platforms either.

This module is the single source of truth for the manifest: the build
script calls it and ``tests/test_bundle_manifest.py`` exercises it.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

MANIFEST_NAME = "SHA256SUMS"


def normalized_digest(path: Path) -> str:
    """Return the sha256 of a file's content with line endings normalized to LF.

    CRLF and lone CR endings both collapse to LF, so equivalent content
    hashes identically regardless of the newline form it was written with.
    """
    content = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(content).hexdigest()


def manifest_entries(bundle: Path) -> list[str]:
    """Return the manifest lines for every bundled file, in deterministic order.

    Only the manifest at the bundle root is skipped; a nested file with the
    same name is listed and hashed like any other.
    """
    paths = sorted(
        (
            path
            for path in bundle.rglob("*")
            if path.is_file() and path.relative_to(bundle).as_posix() != MANIFEST_NAME
        ),
        key=lambda path: path.relative_to(bundle).as_posix(),
    )
    return [
        f"{normalized_digest(path)}  {path.relative_to(bundle).as_posix()}"
        for path in paths
    ]


def render_manifest(bundle: Path) -> str:
    """Render the manifest text, using LF line endings on every platform."""
    return "\n".join(manifest_entries(bundle)) + "\n"


def write_manifest(bundle: Path) -> Path:
    """Write the manifest as LF bytes and return its path."""
    target = bundle / MANIFEST_NAME
    target.write_bytes(render_manifest(bundle).encode("utf-8"))
    return target


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: bundle_manifest.py <bundle-dir>", file=sys.stderr)
        return 2
    bundle = Path(args[0]).resolve()
    if not bundle.is_dir():
        print(f"not a directory: {bundle}", file=sys.stderr)
        return 2
    write_manifest(bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
