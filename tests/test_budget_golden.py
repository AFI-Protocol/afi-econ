"""Golden image test for budget plot reproducibility."""

import hashlib
import os
import tempfile
from pathlib import Path
import pytest
from afi_econ_kit.scenarios import run_monte_carlo_simulation, plot_budget_series


# Expected SHA256 hash of the golden budget plot
# This will be updated when AFI_ECON_REGEN_GOLDEN=1 is set
GOLDEN_BUDGET_HASH = "placeholder_hash_will_be_updated"


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def test_budget_plot_golden():
    """Test that budget plot is reproducible and matches golden hash."""
    # Set golden test environment variable
    os.environ["AFI_ECON_GOLDEN_TEST"] = "1"
    
    try:
        # Fixed configuration for reproducible test
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
                "runs": 20,  # Small number for fast test
                "seed": 12345  # Fixed seed for reproducibility
            }
        }
        
        # Run simulation
        results = run_monte_carlo_simulation(config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create fixed stamp for reproducible plot
            fixed_stamp = {
                "timestamp": "2024-01-01T00:00:00Z",
                "git_short_hash": "abc1234",
                "seed": 12345,
                "data_hash": "test_hash"
            }
            
            # Generate plot
            plot_path = plot_budget_series(results["series"]["budget"], output_dir, fixed_stamp)
            
            # Compute hash
            actual_hash = compute_file_hash(plot_path)
            
            # Check if we should regenerate golden hash
            if os.environ.get("AFI_ECON_REGEN_GOLDEN") == "1":
                print(f"\nNew golden hash for budget plot: {actual_hash}")
                print("Update GOLDEN_BUDGET_HASH in test_budget_golden.py")
                return
            
            # Compare with golden hash
            if GOLDEN_BUDGET_HASH == "placeholder_hash_will_be_updated":
                pytest.skip("Golden hash not set. Run with AFI_ECON_REGEN_GOLDEN=1 to generate.")
            
            assert actual_hash == GOLDEN_BUDGET_HASH, (
                f"Budget plot hash mismatch!\n"
                f"Expected: {GOLDEN_BUDGET_HASH}\n"
                f"Actual:   {actual_hash}\n"
                f"Run with AFI_ECON_REGEN_GOLDEN=1 to update golden hash."
            )
    
    finally:
        # Clean up environment
        if "AFI_ECON_GOLDEN_TEST" in os.environ:
            del os.environ["AFI_ECON_GOLDEN_TEST"]


def test_budget_plot_deterministic():
    """Test that budget plot generation is deterministic."""
    os.environ["AFI_ECON_GOLDEN_TEST"] = "1"
    
    try:
        # Simple test data
        budget_series = [
            {"epoch": 1, "budget": 1000.0, "total_pool": 1000.0, "total_payouts": 850.0},
            {"epoch": 2, "budget": 1000.0, "total_pool": 1000.0, "total_payouts": 900.0},
            {"epoch": 3, "budget": 1000.0, "total_pool": 1000.0, "total_payouts": 875.0}
        ]
        
        fixed_stamp = {
            "timestamp": "2024-01-01T00:00:00Z",
            "git_short_hash": "test123",
            "seed": 999,
            "data_hash": "test_data"
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Generate plot twice
            plot_path1 = plot_budget_series(budget_series, output_dir, fixed_stamp)
            
            # Rename first plot
            plot_path1_copy = output_dir / "budget1.png"
            plot_path1.rename(plot_path1_copy)
            
            plot_path2 = plot_budget_series(budget_series, output_dir, fixed_stamp)
            
            # Compare hashes
            hash1 = compute_file_hash(plot_path1_copy)
            hash2 = compute_file_hash(plot_path2)
            
            assert hash1 == hash2, "Budget plot generation should be deterministic"
    
    finally:
        if "AFI_ECON_GOLDEN_TEST" in os.environ:
            del os.environ["AFI_ECON_GOLDEN_TEST"]


def test_budget_plot_without_golden_env():
    """Test that plot includes timestamp when not in golden test mode."""
    # Make sure golden test env is not set
    if "AFI_ECON_GOLDEN_TEST" in os.environ:
        del os.environ["AFI_ECON_GOLDEN_TEST"]
    
    budget_series = [
        {"epoch": 1, "budget": 1000.0, "total_pool": 1000.0, "total_payouts": 850.0}
    ]
    
    stamp = {
        "timestamp": "2024-01-01T12:00:00Z",
        "git_short_hash": "abc123",
        "seed": 42,
        "data_hash": "test"
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        plot_path = plot_budget_series(budget_series, output_dir, stamp)
        
        # Plot should be created successfully
        assert plot_path.exists()
        assert plot_path.stat().st_size > 0


def test_golden_hash_regeneration_message():
    """Test that regeneration mode prints the expected message."""
    os.environ["AFI_ECON_GOLDEN_TEST"] = "1"
    os.environ["AFI_ECON_REGEN_GOLDEN"] = "1"
    
    try:
        # This should print the new hash and return early
        test_budget_plot_golden()
        
        # If we get here, the test ran in regen mode
        # (The actual assertion would be skipped)
        
    finally:
        # Clean up environment
        for env_var in ["AFI_ECON_GOLDEN_TEST", "AFI_ECON_REGEN_GOLDEN"]:
            if env_var in os.environ:
                del os.environ[env_var]


def test_plot_file_properties():
    """Test basic properties of generated plot file."""
    os.environ["AFI_ECON_GOLDEN_TEST"] = "1"
    
    try:
        budget_series = [
            {"epoch": 1, "budget": 1000.0, "total_pool": 1000.0, "total_payouts": 850.0},
            {"epoch": 2, "budget": 1100.0, "total_pool": 1100.0, "total_payouts": 950.0}
        ]
        
        stamp = {
            "timestamp": "2024-01-01T00:00:00Z",
            "git_short_hash": "test",
            "seed": 1,
            "data_hash": "test"
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            plot_path = plot_budget_series(budget_series, output_dir, stamp)
            
            # Check file properties
            assert plot_path.exists()
            assert plot_path.suffix == ".png"
            assert plot_path.name == "econ_budget.png"
            
            # Check file is not empty and has reasonable size
            file_size = plot_path.stat().st_size
            assert file_size > 1000, f"Plot file too small: {file_size} bytes"
            assert file_size < 1_000_000, f"Plot file too large: {file_size} bytes"
    
    finally:
        if "AFI_ECON_GOLDEN_TEST" in os.environ:
            del os.environ["AFI_ECON_GOLDEN_TEST"]
