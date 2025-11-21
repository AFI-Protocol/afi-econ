"""Test scores ingestion with BenchKit scores file."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from afi_econ_kit.scenarios import run_monte_carlo_simulation


def test_scores_ingestion_with_file():
    """Test simulation with --scores file produces expected changes."""
    # Load the test scores
    scores_path = Path("tests/fixtures/scores_min.json")
    assert scores_path.exists(), "Test scores fixture not found"
    
    with scores_path.open("r") as f:
        scores_data = json.load(f)
    
    # Prepare bench_data as it would be loaded by CLI
    from afi_econ_kit.scenarios import compute_file_sha256
    bench_data = {
        "scores": {
            "reputation": scores_data["reputation"]["score"],
            "poi": scores_data["poi"]["score"],
            "poinsight": scores_data["poinsight"]["score"]
        },
        "n": scores_data["n"],
        "warnings": [],
        "path": str(scores_path.resolve()),
        "hash": compute_file_sha256(scores_path),
        "benchkit_stamp": scores_data.get("stamp", None)
    }
    
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
    
    # Run without scores (baseline)
    result_no_scores = run_monte_carlo_simulation(config)
    
    # Run with scores
    result_with_scores = run_monte_carlo_simulation(config, bench_data)
    
    # Check that bench_merit is applied in diagnostics
    assert result_with_scores["epochs"][0]["gauge_diagnostics"]["bench_merit_applied"]
    assert not result_no_scores["epochs"][0]["gauge_diagnostics"]["bench_merit_applied"]

    # Check that gauge shares differ between runs
    epoch1_no_scores = result_no_scores["epochs"][0]["gauge_capped"]
    epoch1_with_scores = result_with_scores["epochs"][0]["gauge_capped"]
    
    # At least one role should have different allocation
    differences_found = False
    for role in epoch1_no_scores:
        if abs(epoch1_no_scores[role] - epoch1_with_scores[role]) > 1e-6:
            differences_found = True
            break
    
    assert differences_found, "BenchKit scores should affect gauge allocation"
    
    # Check stamp includes bench_merit data
    stamp = result_with_scores["stamp"]
    assert stamp["scores_path"] == str(scores_path.resolve())
    assert stamp["bench_merit"] is not None
    assert stamp["bench_merit"]["reputation"] == 0.58
    assert stamp["bench_merit"]["poi"] == 0.55
    assert stamp["bench_merit"]["poinsight"] == 0.60
    
    # Check that config and params hashes are present
    assert "config_hash" in stamp
    assert "params_hash" in stamp
    assert stamp["config_hash"] != "none"  # Should have computed a hash
    
    # With high poinsight (0.60), producers should get a boost
    # producers weight: 0.7 * poinsight + 0.3 * reputation = 0.7 * 0.60 + 0.3 * 0.58 = 0.594
    # This should increase producers allocation compared to baseline
    assert epoch1_with_scores["producers"] > epoch1_no_scores["producers"], \
        "High poinsight should boost producers allocation"


def test_cli_simulate_with_scores():
    """Test CLI simulate command with --scores parameter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        scores_path = Path("tests/fixtures/scores_min.json")
        
        # Run CLI command
        cmd = [
            sys.executable, "-m", "afi_econ_kit.cli", "simulate",
            "--config", "config.yaml",
            "--outdir", str(tmpdir_path),
            "--scores", str(scores_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check command succeeded
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        
        # Check output contains expected messages
        assert str(scores_path.resolve()) in result.stdout, "Should echo absolute scores path"
        assert "Using BenchKit scores:" in result.stdout, "Should print scores summary"
        assert "rep=0.580" in result.stdout, "Should show reputation score"
        assert "poi=0.550" in result.stdout, "Should show poi score"
        assert "poinsight=0.600" in result.stdout, "Should show poinsight score"
        assert "(n=20)" in result.stdout, "Should show n count"
        
        # Check econ_summary.json contains enriched fields
        summary_path = tmpdir_path / "econ_summary.json"
        assert summary_path.exists(), "Summary JSON should be created"
        
        with summary_path.open("r") as f:
            summary = json.load(f)
        
        stamp = summary["stamp"]
        assert stamp["scores_path"] == str(scores_path.resolve())
        assert stamp["bench_merit"]["reputation"] == 0.58
        assert "version" in stamp
        assert "config_hash" in stamp
        assert "params_hash" in stamp


if __name__ == "__main__":
    test_scores_ingestion_with_file()
    test_cli_simulate_with_scores()
