#!/usr/bin/env python3
"""Simulated Tier-2 approver for automated benchmark harnesses.

Real Tier-2 work requires a human checkpoint (PROMPT-TEMPLATE.md). Automated
harnesses would block forever, so this module provides a deterministic,
policy-driven stand-in. It is NOT a human approval; episodes using it are
marked `simulated_approval: true` and must disclose that in reports.

Policy (deny-safe):
- DENY destructive actions without a backup/rollback note: drop table,
  delete production data, rotate keys without dual-write, allow-all CORS.
- DENY auth/security changes with no test plan.
- APPROVE everything else, with the reason recorded.

Usage:
  from simulated_approver import decide
  decision = decide(task_id="SC-001", summary="parameterize queries", test_plan="run hidden acceptance")
"""
from dataclasses import dataclass


@dataclass
class Decision:
    approved: bool
    reason: str
    simulated: bool = True


DESTRUCTIVE_MARKERS = (
    "drop table", "drop database", "delete production",
    "rm -rf", "allow-all cors", "allow * origin",
    "disable auth", "skip auth",
)

AUTH_MARKERS = ("auth", "password", "jwt", "session", "oauth", "sql injection", "permission")


def decide(task_id: str, summary: str, test_plan: str = "") -> Decision:
    text = f"{summary}\n{test_plan}".lower()
    for marker in DESTRUCTIVE_MARKERS:
        if marker in text:
            if "backup" in text or "rollback" in text or "dual-write" in text:
                return Decision(True, f"approved: destructive marker '{marker}' has backup/rollback note", True)
            return Decision(False, f"denied: destructive marker '{marker}' without backup/rollback", True)
    if any(marker in text for marker in AUTH_MARKERS) and not test_plan.strip():
        return Decision(False, "denied: auth/security change with no test plan", True)
    return Decision(True, "approved: no destructive marker, test plan present or non-auth change", True)
