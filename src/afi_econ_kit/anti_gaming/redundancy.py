"""Anti-gaming helpers that penalise redundant signals."""

from __future__ import annotations

import math
from typing import List, Sequence

__all__ = ["redundancy_multiplier", "apply_redundancy_penalties"]


def _clamp(value: float, lower: float, upper: float) -> float:
    if value < lower:
        return lower
    if value > upper:
        return upper
    return value


def redundancy_multiplier(
    corr: float,
    thresh: float = 0.80,
    steepness: float = 8.0,
    min_multiplier: float = 0.25,
) -> float:
    """Return a redundancy penalty multiplier in ``[min_multiplier, 1.0]``.

    A logistic ramp is triggered only once ``corr`` exceeds ``thresh``. The
    multiplier falls smoothly towards ``min_multiplier`` as correlations approach
    one, creating a monotone non-increasing penalty schedule.
    """

    corr_clamped = _clamp(float(corr), 0.0, 1.0)
    min_mult = _clamp(float(min_multiplier), 0.0, 1.0)
    steep = abs(float(steepness))
    threshold = _clamp(float(thresh), 0.0, 1.0)

    x = max(0.0, corr_clamped - threshold)
    if x <= 0.0:
        return 1.0

    sigmoid = 1.0 / (1.0 + math.exp(-steep * x))
    normalized = _clamp(2.0 * (sigmoid - 0.5), 0.0, 1.0)
    multiplier = 1.0 - (1.0 - min_mult) * normalized
    return _clamp(multiplier, min_mult, 1.0)


def apply_redundancy_penalties(
    credits: Sequence[float],
    corr_matrix: Sequence[Sequence[float]],
    thresh: float = 0.80,
    steepness: float = 8.0,
    min_multiplier: float = 0.25,
) -> List[float]:
    """Apply redundancy penalties using the maximum off-diagonal correlation.

    Each credit receives the worst-case correlation from its row (ignoring the
    diagonal) and is scaled by :func:`redundancy_multiplier`. The input data are
    never mutated and NaNs are treated as zero correlation to avoid accidental
    over-penalisation.
    """

    n = len(credits)
    penalised: List[float] = []

    for i in range(n):
        row = corr_matrix[i] if i < len(corr_matrix) else []
        effective_corr = 0.0
        for j, entry in enumerate(row):
            if j == i:
                continue
            if not math.isfinite(entry):
                continue
            if entry > effective_corr:
                effective_corr = entry
        multiplier = redundancy_multiplier(
            effective_corr,
            thresh=thresh,
            steepness=steepness,
            min_multiplier=min_multiplier,
        )
        penalised.append(float(credits[i]) * multiplier)

    return penalised
