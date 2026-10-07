#!/usr/bin/env python3
"""Deterministic statistics helpers for GravitasBench.

Pure standard library: no external statistics packages are required.  The
Mann-Whitney U test uses the normal approximation with tie and continuity
corrections, which is the standard large-sample form; for very small samples
exact tables would be more precise, and any published claim must state which
implementation produced its p-values (see docs/eval-methodology.md).
"""
import math


def mann_whitney_u(xs, ys):
    """Return (U1, two_sided_p) for samples xs and ys.

    U1 counts xy pairs where x > y (ties count 0.5).  The two-sided p-value
    uses the normal approximation with tie correction and continuity
    correction.  Returns (None, None) when either sample is empty.
    """
    xs = [value for value in xs if value is not None]
    ys = [value for value in ys if value is not None]
    n1, n2 = len(xs), len(ys)
    if not n1 or not n2:
        return None, None
    combined = [(value, 0) for value in xs] + [(value, 1) for value in ys]
    combined.sort(key=lambda item: item[0])
    ranks = [0.0] * len(combined)
    index = 0
    while index < len(combined):
        end = index
        while end + 1 < len(combined) and combined[end + 1][0] == combined[index][0]:
            end += 1
        average_rank = (index + end) / 2 + 1
        for position in range(index, end + 1):
            ranks[position] = average_rank
        index = end + 1
    rank_sum_x = sum(rank for rank, (value, side) in zip(ranks, combined) if side == 0)
    u1 = rank_sum_x - n1 * (n1 + 1) / 2
    u2 = n1 * n2 - u1
    mu = n1 * n2 / 2
    tie_term = sum(
        count ** 3 - count for count in _tie_counts(combined)
    )
    variance = (n1 * n2 / 12) * ((n1 + n2 + 1) - tie_term / ((n1 + n2) * (n1 + n2 - 1)))
    if variance <= 0:
        return u1, 1.0
    z = (max(u1, u2) - mu - 0.5) / math.sqrt(variance)
    p = min(1.0, 2.0 * (1.0 - _normal_cdf(z)))
    return u1, round(p, 6)


def _tie_counts(combined):
    counts = []
    index = 0
    while index < len(combined):
        end = index
        while end + 1 < len(combined) and combined[end + 1][0] == combined[index][0]:
            end += 1
        counts.append(end - index + 1)
        index = end + 1
    return [count for count in counts if count > 1]


def _normal_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def percentile(values, q):
    """Linear-interpolation percentile of non-None values, or None."""
    data = sorted(value for value in values if value is not None)
    if not data:
        return None
    if len(data) == 1:
        return data[0]
    position = (len(data) - 1) * q / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return data[lower]
    return data[lower] + (data[upper] - data[lower]) * (position - lower)


def cohens_d(xs, ys):
    """Pooled-standard-deviation Cohen's d (positive means xs larger)."""
    xs = [value for value in xs if value is not None]
    ys = [value for value in ys if value is not None]
    if len(xs) < 2 or len(ys) < 2:
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    var_x = sum((value - mean_x) ** 2 for value in xs) / (len(xs) - 1)
    var_y = sum((value - mean_y) ** 2 for value in ys) / (len(ys) - 1)
    pooled = math.sqrt(((len(xs) - 1) * var_x + (len(ys) - 1) * var_y) / (len(xs) + len(ys) - 2))
    if pooled == 0:
        return 0.0
    return round((mean_x - mean_y) / pooled, 4)


def bonferroni(alpha, k):
    """Per-test alpha for a family of k tests at family-wise error rate alpha."""
    if k <= 0:
        return None
    return alpha / k


def median_ratio(numerators, denominators):
    """median(numerators) / median(denominators) ignoring None entries."""
    medians = []
    for values in (numerators, denominators):
        data = [value for value in values if value is not None]
        if not data:
            return None
        medians.append(_median(data))
    if medians[1] == 0:
        return None
    return round(medians[0] / medians[1], 4)


def _median(data):
    ordered = sorted(data)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2
