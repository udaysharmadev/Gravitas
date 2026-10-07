#!/usr/bin/env python3
"""Seeded randomization and experiment control for GravitasBench.

Implements a randomized complete-block design: every (task, run_index) pair is
one block containing all configurations exactly once, so model drift over time
affects each configuration pair equally.  Given the same seed the plan is
byte-identical across machines, which is what makes published runs
reproducible.  The block label is recorded in every episode's
``execution.randomized_block`` (schemas/episode.schema.json).
"""
import random


def build_run_plan(task_ids, configurations, runs_per_config, seed=0):
    """Return the seeded execution plan: a list of run dicts in run order.

    Each entry carries task_id, configuration, run_index (1-based) and
    randomized_block.  Deterministic for a given (inputs, seed) tuple.
    """
    task_ids = list(task_ids)
    configurations = list(configurations)
    if not task_ids or not configurations:
        raise ValueError("build_run_plan requires at least one task and one configuration")
    if len(set(task_ids)) != len(task_ids):
        raise ValueError("task_ids must be unique")
    if runs_per_config < 1:
        raise ValueError("runs_per_config must be at least 1")

    blocks = []
    for task_id in task_ids:
        for run_index in range(1, runs_per_config + 1):
            blocks.append((task_id, run_index))
    randomizer = random.Random(seed)
    randomizer.shuffle(blocks)

    plan = []
    for block_number, (task_id, run_index) in enumerate(blocks):
        order = list(configurations)
        randomizer.shuffle(order)
        block_label = f"block-{block_number:04d}"
        for configuration in order:
            plan.append({
                "task_id": task_id,
                "configuration": configuration,
                "run_index": run_index,
                "randomized_block": block_label,
            })
    return plan


def block_index_of(plan, task_id, run_index, configuration):
    """Look up the block label recorded for one planned run."""
    for entry in plan:
        if entry["task_id"] == task_id and entry["run_index"] == run_index and entry["configuration"] == configuration:
            return entry["randomized_block"]
    raise KeyError(f"no planned run for {task_id} run {run_index} configuration {configuration}")
