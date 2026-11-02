#!/usr/bin/env python3
"""Keep the README contributor wall and CONTRIBUTORS.md in sync with GitHub.

Rules (deliberately conservative):
- Existing entries are never edited, removed, or reordered. The repo owner
  always stays first as maintainer.
- New contributors (merged-PR authors and repo contributors, humans only)
  are appended, ordered by earliest merged PR (then login).
- Credit text uses merged PR numbers plus short titles. Titles are filtered
  against the public-claims denylist enforced by
  ``scripts/check_readme_claims.py`` so automation can never introduce an
  unsupported benchmark claim; rejected titles degrade to bare ``#N`` refs.

Data source is the GitHub REST API, or fixture files for tests/offline use::

    python scripts/sync_contributors.py --owner O --repo R --token TOKEN
    python scripts/sync_contributors.py --check   # exit 1 if files would change
    python scripts/sync_contributors.py --contributors-json c.json --prs-json p.json

Exit codes: 0 = in sync (or synced OK), 1 = would change (--check) or error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
CONTRIBUTORS_PATH = ROOT / "CONTRIBUTORS.md"

API = "https://api.github.com"

# Mirrors the denylist in scripts/check_readme_claims.py. The unit test
# asserts every phrase there is covered here; keep both lists in sync.
PROHIBITED_PHRASES = [
    "gap closure",
    "Functional Solve Rate",
    "false completion rate",
    "99% Claude",
    "Claude replacement",
    "better than Claude",
    "Claude-like",
    "like Claude",
    "forces Gemini",
    "competitive with Claude",
]

_AVATAR_RE = re.compile(r"\[!\[([^\]]*)\]\(https://github\.com/([^)/\s]+)\.png[^)]*\)\]\(https://github\.com/([^)/\s]+)\)")
_BULLET_RE = re.compile(r"^- (.+?) \(\[@([^]]+)\]\(https://github\.com/[^)]+\)\) — (.*)$")


def api_get(url: str, token: str | None) -> object:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_contributors(owner: str, repo: str, token: str | None) -> list[str]:
    """Repo contributor logins (humans only), in API order."""
    logins: list[str] = []
    page = 1
    while True:
        data = api_get(f"{API}/repos/{owner}/{repo}/contributors?per_page=100&page={page}", token)
        if not isinstance(data, list) or not data:
            break
        for entry in data:
            if isinstance(entry, dict) and entry.get("type") == "User" and entry.get("login"):
                if entry["login"] not in logins:
                    logins.append(entry["login"])
        if len(data) < 100 or page >= 5:
            break
        page += 1
    return logins


def fetch_merged_prs(owner: str, repo: str, token: str | None) -> dict[str, list[dict]]:
    """Map login -> [{number, title, merged_at}] for merged PRs, oldest first."""
    by_login: dict[str, list[dict]] = {}
    page = 1
    while page <= 5:
        data = api_get(
            f"{API}/repos/{owner}/{repo}/pulls?state=closed&sort=updated"
            f"&direction=desc&per_page=100&page={page}",
            token,
        )
        if not isinstance(data, list) or not data:
            break
        for pr in data:
            if not isinstance(pr, dict) or not pr.get("merged_at"):
                continue
            user = pr.get("user") or {}
            login = user.get("login")
            if not login or user.get("type") == "Bot":
                continue
            by_login.setdefault(login, []).append(
                {"number": pr.get("number"), "title": pr.get("title") or "", "merged_at": pr.get("merged_at") or ""}
            )
        if len(data) < 100:
            break
        page += 1
    for prs in by_login.values():
        prs.sort(key=lambda p: (p["merged_at"], p["number"] or 0))
    return by_login


def fetch_display_name(login: str, token: str | None) -> str:
    try:
        data = api_get(f"{API}/users/{login}", token)
    except Exception:
        return login
    if isinstance(data, dict) and data.get("name"):
        return str(data["name"]).strip() or login
    return login


def sanitize_title(title: str, limit: int = 80) -> str:
    text = re.sub(r"\s+", " ", title).strip().strip('"').strip()
    if not text:
        return ""
    lowered = text.lower()
    if any(phrase.lower() in lowered for phrase in PROHIBITED_PHRASES):
        return ""
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def credit_for(prs: list[dict]) -> str:
    parts = []
    for pr in prs:
        title = sanitize_title(pr.get("title") or "")
        if title:
            parts.append(f"#{pr['number']} “{title}”")
        else:
            parts.append(f"#{pr['number']}")
    refs = ", ".join(parts)
    return f"contributions via {refs}" if parts else "contributor"


def parse_readme_wall(text: str) -> tuple[list[str], list[str], dict[str, str], str, str]:
    """Return (logins, captions, display_names, prefix, suffix) around the wall table."""
    start = text.find("## Contributors\n")
    if start < 0:
        raise ValueError("README has no ## Contributors section")
    body_start = start + len("## Contributors\n")
    next_section = text.find("\n## ", body_start)
    if next_section < 0:
        raise ValueError("README Contributors section has no following section")
    body = text[body_start:next_section]
    matches = list(_AVATAR_RE.finditer(body))
    logins = [m.group(2) for m in matches]
    wall_names = {m.group(2): (m.group(1) or m.group(2)) for m in matches}
    rows = [line for line in body.splitlines() if line.startswith("|")]
    captions: list[str] = []
    if len(rows) >= 4:
        captions = [c.strip() for c in rows[3].strip().strip("|").split("|")]
    return logins, captions, wall_names, text[:body_start], text[next_section:]


def build_readme_wall(names: dict[str, str], captions: dict[str, str], order: list[str]) -> str:
    avatars = " | ".join(
        f"[![{names[l]}](https://github.com/{l}.png?size=100)](https://github.com/{l})" for l in order
    )
    names_row = " | ".join(f"[{names[l]}](https://github.com/{l})" for l in order)
    caps = " | ".join(captions.get(l, "contributor") for l in order)
    align = "|".join([":---:"] * len(order))
    return f"| {avatars} |\n|{align}|\n| {names_row} |\n| {caps} |\n"


def parse_contributors_md(text: str) -> list[tuple[str, str]]:
    """Return [(login, raw_line)] for contributor bullets in CONTRIBUTORS.md."""
    entries: list[tuple[str, str]] = []
    for line in text.splitlines():
        if line.startswith("- "):
            m = _BULLET_RE.match(line)
            if m:
                entries.append((m.group(2), line))
    return entries


def sync(
    readme_text: str,
    contributors_text: str,
    candidates: list[str],
    prs_by_login: dict[str, list[dict]],
    names: dict[str, str],
    owner: str,
) -> tuple[str, str, list[str]]:
    old_logins, old_captions, wall_names, prefix, suffix = parse_readme_wall(readme_text)
    old_entries = parse_contributors_md(contributors_text)
    old_md_logins = [login for login, _ in old_entries]

    known = list(dict.fromkeys(old_logins + old_md_logins))
    if owner in known:
        known.remove(owner)
    ordered = ([owner] if owner in (known + [owner]) else []) + known

    def sort_key(login: str) -> tuple[str, object]:
        prs = prs_by_login.get(login) or []
        first = prs[0]["merged_at"] if prs else "9999"
        return (first, login.lower())

    fresh = sorted([l for l in dict.fromkeys(candidates) if l not in ordered], key=sort_key)
    ordered = ordered + fresh

    # README wall: keep existing captions verbatim, caption newcomers by PR refs.
    caption_map = dict(zip(old_logins, old_captions))
    for login in fresh:
        nums = [str(p["number"]) for p in (prs_by_login.get(login) or [])[:3]]
        caption_map[login] = f"PR #{', #'.join(nums)}" if nums else "contributor"
    for login in ordered:
        names.setdefault(login, wall_names.get(login, login))
        caption_map.setdefault(login, "contributor" if login != owner else "maintainer")

    wall = build_readme_wall(names, caption_map, ordered)
    new_readme = f"{prefix}\n{wall}\n<br />\n{suffix}"

    # CONTRIBUTORS.md: keep existing bullets byte-identical, append newcomers.
    existing_lines = [line for _, line in old_entries]
    have = {login for login, _ in old_entries}
    appended: list[str] = []
    for login in ordered:
        if login in have:
            continue
        display = names.get(login, login)
        if login == owner and login not in have:
            appended.append(f"- {display} ([@{login}](https://github.com/{login})) — maintainer")
        else:
            appended.append(
                f"- {display} ([@{login}](https://github.com/{login})) — {credit_for(prs_by_login.get(login, []))}"
            )
    header_end = contributors_text.find("- ")
    if header_end < 0:
        raise ValueError("CONTRIBUTORS.md has no bullet list")
    header = contributors_text[:header_end].rstrip() + "\n\n"
    new_md = header + "\n".join(existing_lines + appended) + "\n"
    return new_readme, new_md, fresh


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--owner", default=os.environ.get("GITHUB_REPOSITORY_OWNER", ""))
    parser.add_argument("--repo", default="Gravitas")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--contributors-json", default="")
    parser.add_argument("--prs-json", default="")
    parser.add_argument("--names-json", default="")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    if not args.owner:
        print("error: --owner is required (or set GITHUB_REPOSITORY_OWNER)", file=sys.stderr)
        return 1

    if args.contributors_json:
        candidates = json.loads(Path(args.contributors_json).read_text(encoding="utf-8"))
        prs_by_login = json.loads(Path(args.prs_json).read_text(encoding="utf-8")) if args.prs_json else {}
        names = json.loads(Path(args.names_json).read_text(encoding="utf-8")) if args.names_json else {}
    else:
        try:
            candidates = fetch_contributors(args.owner, args.repo, args.token or None)
            prs_by_login = fetch_merged_prs(args.owner, args.repo, args.token or None)
        except Exception as exc:
            print(f"error: GitHub API failed: {exc}", file=sys.stderr)
            return 1
        names = {}

    # Resolve display names only for newcomers (one API call each, cached by file).
    try:
        old_logins, _, _, _, _ = parse_readme_wall(README_PATH.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not args.contributors_json:
        for login in candidates:
            if login not in old_logins and login not in names:
                names[login] = fetch_display_name(login, args.token or None)

    try:
        new_readme, new_md, fresh = sync(
            README_PATH.read_text(encoding="utf-8"),
            CONTRIBUTORS_PATH.read_text(encoding="utf-8"),
            candidates,
            prs_by_login,
            names,
            args.owner,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    changed = (
        new_readme != README_PATH.read_text(encoding="utf-8")
        or new_md != CONTRIBUTORS_PATH.read_text(encoding="utf-8")
    )
    if args.check:
        if changed:
            print(f"would add contributors: {', '.join(fresh) or '(format drift)'}")
            return 1
        print("contributors in sync")
        return 0
    if changed:
        README_PATH.write_text(new_readme, encoding="utf-8")
        CONTRIBUTORS_PATH.write_text(new_md, encoding="utf-8")
        print(f"added contributors: {', '.join(fresh) or '(format drift)'}")
    else:
        print("contributors in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
