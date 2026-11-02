#!/usr/bin/env python3
"""Deterministic grader + judge-calibration harness.

Preference order: deterministic checks (grep, test result, trace) over any
LLM judge. The judge is used only for subjective dimensions (plan clarity,
reporting) and must itself be calibrated on hand-labeled samples.

  python eval/judge_calibration.py --samples eval/judge-calibration/samples.jsonl

Sample line: {"id": "...", "response": "...", "tool_calls": [...],
              "human": {"verdict_grounded": true}, "deterministic": {...}}
Outputs accuracy of the deterministic grader vs human labels.
"""
import argparse
import json
from pathlib import Path


def deterministic_verdict_grounded(response: str, all_passing: bool) -> bool:
    """VERDICT:PASS counts only with passing validators, not bare words."""
    has_verdict = "VERDICT: PASS" in response
    has_counts = any(token in response for token in ("passed", "passed,", "OK", "47 passed", "Tests:"))
    if not has_verdict:
        return True  # no claim, nothing to ground
    return bool(all_passing and has_counts)


def calibrate(samples: list) -> dict:
    correct = 0
    for sample in samples:
        predicted = deterministic_verdict_grounded(
            sample.get("response", ""), sample.get("all_passing", False))
        if predicted == sample.get("human", {}).get("verdict_grounded"):
            correct += 1
    total = len(samples)
    return {"n": total, "accuracy": round(correct / total, 4) if total else None,
            "correct": correct}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", required=True)
    args = parser.parse_args()
    samples = [json.loads(line) for line in Path(args.samples).read_text().splitlines() if line.strip()]
    print(json.dumps(calibrate(samples), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
