"""Scalar rate limiting helpers for AFI safety tooling."""

from __future__ import annotations

import math

__all__ = ["rate_limit_scalar"]


def _sanitize_float(value: float, fallback: float = 0.0) -> float:
    """Return ``value`` if finite, otherwise ``fallback``."""
    if math.isfinite(value):
        return float(value)
    return float(fallback)


def rate_limit_scalar(value: float, prev: float, max_delta_pct: float) -> float:
    """Clamp ``value`` so it stays within a fractional band around ``prev``.

    Args:
        value: Proposed scalar value to clamp.
        prev: Previous accepted value.
        max_delta_pct: Maximum fractional change allowed (e.g. ``0.10`` for 10%).

    Returns:
        A finite float constrained to the allowed band. NaNs in the inputs cause
        the function to fall back to ``prev``.
    """
    prev_valid = math.isfinite(prev)
    max_delta = abs(_sanitize_float(max_delta_pct, 0.0))
    prev_sanitized = _sanitize_float(prev, 0.0)

    if not prev_valid:
        return prev_sanitized

    value_sanitized = _sanitize_float(value, prev_sanitized)

    if prev_sanitized == 0.0:
        lower = -max_delta
        upper = max_delta
    else:
        span_low = prev_sanitized * (1.0 - max_delta)
        span_high = prev_sanitized * (1.0 + max_delta)
        lower = min(span_low, span_high)
        upper = max(span_low, span_high)

    if value_sanitized < lower:
        return lower
    if value_sanitized > upper:
        return upper
    return value_sanitized
