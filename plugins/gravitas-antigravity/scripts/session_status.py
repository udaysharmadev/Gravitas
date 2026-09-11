#!/usr/bin/env python3
"""Gravitas session status reporter.

Shows current session state, evidence coverage, and pending criteria.

Usage: python session_status.py [--session-dir PATH]
"""
import json
import sys
from pathlib import Path


def find_session_dir() -> Path:
    gravitas_dir = Path('.gravitas/sessions')
    if not gravitas_dir.exists():
        return None
    sessions = sorted(
        [p for p in gravitas_dir.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    return sessions[0] if sessions else None


def load_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Show Gravitas session status')
    parser.add_argument('--session-dir', help='Explicit session directory path')
    args = parser.parse_args()

    session_dir = Path(args.session_dir) if args.session_dir else find_session_dir()
    if not session_dir:
        print('No active Gravitas session found.')
        sys.exit(0)

    # Load files
    state_path = session_dir / 'state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    contract_path = session_dir / 'contract.json'
    contract = json.loads(contract_path.read_text()) if contract_path.exists() else {}
    evidence = load_jsonl(session_dir / 'evidence.jsonl')
    failures = load_jsonl(session_dir / 'failures.jsonl')

    # Compute coverage
    all_criteria = contract.get('acceptance_criteria', [])
    passed = {e['criterion'] for e in evidence if e.get('verdict') == 'PASS'}
    pending = [c for c in all_criteria if c not in passed]

    print(f'Session: {session_dir.name}')
    print(f'Mode: {contract.get("mode", "unknown")}')
    print(f'Phase: {state.get("phase", "unknown")}')
    print(f'Budget: {contract.get("budget", "balanced")}')
    print()
    print(f'Acceptance Criteria: {len(passed)}/{len(all_criteria)} satisfied')
    for c in all_criteria:
        status = '✅' if c in passed else '⬜'
        print(f'  {status} {c}')
    print()
    if state.get('files_touched'):
        print(f'Files touched: {len(state["files_touched"])}')
        for f in state['files_touched']:
            print(f'  - {f}')
    if failures:
        print(f'\nKnown failures: {len(failures)}')
        for f in failures:
            print(f'  - {f.get("approach", f.get("tool", "unknown"))}: {f.get("reason", f.get("error", ""))[:80]}')
    print()
    if pending:
        print(f'Next action: {state.get("next_action", "Satisfy remaining criteria")}')
    else:
        print('All criteria satisfied. Ready for completion gate.')


if __name__ == '__main__':
    main()
