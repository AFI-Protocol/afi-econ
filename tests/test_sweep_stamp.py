# SPDX-License-Identifier: Apache-2.0
"""Test sweep stamp contract."""

import json
import tempfile
import subprocess
from pathlib import Path


def test_sweep_stamp_contract():
    """Test that sweep run_report.json contains required provenance fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "sweep_stamp_test"
        
        # Run minimal sweep command
        result = subprocess.run([
            "afi-emissions", "sweep",
            "--config", "params/emissions_v0.yaml",
            "--grid", "params/sweep.yaml", 
            "--out", str(output_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Command failed: {result.stderr}"
        
        # Load run_report.json
        report_path = output_dir / "run_report.json"
        assert report_path.exists(), "run_report.json should exist"
        
        with report_path.open() as f:
            report = json.load(f)
        
        # Check stamp structure
        assert "stamp" in report, "Report should contain stamp"
        stamp = report["stamp"]
        
        # Required fields
        required_fields = ["version", "git_sha_short", "config_hash", "grid_hash", "utc_ts"]
        for field in required_fields:
            assert field in stamp, f"Stamp should contain {field}"
            assert stamp[field] is not None, f"{field} should not be null"
            assert isinstance(stamp[field], str), f"{field} should be string"
            assert len(stamp[field]) > 0, f"{field} should not be empty"
        
        # Hash length validation
        assert len(stamp["config_hash"]) == 64, f"config_hash should be 64 chars, got {len(stamp['config_hash'])}"
        assert len(stamp["grid_hash"]) == 64, f"grid_hash should be 64 chars, got {len(stamp['grid_hash'])}"
        
        # git_sha_short should be 7 chars or "n/a"
        git_sha = stamp["git_sha_short"]
        assert git_sha == "n/a" or len(git_sha) == 7, f"git_sha_short should be 'n/a' or 7 chars, got '{git_sha}'"
        
        # Optional fields (can be null)
        optional_fields = ["seed", "signal_path", "signal_hash"]
        for field in optional_fields:
            if field in stamp and stamp[field] is not None:
                assert isinstance(stamp[field], (str, int)), f"{field} should be string or int if present"
        
        print("✓ Sweep stamp contract test passed")
