"""Focused regression test for cumulative supply monotonicity guardrails."""

import numpy as np
import pandas as pd

from afi_econ_kit.data_io import _compute_robust_cum_supply
from afi_econ_kit.emissions import assert_monotone_cum_supply


def test_cum_supply_guard_with_emission_drop():
    """Test that cum_supply remains monotonic even when per-epoch emissions drop."""
    # Create synthetic data that emulates the row 207->208 case
    # where per-epoch emission drops significantly
    data = {
        "epoch": [1, 2, 3, 4, 5],
        "emission": [137820512.82, 137820512.82, 137820512.82, 137820512.82, 32158119.66],
        "aim": [1.0, 1.0, 1.0, 1.0, 1.0],
        "year": [1, 1, 1, 1, 2],
        "mult_aim": [1.0, 1.0, 1.0, 1.0, 1.0],
        "mult_ce": [1.0, 1.0, 1.0, 1.0, 1.0],
        "mult_all": [1.0, 1.0, 1.0, 1.0, 1.0],
        # Deliberately set cum_supply to have a drop (simulating bad input data)
        "cum_supply": [137820512.82, 275641025.64, 413461538.46, 551282051.28, 32158119.66]
    }
    
    df = pd.DataFrame(data)
    
    # Apply the robust cumulative supply computation
    _compute_robust_cum_supply(df)
    
    # Verify that cum_supply is now monotonic
    assert_monotone_cum_supply(df)
    
    # Also verify directly with numpy
    cum_supply_values = df["cum_supply"].to_numpy(dtype=float)
    diffs = np.diff(cum_supply_values)
    assert np.all(diffs >= -1e-12), f"Cumulative supply not monotonic: diffs={diffs}"
    
    # Verify the expected cumulative values
    expected_cum = np.array([137820512.82, 275641025.64, 413461538.46, 551282051.28, 583440170.94])
    np.testing.assert_allclose(df["cum_supply"].values, expected_cum, rtol=1e-6)


def test_cum_supply_guard_with_negative_emission():
    """Test that negative emissions are clipped to zero."""
    data = {
        "epoch": [1, 2, 3, 4],
        "emission": [100.0, -50.0, 75.0, 25.0],  # Negative emission in epoch 2
        "aim": [1.0, 1.0, 1.0, 1.0],
        "year": [1, 1, 1, 1],
        "mult_aim": [1.0, 1.0, 1.0, 1.0],
        "mult_ce": [1.0, 1.0, 1.0, 1.0],
        "mult_all": [1.0, 1.0, 1.0, 1.0],
        "cum_supply": [100.0, 50.0, 125.0, 150.0]  # Bad input data
    }
    
    df = pd.DataFrame(data)
    
    # Apply the robust cumulative supply computation
    _compute_robust_cum_supply(df)
    
    # Verify monotonicity
    assert_monotone_cum_supply(df)
    
    # Verify that negative emission was clipped to zero
    assert df["emission_final"].iloc[1] == 0.0
    
    # Verify expected cumulative values (negative emission becomes 0)
    expected_cum = np.array([100.0, 100.0, 175.0, 200.0])  # 100, 100+0, 100+0+75, 100+0+75+25
    np.testing.assert_allclose(df["cum_supply"].values, expected_cum, rtol=1e-6)


def test_cum_supply_guard_with_multipliers():
    """Test that multipliers are properly applied before cumsum."""
    data = {
        "epoch": [1, 2, 3],
        "emission": [100.0, 100.0, 100.0],
        "aim": [1.0, 1.0, 1.0],
        "year": [1, 1, 1],
        "mult_aim": [1.0, 1.5, 2.0],
        "mult_ce": [1.0, 1.0, 1.0],
        "mult_all": [1.0, 1.0, 1.0],
        "cum_supply": [100.0, 200.0, 300.0]  # Bad input data
    }
    
    df = pd.DataFrame(data)
    
    # Apply the robust cumulative supply computation
    _compute_robust_cum_supply(df)
    
    # Verify monotonicity
    assert_monotone_cum_supply(df)
    
    # Verify that multipliers were applied correctly
    expected_emissions = np.array([100.0, 150.0, 200.0])  # 100*1, 100*1.5, 100*2
    np.testing.assert_allclose(df["emission_final"].values, expected_emissions, rtol=1e-6)
    
    # Verify expected cumulative values
    expected_cum = np.array([100.0, 250.0, 450.0])  # 100, 100+150, 100+150+200
    np.testing.assert_allclose(df["cum_supply"].values, expected_cum, rtol=1e-6)


def test_cum_supply_guard_with_missing_multipliers():
    """Test that missing multipliers default to 1.0."""
    data = {
        "epoch": [1, 2, 3],
        "emission": [100.0, 100.0, 100.0],
        "aim": [1.0, 1.0, 1.0],
        "year": [1, 1, 1],
        # No multiplier columns
        "cum_supply": [100.0, 200.0, 300.0]
    }
    
    df = pd.DataFrame(data)
    
    # Apply the robust cumulative supply computation
    _compute_robust_cum_supply(df)
    
    # Verify monotonicity
    assert_monotone_cum_supply(df)
    
    # Verify that default multipliers (1.0) were used
    expected_cum = np.array([100.0, 200.0, 300.0])  # Simple cumsum
    np.testing.assert_allclose(df["cum_supply"].values, expected_cum, rtol=1e-6)


def test_cum_supply_guard_enforces_monotonicity():
    """Test that the final guardrail enforces monotonicity even with edge cases."""
    # Create a DataFrame with a pre-existing drop in cum_supply to test the guardrail
    data = {
        "epoch": [1, 2, 3, 4],
        "emission": [100.0, 100.0, 100.0, 100.0],
        "aim": [1.0, 1.0, 1.0, 1.0],
        "year": [1, 1, 1, 1],
        "mult_aim": [1.0, 1.0, 1.0, 1.0],
        "mult_ce": [1.0, 1.0, 1.0, 1.0],
        "mult_all": [1.0, 1.0, 1.0, 1.0],
        # Start with a drop in cum_supply to test the guardrail
        "cum_supply": [100.0, 200.0, 150.0, 400.0]  # Drop from 200 to 150
    }

    df = pd.DataFrame(data)

    # Apply the robust cumulative supply computation (which includes the guardrail)
    _compute_robust_cum_supply(df)

    # Verify monotonicity is enforced
    assert_monotone_cum_supply(df)

    # Verify the guardrail fixed the drop using maximum.accumulate
    # The guardrail should make 150 become 200 (the previous maximum)
    expected_cum = np.array([100.0, 200.0, 300.0, 400.0])  # Proper cumsum from emissions
    np.testing.assert_allclose(df["cum_supply"].values, expected_cum, rtol=1e-6)
