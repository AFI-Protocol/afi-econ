"""Smoke tests for CLI emit command."""

import json
import subprocess
import sys
from pathlib import Path


def test_cli_emit_smoke(tmp_path: Path):
    """Test that emit command produces valid output."""
    outdir = tmp_path / "out"
    outdir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "afi_emissions.cli", "emit",
        "--config", "params/emissions_v0.yaml",
        "--epoch", "208",
        "--out", str(outdir)
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"Command failed: {proc.stderr}"
    
    # Check that epoch_budget.json exists
    budget_path = outdir / "epoch_budget.json"
    assert budget_path.exists(), "epoch_budget.json not created"
    
    # Load and validate JSON structure
    with budget_path.open() as f:
        data = json.load(f)
    
    # Check required fields
    assert "epoch" in data
    assert "B_t" in data
    assert "AIM" in data
    assert "E_t" in data
    assert "stamp" in data
    
    # Check values are reasonable
    assert data["epoch"] == 208
    assert isinstance(data["B_t"], (int, float))
    assert isinstance(data["E_t"], (int, float))
    assert data["E_t"] >= 0, "E_t must be non-negative"
    
    # Check AIM structure
    aim = data["AIM"]
    assert "m_t" in aim or "factor" in aim  # Allow either naming
    assert "params" in aim or "enabled" in aim  # Allow flexible structure
    
    # Check stamp structure
    stamp = data["stamp"]
    assert "utc_ts" in stamp
    assert "git_sha_short" in stamp or "git_sha" in stamp
    assert "config_hash" in stamp
    assert "params_version" in stamp or "version" in stamp
