#!/usr/bin/env python3
"""Gravitas session initializer.

Creates a new .gravitas/sessions/<task-id>/ directory with:
- contract.json from the provided task contract
- state.json with initial state
- empty evidence.jsonl and failures.jsonl

Usage: python init_session.py --contract contract.json [--task-id my-task]
"""
import json
import argparse
import re
from datetime import datetime, timezone, date
from pathlib import Path
from session_context import conversation_key


def criterion_ids(contract: dict) -> list[str]:
    result = []
    for index, criterion in enumerate(contract.get("acceptance_criteria", []), 1):
        result.append(criterion.get("id") if isinstance(criterion, dict) else f"AC{index}")
    return result


def main():
    parser = argparse.ArgumentParser(description='Initialize a Gravitas session')
    parser.add_argument('--contract', help='Path to task contract JSON file')
    parser.add_argument('--task-id', help='Optional task ID (auto-generated if not provided)')
    parser.add_argument('--conversation-id', help='Antigravity conversation ID for isolated native-hook sessions')
    parser.add_argument('--contract-json', help='Task contract as inline JSON string')
    args = parser.parse_args()

    # Load contract
    contract = {}
    if args.contract:
        with open(args.contract) as f:
            contract = json.load(f)
    elif args.contract_json:
        contract = json.loads(args.contract_json)
    else:
        # Minimal default contract
        contract = {
            'mode': 'implement',
            'objective': 'Task objective not specified',
            'acceptance_criteria': [],
            'budget': 'balanced'
        }

    # Determine task ID
    task_id = args.task_id or contract.get('task_id')
    if not task_id:
        obj_slug = contract.get('objective', 'task')[:30].lower()
        obj_slug = ''.join(c if c.isalnum() else '-' for c in obj_slug).strip('-')
        task_id = f"{obj_slug}-{date.today().isoformat()}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", task_id) or task_id in {".", ".."}:
        parser.error("task ID must be 1-128 characters using letters, numbers, dot, underscore, or hyphen")

    # A host conversation wins over a caller-controlled task label. Store only its
    # digest-derived key on disk so logs do not retain the raw host identifier.
    session_key = conversation_key({'conversationId': args.conversation_id}) or task_id
    contract['session_key'] = session_key
    session_dir = Path('.gravitas') / 'sessions' / session_key
    session_dir.mkdir(parents=True, exist_ok=True)

    # Write contract.json
    with open(session_dir / 'contract.json', 'w') as f:
        json.dump(contract, f, indent=2)

    # Write initial state.json
    initial_state = {
        'task_id': task_id,
        'session_key': session_key,
        'contract': './contract.json',
        'phase': 'recon',
        'completed_criteria': [],
        'pending_criteria': criterion_ids(contract),
        'files_touched': [],
        'known_failures': [],
        'read_files': [],
        'background_tasks': [],
        'impact_graph': {},
        'last_successful_action': None,
        'next_action': 'Begin reconnaissance',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'last_updated': datetime.now(timezone.utc).isoformat()
    }
    with open(session_dir / 'state.json', 'w') as f:
        json.dump(initial_state, f, indent=2)

    # Create empty ledgers
    (session_dir / 'evidence.jsonl').touch()
    (session_dir / 'failures.jsonl').touch()
    with open(session_dir / 'coverage.json', 'w') as f:
        json.dump({criterion: 'PENDING' for criterion in criterion_ids(contract)}, f, indent=2)

    result = {
        'session_id': session_key,
        'session_dir': str(session_dir),
        'mode': contract.get('mode', 'implement'),
        'criteria_count': len(contract.get('acceptance_criteria', [])),
        'budget': contract.get('budget', 'balanced')
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
