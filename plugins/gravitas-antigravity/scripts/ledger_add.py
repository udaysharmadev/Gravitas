#!/usr/bin/env python3
"""Gravitas evidence ledger appender.

Adds an evidence entry to the current session's evidence.jsonl.

Usage: python ledger_add.py --criterion "AC1" --evidence "vitest: 47 passed" --source test_run --verdict PASS
"""
import json
import sys
import argparse
from pathlib import Path
from evidence_chain import append_evidence


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


def main():
    parser = argparse.ArgumentParser(description='Add evidence to Gravitas ledger')
    parser.add_argument('--criterion', required=True, help='Acceptance criterion this evidence satisfies')
    parser.add_argument('--evidence', required=True, help='The observed evidence (cite command output)')
    parser.add_argument('--source', default='test_run',
                        choices=['test_run', 'lint', 'type_check', 'build', 'diff', 'static_analysis', 'validator', 'self_review'],
                        help='Evidence source type')
    parser.add_argument('--verdict', default='PASS',
                        choices=['PASS', 'FAIL', 'CONDITIONAL_PASS', 'PENDING'],
                        help='Verdict for this criterion')
    parser.add_argument('--session-dir', help='Explicit session directory path')
    args = parser.parse_args()

    session_dir = Path(args.session_dir) if args.session_dir else find_session_dir()
    if not session_dir:
        print('ERROR: No Gravitas session found. Run init_session.py first.', file=sys.stderr)
        sys.exit(1)

    entry = {
        'criterion': args.criterion,
        'evidence': args.evidence,
        'source': args.source,
        'verdict': args.verdict,
    }
    append_evidence(session_dir, entry)

    print(f'Added evidence for {args.criterion}: {args.verdict}')
    print(f'Session: {session_dir}')


if __name__ == '__main__':
    main()
