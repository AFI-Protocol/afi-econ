"""Unit tests for lightweight safety helpers."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from random import Random

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from afi_econ_kit.safety.rate_limits import rate_limit_scalar
from afi_econ_kit.safety.smoothing import exponential_smoothing


def test_exponential_smoothing_union_and_bounds() -> None:
    current = {"a": 1.2, "b": -0.1}
    prev = {"b": 0.8, "c": 0.5}

    result = exponential_smoothing(current, prev, 0.5)

    assert set(result) == {"a", "b", "c"}
    assert result["a"] == pytest.approx(1.0)
    assert result["b"] == pytest.approx(0.35)
    assert result["c"] == pytest.approx(0.5)


def test_exponential_smoothing_alpha_extremes() -> None:
    rng = Random(42)
    current = {f"k{i}": rng.random() for i in range(5)}
    prev = {f"k{i}": rng.random() for i in range(5)}

    result_one = exponential_smoothing(current, prev, 1.5)
    result_zero = exponential_smoothing(current, prev, -0.7)

    for key in current:
        assert result_one[key] == pytest.approx(current[key])
        assert result_zero[key] == pytest.approx(prev[key])


def test_exponential_smoothing_floor() -> None:
    result = exponential_smoothing({"x": 0.0}, {"x": 0.0}, 0.3)

    assert result["x"] == pytest.approx(1e-12)


def test_rate_limit_scalar_within_and_clamped() -> None:
    assert rate_limit_scalar(105.0, 100.0, 0.10) == pytest.approx(105.0)
    assert rate_limit_scalar(130.0, 100.0, 0.10) == pytest.approx(110.0)
    assert rate_limit_scalar(60.0, 100.0, 0.10) == pytest.approx(90.0)


def test_rate_limit_scalar_prev_zero() -> None:
    assert rate_limit_scalar(0.5, 0.0, 0.10) == pytest.approx(0.10)
    assert rate_limit_scalar(-0.5, 0.0, 0.10) == pytest.approx(-0.10)


def test_rate_limit_scalar_nan_inputs() -> None:
    prev = 2.5
    assert rate_limit_scalar(math.nan, prev, 0.20) == pytest.approx(prev)
    assert rate_limit_scalar(10.0, math.nan, 0.20) == pytest.approx(0.0)


def test_rate_limit_scalar_respects_band() -> None:
    rng = Random(7)
    for _ in range(200):
        prev = rng.uniform(-10.0, 10.0)
        value = rng.uniform(-25.0, 25.0)
        max_delta_pct = rng.uniform(0.0, 0.9)
        limited = rate_limit_scalar(value, prev, max_delta_pct)

        if prev == 0.0:
            lower, upper = -max_delta_pct, max_delta_pct
        else:
            low_candidate = prev * (1.0 - max_delta_pct)
            high_candidate = prev * (1.0 + max_delta_pct)
            lower = min(low_candidate, high_candidate)
            upper = max(low_candidate, high_candidate)

        assert lower - 1e-12 <= limited <= upper + 1e-12


def test_rate_limit_scalar_band_expands_with_pct() -> None:
    rng = Random(99)
    for _ in range(200):
        prev = rng.uniform(-5.0, 5.0)
        value = rng.uniform(-10.0, 10.0)
        small = rng.uniform(0.0, 0.5)
        large = small + rng.uniform(0.0, 0.5)

        limited_small = rate_limit_scalar(value, prev, small)
        limited_large = rate_limit_scalar(value, prev, large)

        assert abs(limited_large - prev) + 1e-12 >= abs(limited_small - prev)
