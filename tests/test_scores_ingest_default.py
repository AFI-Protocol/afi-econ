"""Test scores ingestion - default behavior without --scores."""

import tempfile
from pathlib import Path

from afi_econ_kit.scenarios import run_monte_carlo_simulation


def test_no_scores_baseline():
    """Test that without --scores, gauge outputs are identical to baseline."""
    # Minimal config for fast test
    config = {
        "budget": {"baseline": 1000.0, "aim_enabled": False, "aim_params": {"k": 0.0}},
        "gauge": {
            "weights": {"producers": 0.55, "enrichment": 0.25, "validators": 0.10, "public_goods": 0.10},
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
        "monte_carlo": {"runs": 2, "seed": 1337}  # Small number for speed
    }
    
    # Run simulation twice without bench_data
    result1 = run_monte_carlo_simulation(config)
    result2 = run_monte_carlo_simulation(config)
    
    # Results should be identical (deterministic)
    assert len(result1["epochs"]) == len(result2["epochs"])
    
    # Check first epoch gauge shares are identical
    epoch1_shares1 = result1["epochs"][0]["gauge_capped"]
    epoch1_shares2 = result2["epochs"][0]["gauge_capped"]

    for role in epoch1_shares1:
        assert abs(epoch1_shares1[role] - epoch1_shares2[role]) < 1e-10, \
            f"Role {role} shares differ: {epoch1_shares1[role]} vs {epoch1_shares2[role]}"

    # Check that bench_merit is not applied in diagnostics
    assert not result1["epochs"][0]["gauge_diagnostics"]["bench_merit_applied"]
    assert not result2["epochs"][0]["gauge_diagnostics"]["bench_merit_applied"]


if __name__ == "__main__":
    test_no_scores_baseline()
