# Security Policy

## Supported Versions

| Version | Supported |
|---------|----------|
| 4.x | Yes |
| 3.x | Security fixes only |
| < 3.0 | No |

## Reporting a Vulnerability

If you discover a security vulnerability in Gravitas:

1. **Do not open a public GitHub issue.**
2. Email the maintainer at the address on the GitHub profile.
3. Include: description, reproduction steps, potential impact, and any suggested fixes.
4. You will receive a response within 5 business days.

## Scope

Security-relevant issues include:
- The Antigravity hooks (pre_tool.py, post_tool.py, stop_gate.py) could be bypassed in unexpected ways
- The task contract or evidence ledger could be manipulated to produce false verification
- Session state files contain sensitive repository information that should not be committed

## .gravitas/ Is Not for Committing

The .gravitas/ directory contains runtime session state. It must be in .gitignore. Never commit .gravitas/ to a repository.

## What Gravitas Enforces (and What It Does Not)

Gravitas hooks are an advisory policy layer inside the host's tool flow.
They are **not a sandbox**. Treat every guarantee below as what the
runtime checks, not as containment.

**Enforced at hook level:**
- Read-only modes (`answer`, `research`, `plan`, `review`,
  `security-review`) deny file-edit tools and all shell execution above
  read-only queries, based on tokenizer classification (fail-closed).
- Writes outside `allowed_write_scope` are denied, including enumerable
  shell writes (redirect targets, `tee`/`dd` operands).
- Symlink/traversal escapes from the declared scope are denied after
  symlink resolution.
- Destructive operations (`rm`, `git reset/clean`, infra CLIs, network
  fetch piped to execution) require explicit host-side confirmation.
- Owned validator/reproducer execution (`--cwd`) cannot escape the
  invoking workspace directory.
- Secrets in tool output are redacted before ledger persistence; reads of
  likely secret-bearing files are flagged (`sensitive: true`).

**Explicitly NOT guaranteed:**
- Complete shell containment. Interpreters, package scripts, editor
  subprocesses, and build plugins execute with the user's privileges;
  classification governs the *request*, not the process.
- TOCTOU safety. A path checked safe can be swapped before execution.
  Hooks narrow the window; they do not close it.
- Plan-only non-mutation against a hostile or compromised host tool.
  If the host executes outside the hook flow, Gravitas cannot see it.
- Secret safety of files the agent legitimately reads (`.env` contents
  still enter model context; only ledger persistence is redacted/flagged).
- Ledger tamper-proofing. The hash chain is tamper-*evident*
  (`gravitas verify` detects edits); anyone with filesystem access can
  rewrite history and the rewrite will show.

## Threat Model (tested)

See `tests/test_action_security.py`: bypass corpus (substitution,
pipes, redirection, `sed -i`, `tee`, `curl|sh`, `find -exec`, infra
CLIs), monotonic-escalation fuzzing (2,500 seeded cases), scope escape
(symlink/traversal), runner confinement, and sensitive-read flagging.
