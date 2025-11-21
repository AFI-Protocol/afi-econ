"""Smoke tests for CLI simulate command - check artifacts exist and paths are absolute."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest


def test_cli_simulate_smoke():
    """Test that simulate command produces expected artifacts."""
    config_path = Path("config.yaml")
    assert config_path.exists(), "config.yaml must exist for test"
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "test_output"
        
        # Find the CLI executable
        executable = shutil.which("afi-econ-kit")
        if executable:
            cmd = [executable, "simulate", "--config", str(config_path), "--outdir", str(output_dir)]
        else:
            cmd = [sys.executable, "-m", "afi_econ_kit.cli", "simulate", "--config", str(config_path), "--outdir", str(output_dir)]
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Check command succeeded
        assert result.returncode == 0, f"Command failed: {result.stderr or result.stdout}"
        
        # Check that expected files were created
        expected_files = [
            "econ_pool_series.csv",
            "econ_gauge_series.csv", 
            "econ_payouts_summary.csv",
            "econ_summary.json",
            "econ_budget.png",
            "econ_gauge_shares.png",
            "econ_breakers.png"
        ]
        
        for filename in expected_files:
            file_path = output_dir / filename
            assert file_path.exists(), f"Expected file not created: {filename}"
            assert file_path.stat().st_size > 0, f"File is empty: {filename}"
        
        # Check that absolute paths were printed
        output_lines = result.stdout.strip().split('\n')
        printed_paths = [line for line in output_lines if line.startswith('/')]
        
        assert len(printed_paths) >= len(expected_files), "Not all absolute paths were printed"
        
        # Verify paths are absolute
        for path_str in printed_paths:
            path = Path(path_str)
            assert path.is_absolute(), f"Path is not absolute: {path_str}"


def test_cli_simulate_json_schema():
    """Test that JSON output has expected structure."""
    config_path = Path("config.yaml")
    assert config_path.exists(), "config.yaml must exist for test"
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "test_output"
        
        # Find the CLI executable
        executable = shutil.which("afi-econ-kit")
        if executable:
            cmd = [executable, "simulate", "--config", str(config_path), "--outdir", str(output_dir)]
        else:
            cmd = [sys.executable, "-m", "afi_econ_kit.cli", "simulate", "--config", str(config_path), "--outdir", str(output_dir)]
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f"Command failed: {result.stderr or result.stdout}"
        
        # Load and validate JSON
        json_path = output_dir / "econ_summary.json"
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Check required top-level keys
        required_keys = ["stamp", "summary", "config_hash"]
        for key in required_keys:
            assert key in data, f"Missing key in JSON: {key}"
        
        # Check stamp structure
        stamp = data["stamp"]
        stamp_keys = ["timestamp", "git_short_hash", "seed", "data_hash"]
        for key in stamp_keys:
            assert key in stamp, f"Missing stamp key: {key}"
        
        # Check summary structure
        summary = data["summary"]
        summary_keys = ["total_epochs", "total_breaker_events", "final_budget", "avg_pool_utilization"]
        for key in summary_keys:
            assert key in summary, f"Missing summary key: {key}"
        
        # Validate data types
        assert isinstance(summary["total_epochs"], int)
        assert isinstance(summary["total_breaker_events"], int)
        assert isinstance(summary["final_budget"], (int, float))
        assert isinstance(summary["avg_pool_utilization"], (int, float))


def test_cli_simulate_csv_structure():
    """Test that CSV outputs have expected structure."""
    config_path = Path("config.yaml")
    assert config_path.exists(), "config.yaml must exist for test"
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "test_output"
        
        # Find the CLI executable
        executable = shutil.which("afi-econ-kit")
        if executable:
            cmd = [executable, "simulate", "--config", str(config_path), "--outdir", str(output_dir)]
        else:
            cmd = [sys.executable, "-m", "afi_econ_kit.cli", "simulate", "--config", str(config_path), "--outdir", str(output_dir)]
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f"Command failed: {result.stderr or result.stdout}"
        
        # Check pool series CSV
        import pandas as pd
        
        pool_df = pd.read_csv(output_dir / "econ_pool_series.csv")
        expected_pool_columns = ["epoch", "budget", "total_pool", "total_payouts"]
        for col in expected_pool_columns:
            assert col in pool_df.columns, f"Missing column in pool series: {col}"
        
        assert len(pool_df) > 0, "Pool series CSV is empty"
        
        # Check gauge series CSV
        gauge_df = pd.read_csv(output_dir / "econ_gauge_series.csv")
        expected_gauge_columns = ["epoch", "producers", "enrichment", "validators", "public_goods"]
        for col in expected_gauge_columns:
            assert col in gauge_df.columns, f"Missing column in gauge series: {col}"
        
        assert len(gauge_df) > 0, "Gauge series CSV is empty"
        
        # Check payouts summary CSV
        payouts_df = pd.read_csv(output_dir / "econ_payouts_summary.csv")
        expected_payout_columns = ["epoch", "total_pool", "total_payouts", "total_holdbacks", "utilization"]
        for col in expected_payout_columns:
            assert col in payouts_df.columns, f"Missing column in payouts summary: {col}"
        
        assert len(payouts_df) > 0, "Payouts summary CSV is empty"


def test_cli_simulate_missing_config():
    """Test simulate command with missing config file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "test_output"
        missing_config = Path(temp_dir) / "missing.yaml"
        
        # Find the CLI executable
        executable = shutil.which("afi-econ-kit")
        if executable:
            cmd = [executable, "simulate", "--config", str(missing_config), "--outdir", str(output_dir)]
        else:
            cmd = [sys.executable, "-m", "afi_econ_kit.cli", "simulate", "--config", str(missing_config), "--outdir", str(output_dir)]
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        # Should fail with non-zero exit code
        assert result.returncode != 0, "Command should fail with missing config"
        assert "not found" in result.stderr.lower() or "not found" in result.stdout.lower()


def test_cli_simulate_creates_output_dir():
    """Test that simulate command creates output directory if it doesn't exist."""
    config_path = Path("config.yaml")
    assert config_path.exists(), "config.yaml must exist for test"
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Use nested path that doesn't exist
        output_dir = Path(temp_dir) / "nested" / "output" / "dir"
        assert not output_dir.exists(), "Output dir should not exist initially"
        
        # Find the CLI executable
        executable = shutil.which("afi-econ-kit")
        if executable:
            cmd = [executable, "simulate", "--config", str(config_path), "--outdir", str(output_dir)]
        else:
            cmd = [sys.executable, "-m", "afi_econ_kit.cli", "simulate", "--config", str(config_path), "--outdir", str(output_dir)]
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Check command succeeded
        assert result.returncode == 0, f"Command failed: {result.stderr or result.stdout}"
        
        # Check that output directory was created
        assert output_dir.exists(), "Output directory was not created"
        assert output_dir.is_dir(), "Output path is not a directory"
        
        # Check that files were created in the directory
        files = list(output_dir.glob("*"))
        assert len(files) > 0, "No files created in output directory"


@pytest.mark.slow
def test_cli_simulate_performance():
    """Test that simulate command completes in reasonable time."""
    config_path = Path("config.yaml")
    assert config_path.exists(), "config.yaml must exist for test"
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "test_output"
        
        # Find the CLI executable
        executable = shutil.which("afi-econ-kit")
        if executable:
            cmd = [executable, "simulate", "--config", str(config_path), "--outdir", str(output_dir)]
        else:
            cmd = [sys.executable, "-m", "afi_econ_kit.cli", "simulate", "--config", str(config_path), "--outdir", str(output_dir)]
        
        # Run with timeout - should complete within 30 seconds
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # If we get here without timeout, the performance is acceptable
        assert result.returncode == 0, f"Command failed: {result.stderr or result.stdout}"
