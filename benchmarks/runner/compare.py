#!/usr/bin/env python3
"""Compare paired GravitasBench configurations without external statistics packages."""
import argparse
import json
import math
import random
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit


MIN_PUBLICATION_TASKS = 30
MIN_RUNS_PER_TASK = 5


def _index_episodes(episodes, baseline, treatment):
    if not all(isinstance(value, str) and value.strip() for value in (baseline, treatment)) or baseline == treatment:
        raise ValueError("baseline and treatment must be distinct non-empty configuration names")
    indexed = {}
    for episode in episodes:
        if not isinstance(episode, dict) or episode.get("configuration") not in (baseline, treatment):
            continue
        task_id = episode.get("task_id")
        run_index = episode.get("run_index", 1)
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("paired episodes require a non-empty task_id")
        if isinstance(run_index, bool) or not isinstance(run_index, int) or run_index < 1:
            raise ValueError("run_index must be a positive integer")
        pair = indexed.setdefault((task_id, run_index), {})
        configuration = episode["configuration"]
        if configuration in pair:
            raise ValueError(f"duplicate episode identity: {task_id}/{run_index}/{configuration}")
        pair[configuration] = episode
    return indexed


def valid_pairs(episodes, baseline, treatment):
    indexed = _index_episodes(episodes, baseline, treatment)
    return [pair for pair in indexed.values() if baseline in pair and treatment in pair
            and not pair[baseline].get("infrastructure_failure")
            and not pair[treatment].get("infrastructure_failure")]


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _hex_digest(value, lengths=(64,)):
    return isinstance(value, str) and len(value) in lengths and re.fullmatch(r"[0-9a-fA-F]+", value) is not None


def _provenance(episode):
    value = episode.get("provenance")
    return value if isinstance(value, dict) else {}


def _episode_publication_blockers(episode):
    try:
        from validate import episode_errors
    except ImportError:  # pragma: no cover - package import
        from benchmarks.runner.validate import episode_errors
    blockers = set()
    if episode_errors(episode, {}):
        blockers.add("episodes must pass schema-independent outcome validation")
    kind = episode.get("evidence_kind", "unspecified")
    if kind != "repository":
        blockers.add(f"repository evidence required; found {kind} evidence")
    if "run_index" not in episode:
        blockers.add("every episode must declare its run_index")
    for field in ("model", "effort"):
        if not _nonempty(episode.get(field)):
            blockers.add(f"every episode must declare {field}")
    if not _hex_digest(episode.get("repo_commit"), (40, 64)):
        blockers.add("repo_commit must be a full Git commit hash")
    if not _hex_digest(episode.get("hidden_validator_hash")):
        blockers.add("hidden_validator_hash must be a SHA-256 digest")
    provenance = _provenance(episode)
    if not provenance:
        blockers.add("every episode requires explicit provenance")
    repository_url = provenance.get("repository_url")
    try:
        parsed_url = urlsplit(repository_url) if _nonempty(repository_url) else None
    except ValueError:
        parsed_url = None
    if parsed_url is None or parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        blockers.add("provenance.repository_url must be an HTTP(S) repository URL")
    if not _nonempty(provenance.get("repository_license")):
        blockers.add("provenance.repository_license must be declared")
    for field in ("model_revision", "host_revision"):
        revision = provenance.get(field)
        if not _nonempty(revision) or revision.strip().lower() in {"latest", "head", "main", "master", "unknown", "unspecified"}:
            blockers.add(f"provenance.{field} must be an explicit revision")
    for field in ("dataset_version", "harness_revision", "evaluator_revision"):
        if not _hex_digest(provenance.get(field), (40, 64)):
            blockers.add(f"provenance.{field} must be a full Git commit hash")
    for field in ("fixture_hash", "prompt_hash", "configuration_hash"):
        if not _hex_digest(provenance.get(field)):
            blockers.add(f"provenance.{field} must be a SHA-256 digest")
    return blockers


def publication_evidence(episodes, baseline, treatment, pairs):
    """Check declared experiment structure, not the authenticity of supplied artifacts."""
    indexed = _index_episodes(episodes, baseline, treatment)
    counts = Counter(pair[baseline]["task_id"] for pair in pairs)
    minimum = min(counts.values(), default=0)
    blockers = set()
    if len(counts) < MIN_PUBLICATION_TASKS:
        blockers.add(f"at least {MIN_PUBLICATION_TASKS} distinct paired tasks are required")
    if minimum < MIN_RUNS_PER_TASK:
        blockers.add(f"at least {MIN_RUNS_PER_TASK} valid paired runs per task are required")
    shared_fields = ("model", "effort", "repo_commit", "hidden_validator_hash")
    shared_provenance = ("repository_url", "repository_license", "dataset_version", "fixture_hash",
                         "prompt_hash", "model_revision", "host_revision", "evaluator_revision")
    configuration_fields = ("dataset_version", "model_revision", "host_revision", "harness_revision",
                            "configuration_hash", "evaluator_revision")
    configuration_identities = {}
    task_identities = {}
    for pair in indexed.values():
        for episode in pair.values():
            blockers.update(_episode_publication_blockers(episode))
        if baseline not in pair or treatment not in pair:
            if any(not episode.get("infrastructure_failure") for episode in pair.values()):
                blockers.add("valid episodes must have a matching baseline and treatment run")
            continue
        if any(episode.get("infrastructure_failure") for episode in pair.values()):
            continue
        left, right = pair[baseline], pair[treatment]
        left_provenance, right_provenance = _provenance(left), _provenance(right)
        for field in shared_fields:
            if left.get(field) != right.get(field):
                blockers.add(f"matched pairs must use the same {field}")
        for field in shared_provenance:
            if left_provenance.get(field) != right_provenance.get(field):
                blockers.add(f"matched pairs must use the same provenance.{field}")
        for configuration, episode in pair.items():
            provenance = _provenance(episode)
            configuration_identity = [episode.get("model"), episode.get("effort")]
            configuration_identity += [provenance.get(field) for field in configuration_fields]
            prior = configuration_identities.setdefault(configuration, configuration_identity)
            if prior != configuration_identity:
                blockers.add(f"configuration {configuration} mixes experiment revisions")
            task_identity = [episode.get("repo_commit"), episode.get("hidden_validator_hash")]
            task_identity += [provenance.get(field) for field in
                              ("repository_url", "repository_license", "fixture_hash", "prompt_hash")]
            prior = task_identities.setdefault(episode["task_id"], task_identity)
            if prior != task_identity:
                blockers.add("repeated task runs must use the same repository, fixture, prompt, and validator")
    return {
        "paired_tasks": len(counts),
        "min_pairs_per_task": minimum,
        "publication_blockers": sorted(blockers),
        "publication_ready": not blockers,
    }


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
    episodes = list(episodes)
    pairs = valid_pairs(episodes, baseline, treatment)
    eligibility = publication_evidence(episodes, baseline, treatment, pairs)
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
        **eligibility,
        "notes": "Publication requires declared repository provenance and at least 30 tasks with 5 valid paired runs each. This structural gate does not authenticate artifacts or establish model superiority.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--treatment", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    episodes = []
    for path in sorted(Path(args.episodes).glob("*.json")):
        payload = json.loads(path.read_text())
        if isinstance(payload, list):
            continue
        episodes.append(payload)
    result = json.dumps(compare(episodes, args.baseline, args.treatment), indent=2)
    if args.output:
        Path(args.output).write_text(result + "\n")
    else:
        print(result)


if __name__ == "__main__":
    main()
