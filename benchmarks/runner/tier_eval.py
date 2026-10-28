#!/usr/bin/env python3
"""Tier-classification eval: score planning-level predictions.

Ground truth: eval/tier-eval.json (direct/compact/deep per case).
Input predictions JSONL: {"id": "T-01", "predicted": "deep"}

Reports overall accuracy plus per-level accuracy and the two load-bearing
slices: single-file auth/security cases (must be deep) and
uncertain/ambiguous cases (must be deep).

Usage:
  python benchmarks/runner/tier_eval.py --predictions /tmp/tier-preds.jsonl
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_cases():
    return json.loads((ROOT / "eval/tier-eval.json").read_text())["cases"]


def evaluate(predictions: dict) -> dict:
    cases = load_cases()
    scored = [(c, predictions[c["id"]]) for c in cases if c["id"] in predictions]
    total = len(scored)
    correct = sum(1 for c, p in scored if p == c["expect"])
    by_level: dict = {}
    for level in ("direct", "compact", "deep"):
        subset = [(c, p) for c, p in scored if c["expect"] == level]
        hits = sum(1 for c, p in subset if p == level)
        by_level[level] = {"n": len(subset),
                           "accuracy": round(hits / len(subset), 4) if subset else None}
    def norm(text):
        return text.lower().replace("-", " ")
    auth_singles = [(c, p) for c, p in scored
                    if "single file" in norm(c["task"]) and c["expect"] == "deep"]
    uncertain = [(c, p) for c, p in scored
                 if ("uncertain" in c["task"].lower() or "ambiguous" in c["task"].lower())]
    def acc(pairs):
        if not pairs:
            return {"n": 0, "accuracy": None}
        hits = sum(1 for c, p in pairs if p == c["expect"])
        return {"n": len(pairs), "accuracy": round(hits / len(pairs), 4)}
    overall = round(correct / total, 4) if total else None
    return {"n": total, "accuracy": overall, "by_level": by_level,
            "single_file_auth_deep": acc(auth_singles),
            "uncertain_deep": acc(uncertain),
            "passed": bool(total and overall is not None and overall >= 0.85
                           and (acc(auth_singles)["accuracy"] or 0) >= 1.0
                           and (acc(uncertain)["accuracy"] or 0) >= 1.0)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True)
    args = parser.parse_args()
    predictions = {}
    for line in Path(args.predictions).read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            predictions[row["id"]] = row["predicted"]
    print(json.dumps(evaluate(predictions), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
