"""Descriptive statistics helpers."""

import math
from collections import Counter
from typing import Sequence


def mean(values: Sequence[float]) -> float:
    """Arithmetic mean of a non-empty sequence."""
    if not values:
        raise ValueError("mean requires at least one value")
    return sum(values) / len(values)


def median(values: Sequence[float]) -> float:
    """Median (middle value) of a non-empty sequence."""
    if not values:
        raise ValueError("median requires at least one value")
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return float(sorted_vals[mid])
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0


def mode(values: Sequence[float]) -> float:
    """Most common value. Returns the smallest if there is a tie."""
    if not values:
        raise ValueError("mode requires at least one value")
    counts = Counter(values)
    max_count = max(counts.values())
    candidates = [v for v, c in counts.items() if c == max_count]
    return min(candidates)


def std_dev(values: Sequence[float]) -> float:
    """Population standard deviation."""
    if not values:
        raise ValueError("std_dev requires at least one value")
    m = mean(values)
    variance = sum((x - m) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def summarize(values: Sequence[float]) -> dict:
    """Return a dict with mean, median, mode, std_dev, min, max, count."""
    if not values:
        raise ValueError("summarize requires at least one value")
    return {
        "count":   len(values),
        "min":     min(values),
        "max":     max(values),
        "mean":    mean(values),
        "median":  median(values),
        "mode":    mode(values),
        "std_dev": std_dev(values),
    }
