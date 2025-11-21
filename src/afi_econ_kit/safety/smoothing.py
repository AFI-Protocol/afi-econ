"""Lightweight smoothing helpers for the AFI economic safety toolkit.

These helpers intentionally avoid external dependencies so they can be reused
in lightweight validation paths without importing the heavier safety module.
"""

from __future__ import annotations

from typing import Dict, Mapping

_EPSILON = 1e-12


def _clamp(value: float, lower: float, upper: float) -> float:
    """Clamp ``value`` to the closed interval ``[lower, upper]``."""
    if value < lower:
        return lower
    if value > upper:
        return upper
    return value


def exponential_smoothing(
    current: Mapping[str, float],
    prev: Mapping[str, float],
    alpha: float,
) -> Dict[str, float]:
    """Blend current and previous metrics with exponential smoothing.

    The smoothing factor ``alpha`` is clamped into ``[0.0, 1.0]`` before
    applying ``s[k] = alpha * current[k] + (1 - alpha) * prev.get(k, current[k])``
    for every key present in either mapping. Values are clipped to ``[0.0, 1.0]``
    to keep downstream math bounded. If the entire result would be effectively
    zero, a uniform ``1e-12`` floor is returned instead so follow-on logic never
    sees a truly all-zero vector.
    """

    if not current and not prev:
        return {}

    alpha_clamped = _clamp(float(alpha), 0.0, 1.0)
    keys = set(current.keys()) | set(prev.keys())
    smoothed: Dict[str, float] = {}

    for key in keys:
        if key in current:
            curr_val = float(current[key])
        else:
            curr_val = float(prev.get(key, 0.0))
        prev_val = float(prev.get(key, curr_val))
        smoothed_value = alpha_clamped * curr_val + (1.0 - alpha_clamped) * prev_val
        smoothed[key] = _clamp(smoothed_value, 0.0, 1.0)

    if smoothed and all(value <= _EPSILON for value in smoothed.values()):
        return {key: _EPSILON for key in smoothed}

    return smoothed
