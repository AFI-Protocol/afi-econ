"""Tests for replay determinism - fixed inputs/seed should produce identical outputs."""

import copy
import json
import tempfile
from pathlib import Path
import pandas as pd
import pytest
from afi_econ_kit.scenarios import run_monte_carlo_simulation


def test_monte_carlo_determinism():
    """Test that Monte Carlo simulation is deterministic with fixed seed."""
    config = {
        "budget": {
            "baseline": 1000.0,
            "aim_enabled": False,
            "aim_params": {"k": 0.0}
        },
        "gauge": {
            "weights": {
                "producers": 0.55,
                "enrichment": 0.25,
                "validators": 0.10,
                "public_goods": 0.10
            },
            "caps": {"per_role_max": 0.60},
            "policy_merit_blend": 0.5,
            "version": "v0"
        },
        "safety": {
            "budget_rate_limit": 0.20,
            "weight_rate_limit": 0.15,
            "smoothing_alpha": 0.25,
            "breaker": {"dispute_rate": 0.08}
        },
        "payouts": {
            "maturity_hold_frac": 0.15
        },
        "monte_carlo": {
            "runs": 10,  # Small number for fast test
            "seed": 42
        }
    }
    
    # Run simulation twice
    result1 = run_monte_carlo_simulation(config)
    result2 = run_monte_carlo_simulation(config)
    
    # Results should be identical
    assert result1["summary"] == result2["summary"]
    assert len(result1["epochs"]) == len(result2["epochs"])
    assert len(result1["series"]["budget"]) == len(result2["series"]["budget"])
    
    # Check that budget series are identical
    for i, (b1, b2) in enumerate(zip(result1["series"]["budget"], result2["series"]["budget"])):
        assert b1["epoch"] == b2["epoch"], f"Epoch mismatch at index {i}"
        assert b1["budget"] == b2["budget"], f"Budget mismatch at epoch {b1['epoch']}"
        assert b1["total_pool"] == b2["total_pool"], f"Pool mismatch at epoch {b1['epoch']}"
    
    # Check that gauge series are identical
    for i, (g1, g2) in enumerate(zip(result1["series"]["gauge"], result2["series"]["gauge"])):
        assert g1["epoch"] == g2["epoch"], f"Gauge epoch mismatch at index {i}"
        for role in ["producers", "enrichment", "validators", "public_goods"]:
            assert g1[role] == g2[role], f"Gauge {role} mismatch at epoch {g1['epoch']}"


def test_different_seeds_produce_different_results():
    """Test that different seeds produce different results."""
    base_config = {
        "budget": {
            "baseline": 1000.0,
            "aim_enabled": False,
            "aim_params": {"k": 0.0}
        },
        "gauge": {
            "weights": {
                "producers": 0.55,
                "enrichment": 0.25,
                "validators": 0.10,
                "public_goods": 0.10
            },
            "caps": {"per_role_max": 0.60},
            "policy_merit_blend": 0.5,
            "version": "v0"
        },
        "safety": {
            "budget_rate_limit": 0.20,
            "weight_rate_limit": 0.15,
            "smoothing_alpha": 0.25,
            "breaker": {"dispute_rate": 0.08}
        },
        "payouts": {
            "maturity_hold_frac": 0.15
        },
        "monte_carlo": {
            "runs": 10,
            "seed": None  # Will be set below
        }
    }
    
    # Run with different seeds
    config1 = copy.deepcopy(base_config)
    config1["monte_carlo"]["seed"] = 42

    config2 = copy.deepcopy(base_config)
    config2["monte_carlo"]["seed"] = 123
    
    result1 = run_monte_carlo_simulation(config1)
    result2 = run_monte_carlo_simulation(config2)
    
    # Results should be different (at least some values)
    # Check for differences in epoch results which contain random components
    epochs1 = result1["epochs"]
    epochs2 = result2["epochs"]

    # Find at least one difference in merit or gauge results
    differences_found = False
    for e1, e2 in zip(epochs1, epochs2):
        # Check merit inputs (should be different due to random receipts)
        merit1 = e1["merit"]
        merit2 = e2["merit"]
        for key in merit1:
            if abs(merit1[key] - merit2[key]) > 1e-10:
                differences_found = True
                break
        if differences_found:
            break

        # Check receipts count (should be different due to randomness)
        if e1["receipts_count"] != e2["receipts_count"]:
            differences_found = True
            break

        # Check gauge results (may be different due to merit differences)
        gauge1 = e1["gauge_raw"]
        gauge2 = e2["gauge_raw"]
        for role in gauge1:
            if abs(gauge1[role] - gauge2[role]) > 1e-10:
                differences_found = True
                break
        if differences_found:
            break

    assert differences_found, "Different seeds should produce different results"


def test_config_changes_affect_results():
    """Test that configuration changes affect simulation results."""
    base_config = {
        "budget": {
            "baseline": 1000.0,
            "aim_enabled": False,
            "aim_params": {"k": 0.0}
        },
        "gauge": {
            "weights": {
                "producers": 0.55,
                "enrichment": 0.25,
                "validators": 0.10,
                "public_goods": 0.10
            },
            "caps": {"per_role_max": 0.60},
            "policy_merit_blend": 0.5,
            "version": "v0"
        },
        "safety": {
            "budget_rate_limit": 0.20,
            "weight_rate_limit": 0.15,
            "smoothing_alpha": 0.25,
            "breaker": {"dispute_rate": 0.08}
        },
        "payouts": {
            "maturity_hold_frac": 0.15
        },
        "monte_carlo": {
            "runs": 5,
            "seed": 42
        }
    }
    
    # Run with base config
    result1 = run_monte_carlo_simulation(base_config)
    
    # Run with different budget
    config2 = dict(base_config)
    config2["budget"]["baseline"] = 2000.0  # Double the budget
    result2 = run_monte_carlo_simulation(config2)
    
    # Budget series should be different
    budget1 = result1["series"]["budget"][0]["budget"]
    budget2 = result2["series"]["budget"][0]["budget"]
    
    assert budget1 != budget2, "Different budget configs should produce different results"
    assert budget2 == 2000.0, "Budget should match config"


def test_stamp_consistency():
    """Test that stamp contains expected fields and is consistent."""
    config = {
        "budget": {"baseline": 1000.0, "aim_enabled": False, "aim_params": {"k": 0.0}},
        "gauge": {
            "weights": {"producers": 0.5, "enrichment": 0.3, "validators": 0.2, "public_goods": 0.0},
            "caps": {"per_role_max": 0.60},
            "policy_merit_blend": 0.5,
            "version": "v0"
        },
        "safety": {
            "budget_rate_limit": 0.20,
            "weight_rate_limit": 0.15,
            "smoothing_alpha": 0.25,
            "breaker": {"dispute_rate": 0.08}
        },
        "payouts": {"maturity_hold_frac": 0.15},
        "monte_carlo": {"runs": 3, "seed": 999}
    }
    
    result = run_monte_carlo_simulation(config)
    stamp = result["stamp"]
    
    # Check required fields
    required_fields = ["timestamp", "git_short_hash", "seed", "data_hash"]
    for field in required_fields:
        assert field in stamp, f"Missing stamp field: {field}"
    
    # Check seed matches config
    assert stamp["seed"] == 999
    
    # Check timestamp format (should be ISO format)
    assert "T" in stamp["timestamp"]
    assert stamp["timestamp"].endswith("Z") or "+" in stamp["timestamp"]


def test_empty_epochs_handling():
    """Test simulation handles edge cases gracefully."""
    config = {
        "budget": {"baseline": 0.0, "aim_enabled": False, "aim_params": {"k": 0.0}},
        "gauge": {
            "weights": {"producers": 1.0, "enrichment": 0.0, "validators": 0.0, "public_goods": 0.0},
            "caps": {"per_role_max": 1.0},
            "policy_merit_blend": 0.0,
            "version": "v0"
        },
        "safety": {
            "budget_rate_limit": 0.20,
            "weight_rate_limit": 0.15,
            "smoothing_alpha": 0.25,
            "breaker": {"dispute_rate": 0.08}
        },
        "payouts": {"maturity_hold_frac": 0.0},
        "monte_carlo": {"runs": 2, "seed": 1}
    }
    
    # Should not crash with zero budget
    result = run_monte_carlo_simulation(config)
    
    assert result["summary"]["total_epochs"] == 2
    assert len(result["epochs"]) == 2
    assert result["summary"]["final_budget"] == 0.0
