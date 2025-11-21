"""Test epoch bounds validation."""

import subprocess
import sys
from pathlib import Path


def test_epoch_out_of_bounds_error(tmp_path: Path):
    """Test friendly error for epoch outside baseline range."""
    outdir = tmp_path / "out"
    outdir.mkdir(parents=True, exist_ok=True)

    # Try with an epoch that's likely out of bounds (very high)
    cmd = [
        sys.executable, "-m", "afi_emissions.cli", "emit",
        "--config", "params/emissions_v0.yaml",
        "--epoch", "99999",  # Very high epoch likely to be out of bounds
        "--out", str(outdir)
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    # Should fail with non-zero exit code
    assert proc.returncode != 0, "Should fail for out-of-bounds epoch"
    
    # Should have clear error message
    error_output = proc.stderr.lower()
    assert any(word in error_output for word in ["epoch", "range", "bound", "invalid"]), \
        f"Error message should mention epoch bounds: {proc.stderr}"


def test_negative_epoch_error(tmp_path: Path):
    """Test error for negative epoch."""
    outdir = tmp_path / "out"
    outdir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "afi_emissions.cli", "emit",
        "--config", "params/emissions_v0.yaml",
        "--epoch", "-1",
        "--out", str(outdir)
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    # Should fail with non-zero exit code
    assert proc.returncode != 0, "Should fail for negative epoch"
    
    # Should have clear error message
    error_output = proc.stderr.lower()
    assert any(word in error_output for word in ["epoch", "negative", "invalid"]), \
        f"Error message should mention invalid epoch: {proc.stderr}"
