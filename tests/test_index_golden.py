"""Golden test for AFI Index plot reproducibility."""

import hashlib
import os
import tempfile
from pathlib import Path
import pytest

from afi_econ_kit.index import compute_index_from_receipts, create_index_plot


# Golden hash for the index plot (will be updated during development)
GOLDEN_INDEX_HASH = "a53d6b530f636839d36c89cc03b6eec8064cbdc44b4ce70e8856e169309faf39"


def test_index_plot_golden():
    """Test that index plot is reproducible."""
    # Environment stabilization
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["TZ"] = "UTC"
    os.environ["PYTHONHASHSEED"] = "0"
    os.environ["AFI_ECON_GOLDEN_TEST"] = "1"
    
    # Fixed test data for reproducible results
    receipts_data = [
        {"participant_id": "user_001", "role": "reputation", "region": "north_america", "amount": 100.0},
        {"participant_id": "user_002", "role": "poi", "region": "europe", "amount": 150.0},
        {"participant_id": "user_003", "role": "poinsight", "region": "asia", "amount": 200.0},
        {"participant_id": "user_001", "role": "reputation", "region": "north_america", "amount": 75.0},
    ]
    
    payouts_data = [
        {"participant_id": "user_001", "role": "reputation", "amount": 250.0},
        {"participant_id": "user_002", "role": "poi", "amount": 300.0},
        {"participant_id": "user_003", "role": "poinsight", "amount": 350.0},
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Compute index
        results = compute_index_from_receipts(
            receipts_data=receipts_data,
            payouts_data=payouts_data,
            epoch=1
        )
        
        # Create index plot
        plot_path = tmpdir_path / "afi_index.png"
        create_index_plot(results, plot_path)
        
        assert plot_path.exists(), "Index plot not created"
        
        # Compute hash
        with plot_path.open("rb") as f:
            plot_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Check for regeneration mode
        if os.environ.get("AFI_ECON_REGEN_GOLDEN") == "1":
            print(f"Generated hash: {plot_hash}")
            return  # Pass in regen mode
        
        # Golden image policy: CI strict, local forgiving
        enforce_golden = os.environ.get("AFI_ECON_ENFORCE_GOLDEN") == "1"
        
        if enforce_golden:
            # CI mode: strict hash assertion
            assert plot_hash == GOLDEN_INDEX_HASH, f"Plot hash mismatch. Expected: {GOLDEN_INDEX_HASH}, Got: {plot_hash}"
        else:
            # Local mode: print hash but don't assert
            print(f"Index golden (local): {plot_hash} (assertion skipped)")
            # Just verify the plot was created successfully
            assert len(plot_hash) == 64, "Plot hash should be valid SHA256"


def test_index_plot_deterministic():
    """Test that index plot generation is deterministic."""
    # Environment stabilization
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["TZ"] = "UTC"
    os.environ["PYTHONHASHSEED"] = "0"
    
    receipts_data = [
        {"participant_id": "user_001", "role": "reputation", "region": "north_america", "amount": 100.0},
        {"participant_id": "user_002", "role": "poi", "region": "europe", "amount": 150.0},
    ]
    
    payouts_data = [
        {"participant_id": "user_001", "role": "reputation", "amount": 250.0},
        {"participant_id": "user_002", "role": "poi", "amount": 300.0},
    ]
    
    # Generate plot twice
    hashes = []
    for i in range(2):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            results = compute_index_from_receipts(
                receipts_data=receipts_data,
                payouts_data=payouts_data,
                epoch=1
            )
            
            plot_path = tmpdir_path / f"test_plot_{i}.png"
            create_index_plot(results, plot_path)
            
            with plot_path.open("rb") as f:
                plot_hash = hashlib.sha256(f.read()).hexdigest()
                hashes.append(plot_hash)
    
    assert hashes[0] == hashes[1], "Index plot should be deterministic"
    print(f"✓ Index plot is deterministic: {hashes[0][:16]}...")


def test_index_computation_deterministic():
    """Test that index computation is deterministic."""
    receipts_data = [
        {"participant_id": "user_001", "role": "reputation", "region": "north_america", "amount": 100.0},
        {"participant_id": "user_002", "role": "poi", "region": "europe", "amount": 150.0},
        {"participant_id": "user_003", "role": "poinsight", "region": "asia", "amount": 200.0},
    ]
    
    payouts_data = [
        {"participant_id": "user_001", "role": "reputation", "amount": 250.0},
        {"participant_id": "user_002", "role": "poi", "amount": 300.0},
        {"participant_id": "user_003", "role": "poinsight", "amount": 350.0},
    ]
    
    # Compute index twice
    results1 = compute_index_from_receipts(
        receipts_data=receipts_data,
        payouts_data=payouts_data,
        epoch=1
    )
    
    results2 = compute_index_from_receipts(
        receipts_data=receipts_data,
        payouts_data=payouts_data,
        epoch=1
    )
    
    # Check that results are identical
    assert results1["I_t"] == results2["I_t"], "Index computation should be deterministic"
    assert results1["components"]["AN_t"] == results2["components"]["AN_t"], "AN_t should be deterministic"
    assert results1["components"]["EG_t"] == results2["components"]["EG_t"], "EG_t should be deterministic"
    assert results1["components"]["Cov_t"] == results2["components"]["Cov_t"], "Cov_t should be deterministic"
    
    print(f"✓ Index computation is deterministic: I_t={results1['I_t']:.6f}")


def test_index_components_range():
    """Test that all index components are in valid range [0, 1]."""
    receipts_data = [
        {"participant_id": "user_001", "role": "reputation", "region": "north_america", "amount": 100.0},
        {"participant_id": "user_002", "role": "poi", "region": "europe", "amount": 150.0},
    ]
    
    payouts_data = [
        {"participant_id": "user_001", "role": "reputation", "amount": 250.0},
        {"participant_id": "user_002", "role": "poi", "amount": 300.0},
    ]
    
    results = compute_index_from_receipts(
        receipts_data=receipts_data,
        payouts_data=payouts_data,
        epoch=1
    )
    
    # Check component ranges
    components = results["components"]
    assert 0.0 <= components["AN_t"] <= 1.0, f"AN_t out of range: {components['AN_t']}"
    assert 0.0 <= components["EG_t"] <= 1.0, f"EG_t out of range: {components['EG_t']}"
    assert 0.0 <= components["Cov_t"] <= 1.0, f"Cov_t out of range: {components['Cov_t']}"
    assert 0.0 <= results["I_t"] <= 1.0, f"I_t out of range: {results['I_t']}"
    
    print(f"✓ All components in valid range: AN_t={components['AN_t']:.3f}, EG_t={components['EG_t']:.3f}, Cov_t={components['Cov_t']:.3f}, I_t={results['I_t']:.3f}")


def test_index_empty_data():
    """Test index computation with empty data."""
    # Empty receipts and payouts
    results = compute_index_from_receipts(
        receipts_data=[],
        payouts_data=[],
        epoch=1
    )
    
    # Should handle empty data gracefully
    assert results["I_t"] == 0.0, "Index should be 0.0 for empty data"
    assert results["components"]["AN_t"] == 0.0, "AN_t should be 0.0 for empty receipts"
    assert results["components"]["EG_t"] == 0.0, "EG_t should be 0.0 for empty payouts"
    assert results["components"]["Cov_t"] == 0.0, "Cov_t should be 0.0 for empty receipts"
    
    print("✓ Empty data handled correctly")
