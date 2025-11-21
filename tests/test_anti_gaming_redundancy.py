"""Tests for anti-gaming redundancy helpers."""

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

from afi_econ_kit.anti_gaming.redundancy import (
    apply_redundancy_penalties,
    redundancy_multiplier,
)


def test_redundancy_multiplier_threshold_behaviour() -> None:
    assert redundancy_multiplier(0.50, thresh=0.80) == pytest.approx(1.0)
    assert redundancy_multiplier(0.80, thresh=0.80) == pytest.approx(1.0)
    high_corr = redundancy_multiplier(0.95, thresh=0.80, steepness=8.0, min_multiplier=0.25)
    assert 0.25 <= high_corr < 1.0


def test_redundancy_multiplier_minimum_floor() -> None:
    result = redundancy_multiplier(1.0, thresh=0.60, min_multiplier=0.4)
    assert result >= 0.4
    assert result <= 1.0


def test_redundancy_multiplier_steepness_effect() -> None:
    gentle = redundancy_multiplier(0.9, steepness=1.0)
    sharp = redundancy_multiplier(0.9, steepness=10.0)
    assert sharp <= gentle


def test_apply_redundancy_identity_matrix() -> None:
    credits = [1.0, 2.0, 3.0]
    corr_matrix = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]
    assert apply_redundancy_penalties(credits, corr_matrix) == pytest.approx(credits)


def test_apply_redundancy_uniform_high_corr() -> None:
    credits = [1.0, 1.0, 1.0]
    corr_matrix = [
        [1.0, 0.95, 0.95],
        [0.95, 1.0, 0.95],
        [0.95, 0.95, 1.0],
    ]
    expected_multiplier = redundancy_multiplier(0.95, min_multiplier=0.3)
    penalised = apply_redundancy_penalties(credits, corr_matrix, min_multiplier=0.3)
    for value in penalised:
        assert value == pytest.approx(expected_multiplier)
        assert 0.3 <= value <= 1.0


def test_apply_redundancy_ignores_nan_entries() -> None:
    credits = [1.0, 1.0]
    corr_matrix = [
        [1.0, math.nan],
        [math.nan, 1.0],
    ]
    assert apply_redundancy_penalties(credits, corr_matrix) == pytest.approx(credits)


def test_redundancy_multiplier_monotone_in_corr() -> None:
    rng = Random(21)
    corrs = sorted(rng.random() for _ in range(20))
    multipliers = [
        redundancy_multiplier(c, thresh=0.4, steepness=12.0, min_multiplier=0.2)
        for c in corrs
    ]

    for earlier, later in zip(multipliers, multipliers[1:]):
        assert later <= earlier + 1e-12
