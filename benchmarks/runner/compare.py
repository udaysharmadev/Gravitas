#!/usr/bin/env python3
"""Compare paired GravitasBench configurations without external statistics packages."""
import argparse
import json
import math
import random
from pathlib import Path


def valid_pairs(episodes, baseline, treatment):
    indexed = {}
    for episode in episodes:
        if not episode.get("infrastructure_failure") and episode.get("configuration") in {baseline, treatment}:
            indexed.setdefault((episode["task_id"], episode.get("run_index", 1)), {})[episode["configuration"]] = episode
    return [pair for pair in indexed.values() if baseline in pair and treatment in pair]


def bootstrap_delta(pairs, samples=2000, seed=0):
    if not pairs:
        return None
    randomizer = random.Random(seed)
    deltas = []
    for _ in range(samples):
        sample = [randomizer.choice(pairs) for _ in pairs]
        deltas.append(sum(bool(pair["treatment"].get("functional_solve")) - bool(pair["baseline"].get("functional_solve")) for pair in sample) / len(sample))
    deltas.sort()
    return [round(deltas[int((samples - 1) * 0.025)], 4), round(deltas[int((samples - 1) * 0.975)], 4)]


def mcnemar_exact_p(baseline_only, treatment_only):
    n = baseline_only + treatment_only
    if not n:
        return 1.0
    tail = sum(math.comb(n, index) for index in range(0, min(baseline_only, treatment_only) + 1)) / (2 ** n)
    return min(1.0, round(2 * tail, 6))


def compare(episodes, baseline, treatment):
    pairs = valid_pairs(episodes, baseline, treatment)
    normalized = [{"baseline": pair[baseline], "treatment": pair[treatment]} for pair in pairs]
    baseline_only = sum(bool(pair["baseline"].get("functional_solve")) and not bool(pair["treatment"].get("functional_solve")) for pair in normalized)
    treatment_only = sum(bool(pair["treatment"].get("functional_solve")) and not bool(pair["baseline"].get("functional_solve")) for pair in normalized)
    baseline_rate = sum(bool(pair["baseline"].get("functional_solve")) for pair in normalized) / len(normalized) if normalized else None
    treatment_rate = sum(bool(pair["treatment"].get("functional_solve")) for pair in normalized) / len(normalized) if normalized else None
    return {
        "baseline": baseline, "treatment": treatment, "paired_episodes": len(normalized),
        "baseline_fsr": round(baseline_rate, 4) if baseline_rate is not None else None,
        "treatment_fsr": round(treatment_rate, 4) if treatment_rate is not None else None,
        "fsr_delta": round(treatment_rate - baseline_rate, 4) if baseline_rate is not None else None,
        "fsr_delta_bootstrap_ci95": bootstrap_delta(normalized),
        "mcnemar": {"baseline_only": baseline_only, "treatment_only": treatment_only, "two_sided_exact_p": mcnemar_exact_p(baseline_only, treatment_only)},
        "publication_ready": len(normalized) >= 30,
        "notes": "Synthetic or fewer-than-30 paired episodes are not publishable benchmark evidence.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--treatment", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    episodes = [json.loads(path.read_text()) for path in sorted(Path(args.episodes).glob("*.json"))]
    result = json.dumps(compare(episodes, args.baseline, args.treatment), indent=2)
    if args.output:
        Path(args.output).write_text(result + "\n")
    else:
        print(result)


if __name__ == "__main__":
    main()
