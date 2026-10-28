#!/usr/bin/env python3
"""Trigger evaluation: measure skill activation rate from predictions.

Input predictions JSONL: {"input": "...", "predicted": true/false}
Ground truth: eval/trigger-eval.json (intended true, non-activations false).

Outputs activation rate (intended), false-positive rate (non-activations),
and near-miss false-positive rate separately.

Usage:
  python benchmarks/runner/trigger_eval.py --predictions /tmp/preds.jsonl
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_ground_truth():
    data = json.loads((ROOT / "eval/trigger-eval.json").read_text())
    truth = {}
    for item in data.get("intended_activations", []):
        truth[item["input"]] = True
    for item in data.get("non_activations", []):
        truth[item["input"]] = False
    near_miss_markers = ("regex", "summarize", "stack trace", "do not change",
                         "difference between", "configure my editor")
    near_miss = {inp for inp in truth if not truth[inp] and
                 any(m in inp.lower() for m in near_miss_markers)}
    return truth, near_miss


def evaluate(predictions: dict) -> dict:
    truth, near_miss = load_ground_truth()
    intended = [inp for inp, exp in truth.items() if exp]
    non = [inp for inp, exp in truth.items() if not exp]
    near = [inp for inp in non if inp in near_miss]
    def rate(inputs):
        scored = [predictions[inp] for inp in inputs if inp in predictions]
        if not scored:
            return {"n": 0, "rate": None}
        return {"n": len(scored), "rate": round(sum(1 for v in scored if v) / len(scored), 4)}
    act = rate(intended)
    fpr = {"n": 0, "rate": None}
    non_scored = [predictions[inp] for inp in non if inp in predictions]
    if non_scored:
        fpr = {"n": len(non_scored),
               "rate": round(sum(1 for v in non_scored if v) / len(non_scored), 4)}
    near_scored = [predictions[inp] for inp in near if inp in predictions]
    near_fpr = {"n": len(near_scored),
                "rate": round(sum(1 for v in near_scored if v) / len(near_scored), 4)} if near_scored else {"n": 0, "rate": None}
    passed = ((act["rate"] is not None and act["rate"] >= 0.95) and
              (fpr["rate"] is not None and fpr["rate"] <= 0.05))
    return {"activation_rate": act, "false_positive_rate": fpr,
            "near_miss_fpr": near_fpr, "passed": bool(passed)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True)
    args = parser.parse_args()
    predictions = {}
    for line in Path(args.predictions).read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            predictions[row["input"]] = bool(row["predicted"])
    print(json.dumps(evaluate(predictions), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
