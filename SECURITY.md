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
