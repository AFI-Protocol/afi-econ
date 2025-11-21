"""Tests for AFI emissions budget ingestion."""

import json
import tempfile
from pathlib import Path
import pytest

from afi_econ_kit.cli import _load_budget_data
from afi_econ_kit.scenarios import create_stamp


def test_load_budget_data_valid():
    """Test loading valid budget data."""
    # Create a valid budget file
    budget_data = {
        "epoch": 208,
        "B_t": 950.23,
        "AIM": {
            "enabled": True,
            "k": 0.05,
            "factor": 1.03
        },
        "E_t": 978.74,
        "stamp": {
            "version": "0.1.0",
            "git_sha": "abc1234",
            "utc_ts": "2024-01-01T12:00:00Z",
            "config_hash": "sha256..."
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(budget_data, f)
        budget_path = f.name
    
    try:
        result = _load_budget_data(budget_path)
        
        # Check structure
        assert "budget" in result
        assert "path" in result
        assert "hash" in result
        assert "stamp" in result
        
        # Check budget data
        assert result["budget"]["epoch"] == 208
        assert result["budget"]["B_t"] == 950.23
        assert result["budget"]["E_t"] == 978.74
        assert result["budget"]["AIM"]["factor"] == 1.03
        
        # Check provenance
        assert result["path"] == str(Path(budget_path).resolve())
        assert len(result["hash"]) == 64  # SHA256 hex length
        assert result["stamp"]["version"] == "0.1.0"
        
        print("✓ Valid budget data loaded successfully")
        
    finally:
        Path(budget_path).unlink()


def test_load_budget_data_missing_file():
    """Test loading budget data from non-existent file."""
    with pytest.raises(FileNotFoundError):
        _load_budget_data("/nonexistent/budget.json")


def test_load_budget_data_invalid_schema():
    """Test loading budget data with missing required fields."""
    # Create budget with missing required field
    invalid_budget = {
        "epoch": 208,
        "B_t": 950.23,
        # Missing "AIM" and "E_t"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(invalid_budget, f)
        budget_path = f.name
    
    try:
        with pytest.raises(ValueError, match="Budget file missing required field"):
            _load_budget_data(budget_path)
    finally:
        Path(budget_path).unlink()


def test_load_budget_data_none():
    """Test loading budget data when no path provided."""
    result = _load_budget_data(None)
    
    assert result["budget"] is None
    assert result["path"] is None
    assert result["hash"] is None
    assert result["stamp"] is None


def test_create_stamp_with_budget():
    """Test stamp creation with budget data."""
    # Create mock budget data
    budget_data = {
        "budget": {
            "epoch": 208,
            "B_t": 950.23,
            "E_t": 978.74
        },
        "path": "/path/to/budget.json",
        "hash": "abc123def456",
        "stamp": {
            "version": "0.1.0",
            "git_sha": "xyz789"
        }
    }
    
    stamp = create_stamp(
        seed=42,
        data_hash="test_hash",
        config_path="config.yaml",
        params_path="params/gauge_v0.yaml",
        bench_data=None,
        budget_data=budget_data
    )
    
    # Check budget fields in stamp
    assert stamp["budget_path"] == "/path/to/budget.json"
    assert stamp["budget_hash"] == "abc123def456"
    assert stamp["budget_stamp"]["version"] == "0.1.0"
    assert stamp["budget_epoch"] == 208
    
    # Check other fields still present
    assert stamp["seed"] == 42
    assert stamp["data_hash"] == "test_hash"
    assert "timestamp" in stamp
    assert "version" in stamp
    
    print("✓ Stamp creation with budget data works")


def test_create_stamp_without_budget():
    """Test stamp creation without budget data."""
    stamp = create_stamp(
        seed=42,
        data_hash="test_hash",
        config_path="config.yaml",
        params_path="params/gauge_v0.yaml",
        bench_data=None,
        budget_data=None
    )
    
    # Check budget fields are None
    assert stamp["budget_path"] is None
    assert stamp["budget_hash"] is None
    assert stamp["budget_stamp"] is None
    assert stamp["budget_epoch"] is None
    
    # Check other fields still present
    assert stamp["seed"] == 42
    assert stamp["data_hash"] == "test_hash"
    
    print("✓ Stamp creation without budget data works")


def test_budget_schema_validation():
    """Test that all required budget schema fields are validated."""
    required_fields = ["epoch", "B_t", "AIM", "E_t"]
    
    for missing_field in required_fields:
        # Create budget missing one required field
        budget_data = {
            "epoch": 208,
            "B_t": 950.23,
            "AIM": {"enabled": True, "k": 0.05, "factor": 1.03},
            "E_t": 978.74
        }
        del budget_data[missing_field]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(budget_data, f)
            budget_path = f.name
        
        try:
            with pytest.raises(ValueError, match=f"Budget file missing required field: {missing_field}"):
                _load_budget_data(budget_path)
        finally:
            Path(budget_path).unlink()
    
    print("✓ All required schema fields are validated")
