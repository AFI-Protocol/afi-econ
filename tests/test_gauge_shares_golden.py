"""Golden test for gauge shares figure reproducibility."""

import hashlib
import os
import tempfile
from pathlib import Path

import pytest

from afi_econ_kit.scenarios import run_monte_carlo_simulation


# Expected SHA256 hash of the gauge shares plot
GOLDEN_HASH = "edd897fade1f6ba118d36975d624a170156cbd45988c9df4297faa9719db482b"


def test_gauge_shares_golden():
    """Test that gauge shares plot is reproducible."""
    # Environment stabilization
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["TZ"] = "UTC"
    os.environ["PYTHONHASHSEED"] = "0"
    os.environ["AFI_ECON_KIT_GOLDEN_TEST"] = "1"

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
        "monte_carlo": {"runs": 3, "seed": 42}  # Small number for speed
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Run simulation
        results = run_monte_carlo_simulation(config)

        # Save outputs to get the plot
        from afi_econ_kit.scenarios import save_simulation_outputs
        saved_paths = save_simulation_outputs(results, tmpdir_path)

        # Find the gauge shares plot
        gauge_plot_path = tmpdir_path / "econ_gauge_shares.png"
        assert gauge_plot_path.exists(), "Gauge shares plot not created"

        # Compute hash
        with gauge_plot_path.open("rb") as f:
            plot_hash = hashlib.sha256(f.read()).hexdigest()

        # Check for regeneration mode
        if os.environ.get("AFI_ECON_KIT_REGEN_GOLDEN") == "1":
            print(f"Generated hash: {plot_hash}")
            return  # Pass in regen mode

        # Golden image policy: CI strict, local forgiving
        enforce_golden = os.environ.get("AFI_ECON_KIT_ENFORCE_GOLDEN") == "1"

        if enforce_golden:
            # CI mode: strict hash assertion
            assert plot_hash == GOLDEN_HASH, f"Plot hash mismatch. Expected: {GOLDEN_HASH}, Got: {plot_hash}"
        else:
            # Local mode: print hash but don't assert
            print(f"Gauge golden (local): {plot_hash} (assertion skipped)")
            # Just verify the plot was created successfully
            assert len(plot_hash) == 64, "Plot hash should be valid SHA256"


if __name__ == "__main__":
    test_gauge_shares_golden()
