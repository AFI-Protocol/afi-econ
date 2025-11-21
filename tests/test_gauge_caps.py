"""Tests for gauge caps functionality."""

import pytest
from afi_econ_kit.gauge import allocation_gauge, compute_merit_inputs
import pandas as pd


def test_gauge_caps_honored():
    """Test that per-role caps are honored."""
    weights = {
        "producers": 0.8,  # This exceeds the cap
        "enrichment": 0.1,
        "validators": 0.05,
        "public_goods": 0.05
    }
    
    caps = {"per_role_max": 0.6}
    merit = {}
    
    result = allocation_gauge(weights, caps, merit, blend=0.0)
    
    # Check that no role exceeds the cap
    for role, allocation in result["capped"].items():
        assert allocation <= caps["per_role_max"], f"Role {role} exceeds cap: {allocation}"
    
    # Check that producers was capped
    assert "producers" in result["diag"]["capped_roles"]


def test_gauge_renorm_sums_to_one():
    """Test that final allocation sums to 1.0 after renormalization."""
    weights = {
        "producers": 0.7,
        "enrichment": 0.2,
        "validators": 0.1,
        "public_goods": 0.0
    }
    
    caps = {"per_role_max": 0.5}
    merit = {}
    
    result = allocation_gauge(weights, caps, merit, blend=0.0)
    
    # Check that capped allocation sums to 1.0
    total = sum(result["capped"].values())
    assert abs(total - 1.0) < 1e-10, f"Total allocation {total} does not sum to 1.0"


def test_gauge_diagnostics_sane():
    """Test that diagnostics contain expected information."""
    weights = {
        "producers": 0.6,
        "enrichment": 0.3,
        "validators": 0.1,
        "public_goods": 0.0
    }
    
    caps = {"per_role_max": 0.4}
    merit = {"confidence": 0.8, "novelty": 0.6}
    
    result = allocation_gauge(weights, caps, merit, blend=0.3)
    
    diag = result["diag"]
    
    # Check diagnostic fields exist
    assert "capped_roles" in diag
    assert "total_raw" in diag
    assert "total_capped" in diag
    assert "blend_factor" in diag
    assert "merit_applied" in diag
    
    # Check values are reasonable
    assert diag["blend_factor"] == 0.3
    assert diag["merit_applied"] is True
    assert isinstance(diag["capped_roles"], list)
    assert diag["total_raw"] > 0
    assert abs(diag["total_capped"] - 1.0) < 1e-10


def test_compute_merit_inputs_empty_df():
    """Test merit computation with empty DataFrame."""
    empty_df = pd.DataFrame()
    merit = compute_merit_inputs(empty_df)
    
    expected_keys = ["confidence", "novelty", "attestation_accuracy", "timeliness"]
    assert set(merit.keys()) == set(expected_keys)
    
    # All values should be 0.0 for empty input
    for key in expected_keys:
        assert merit[key] == 0.0


def test_compute_merit_inputs_with_data():
    """Test merit computation with actual data."""
    data = {
        "confidence": [0.8, 0.9, 0.7],
        "novelty_score": [0.6, 0.8, 0.5],
        "attestation_correct": [1, 1, 0],
        "response_time": [1.0, 2.0, 3.0]
    }
    df = pd.DataFrame(data)
    
    merit = compute_merit_inputs(df)
    
    # Check that values are computed correctly
    assert merit["confidence"] == pytest.approx(0.8, abs=1e-10)  # mean of [0.8, 0.9, 0.7]
    assert merit["novelty"] == pytest.approx(0.633, abs=1e-2)  # mean of [0.6, 0.8, 0.5]
    assert merit["attestation_accuracy"] == pytest.approx(0.667, abs=1e-2)  # 2/3
    assert 0.0 <= merit["timeliness"] <= 1.0  # Should be normalized


def test_gauge_no_merit_blend():
    """Test gauge with no merit blending (pure policy)."""
    weights = {
        "producers": 0.5,
        "enrichment": 0.3,
        "validators": 0.2,
        "public_goods": 0.0
    }
    
    caps = {"per_role_max": 1.0}  # No caps
    merit = {"confidence": 0.9}
    
    result = allocation_gauge(weights, caps, merit, blend=0.0)
    
    # With no blending and no caps, should match original weights
    for role in weights:
        assert result["capped"][role] == pytest.approx(weights[role], abs=1e-10)


def test_gauge_full_merit_blend():
    """Test gauge with full merit blending."""
    weights = {
        "producers": 0.25,
        "enrichment": 0.25,
        "validators": 0.25,
        "public_goods": 0.25
    }
    
    caps = {"per_role_max": 1.0}  # No caps
    merit = {"confidence": 0.8, "novelty": 0.6}
    
    result = allocation_gauge(weights, caps, merit, blend=1.0)
    
    # With full merit blending, allocation should be different from original weights
    # (exact values depend on merit computation, but should still sum to 1)
    total = sum(result["capped"].values())
    assert abs(total - 1.0) < 1e-10
    
    # Merit should be applied
    assert result["diag"]["merit_applied"] is True
