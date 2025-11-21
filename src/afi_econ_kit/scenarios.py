"""Scenarios module for AFI Economic Kit.

This module implements deterministic Monte Carlo scenarios for economic simulation.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from .gauge import allocation_gauge, compute_merit_inputs
from .safety import apply_safety_controls, circuit_breaker
from .payouts import compute_epoch_payouts
from .plots import get_git_short_hash


def _compute_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of a file."""
    import hashlib
    from pathlib import Path

    try:
        path = Path(file_path)
        if not path.exists():
            return "none"

        with path.open("rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return "none"


def compute_file_sha256(path: Path) -> str:
    """Compute SHA256 hash of a file using streaming for large files.

    Args:
        path: Path to file

    Returns:
        64-character hex digest or "none" if file doesn't exist/error
    """
    import hashlib

    try:
        if not path.exists():
            return "none"

        sha256_hash = hashlib.sha256()
        with path.open("rb") as f:
            # Read in chunks for memory efficiency
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception:
        return "none"


def _get_package_version() -> str:
    """Get package version from metadata."""
    try:
        import importlib.metadata
        return importlib.metadata.version("afi-econ-kit")
    except Exception:
        return "unknown"


def create_stamp(seed: int, data_hash: str, config_path: str = "config.yaml",
                 params_path: str = "params/gauge_v0.yaml", bench_data: Optional[Dict[str, Any]] = None,
                 budget_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a comprehensive reproducibility stamp.

    Args:
        seed: Random seed used
        data_hash: Hash of input data
        config_path: Path to config file for hashing
        params_path: Path to params file for hashing
        bench_data: Optional BenchKit data
        budget_data: Optional AFI emissions budget data

    Returns:
        Stamp dictionary with comprehensive provenance information
    """
    return {
        # Original fields (preserved for compatibility)
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_short_hash": get_git_short_hash(),
        "seed": seed,
        "data_hash": data_hash,

        # New comprehensive provenance fields
        "version": _get_package_version(),
        "git_sha_short": get_git_short_hash(),  # Alias for consistency
        "utc_ts": datetime.now(timezone.utc).isoformat(),
        "config_hash": _compute_file_hash(config_path),
        "params_hash": _compute_file_hash(params_path),
        "rng_seed_used": seed,
        "scores_path": bench_data['path'] if bench_data else None,
        "scores_hash": bench_data['hash'] if bench_data else None,
        "benchkit_stamp": bench_data['benchkit_stamp'] if bench_data else None,
        "bench_merit": bench_data['scores'] if bench_data else None,
        "budget_path": budget_data['path'] if budget_data and budget_data['budget'] else None,
        "budget_hash": budget_data['hash'] if budget_data and budget_data['budget'] else None,
        "budget_stamp": budget_data['stamp'] if budget_data and budget_data['budget'] else None,
        "budget_epoch": budget_data['budget']['epoch'] if budget_data and budget_data['budget'] else None
    }


def synthesize_receipts(epoch: int, rng: np.random.Generator, n_receipts: int = 100) -> pd.DataFrame:
    """Synthesize receipt data for an epoch.
    
    Args:
        epoch: Current epoch number
        rng: Random number generator
        n_receipts: Number of receipts to generate
        
    Returns:
        DataFrame with synthetic receipt data
    """
    receipts = []
    
    for i in range(n_receipts):
        receipt = {
            "receipt_id": f"epoch_{epoch}_receipt_{i}",
            "epoch": epoch,
            "confidence": rng.uniform(0.3, 1.0),
            "novelty_score": rng.uniform(0.0, 1.0),
            "attestation_correct": rng.choice([0, 1], p=[0.2, 0.8]),  # 80% correct
            "response_time": rng.exponential(2.0),  # Exponential distribution
            "role": rng.choice(["producers", "enrichment", "validators", "public_goods"])
        }
        receipts.append(receipt)
    
    return pd.DataFrame(receipts)


def synthesize_credits(receipts_df: pd.DataFrame, rng: np.random.Generator) -> Dict[str, pd.DataFrame]:
    """Synthesize credit data from receipts.
    
    Args:
        receipts_df: Receipt data
        rng: Random number generator
        
    Returns:
        Dictionary mapping role to credits DataFrame
    """
    role_credits = {}
    
    for role in ["producers", "enrichment", "validators", "public_goods"]:
        role_receipts = receipts_df[receipts_df["role"] == role]
        
        if role_receipts.empty:
            role_credits[role] = pd.DataFrame(columns=["participant_id", "credits"])
            continue
        
        # Generate participants for this role
        n_participants = max(1, len(role_receipts) // 3)  # Roughly 3 receipts per participant
        participants = [f"{role}_participant_{i}" for i in range(n_participants)]
        
        credits_data = []
        for participant in participants:
            # Credits based on performance metrics
            base_credits = rng.uniform(10, 100)
            performance_bonus = rng.uniform(0.8, 1.2)
            credits = base_credits * performance_bonus
            
            credits_data.append({
                "participant_id": participant,
                "credits": credits
            })
        
        role_credits[role] = pd.DataFrame(credits_data)
    
    return role_credits


def run_epoch_simulation(
    epoch: int,
    config: Dict[str, Any],
    prev_state: Dict[str, Any],
    rng: np.random.Generator,
    bench_data: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Run simulation for a single epoch.

    Args:
        epoch: Current epoch number
        config: Full configuration
        prev_state: Previous epoch state
        rng: Random number generator
        bench_data: Optional BenchKit scores data

    Returns:
        Tuple of (new_state, epoch_results)
    """
    # Synthesize data for this epoch
    receipts_df = synthesize_receipts(epoch, rng)
    role_credits = synthesize_credits(receipts_df, rng)
    
    # Compute merit inputs
    merit = compute_merit_inputs(receipts_df)
    
    # Apply allocation gauge
    gauge_config = config["gauge"]

    # Load bench merit weights from params if available
    bench_merit_weights = None
    if bench_data:
        # Try to load from params file
        try:
            import yaml
            from pathlib import Path
            params_path = Path("params") / f"gauge_{gauge_config.get('version', 'v0')}.yaml"
            if params_path.exists():
                with params_path.open("r", encoding="utf-8") as f:
                    params = yaml.safe_load(f)
                    bench_merit_weights = params.get("bench_merit_weights")
        except Exception:
            # Fall back to defaults if params loading fails
            pass

    gauge_result = allocation_gauge(
        weights=gauge_config["weights"],
        caps=gauge_config["caps"],
        merit=merit,
        blend=gauge_config["policy_merit_blend"],
        bench_merit=bench_data['scores'] if bench_data else None,
        bench_merit_weights=bench_merit_weights
    )
    
    # Prepare new state
    budget = config["budget"]["baseline"]
    new_state = {
        "epoch": epoch,
        "budget": budget,
        "weights": gauge_result["capped"],
        "metrics": {
            "dispute_rate": rng.uniform(0.0, 0.15),  # Synthetic dispute rate
            "network_load": rng.uniform(0.3, 1.0)
        }
    }
    
    # Apply safety controls
    safe_state = apply_safety_controls(prev_state, new_state, config["safety"])
    
    # Compute payouts
    payout_results = compute_epoch_payouts(
        budget=safe_state["budget"],
        aim_config=config["budget"],
        gauge_shares=safe_state["weights"],
        role_credits=role_credits,
        maturity_hold_frac=config["payouts"]["maturity_hold_frac"]
    )
    
    # Prepare epoch results
    epoch_results = {
        "epoch": epoch,
        "receipts_count": len(receipts_df),
        "merit": merit,
        "gauge_raw": gauge_result["raw"],
        "gauge_capped": gauge_result["capped"],
        "gauge_diagnostics": gauge_result["diag"],
        "safety_applied": safe_state.get("circuit_breaker", {"tripped": False}),
        "payouts": payout_results
    }
    
    return safe_state, epoch_results


def run_monte_carlo_simulation(config: Dict[str, Any], bench_data: Optional[Dict[str, Any]] = None,
                               budget_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run full Monte Carlo simulation.

    Args:
        config: Full configuration dictionary
        bench_data: Optional BenchKit scores data
        budget_data: Optional AFI emissions budget data

    Returns:
        Complete simulation results
    """
    mc_config = config["monte_carlo"]
    n_runs = mc_config["runs"]
    seed = mc_config["seed"]
    
    # Initialize random number generator
    rng = np.random.default_rng(seed)
    
    # Initialize results storage
    all_epochs = []
    budget_series = []
    gauge_series = []
    breaker_events = []
    
    # Initial state
    prev_state = {
        "epoch": 0,
        "budget": config["budget"]["baseline"],
        "weights": config["gauge"]["weights"],
        "metrics": {"dispute_rate": 0.0, "network_load": 0.5},
        "smoothed_metrics": {"dispute_rate": 0.0, "network_load": 0.5}
    }
    
    # Run simulation epochs
    for epoch in range(1, n_runs + 1):
        state, results = run_epoch_simulation(epoch, config, prev_state, rng, bench_data)
        
        all_epochs.append(results)
        
        # Track series data
        budget_series.append({
            "epoch": epoch,
            "budget": state["budget"],
            "total_pool": results["payouts"]["total_pool"],
            "total_payouts": results["payouts"]["summary"]["total_payouts"]
        })
        
        # Track gauge shares
        gauge_entry = {"epoch": epoch}
        gauge_entry.update(state["weights"])
        gauge_series.append(gauge_entry)
        
        # Track breaker events
        if state.get("circuit_breaker", {}).get("tripped", False):
            breaker_events.append({
                "epoch": epoch,
                "reason": state["circuit_breaker"]["reason"],
                "triggered_metrics": state["circuit_breaker"]["triggered_metrics"]
            })
        
        prev_state = state
    
    # Create summary
    summary = {
        "total_epochs": n_runs,
        "total_breaker_events": len(breaker_events),
        "final_budget": prev_state["budget"],
        "avg_pool_utilization": np.mean([
            ep["payouts"]["summary"]["utilization"] for ep in all_epochs
        ])
    }
    
    # Create stamp
    data_hash = f"mc_{seed}_{n_runs}"  # Simple hash for reproducibility
    gauge_version = config["gauge"].get("version", "v0")
    params_path = f"params/gauge_{gauge_version}.yaml"
    stamp = create_stamp(seed, data_hash, "config.yaml", params_path, bench_data, budget_data)
    
    return {
        "config": config,
        "stamp": stamp,
        "summary": summary,
        "epochs": all_epochs,
        "series": {
            "budget": budget_series,
            "gauge": gauge_series,
            "breaker_events": breaker_events
        }
    }


def plot_budget_series(budget_series: List[Dict], output_dir: Path, stamp: Dict[str, Any]) -> Path:
    """Plot budget and pool evolution over time.

    Args:
        budget_series: List of budget data per epoch
        output_dir: Output directory for plots
        stamp: Reproducibility stamp

    Returns:
        Path to saved plot
    """
    df = pd.DataFrame(budget_series)

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(df["epoch"], df["budget"], label="Budget", linewidth=2)
    ax.plot(df["epoch"], df["total_pool"], label="Total Pool", linewidth=2)
    ax.plot(df["epoch"], df["total_payouts"], label="Total Payouts", linewidth=2)

    ax.set_xlabel("Epoch")
    ax.set_ylabel("Amount")
    ax.set_title("Economic Budget Evolution")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add provenance footer
    if not os.environ.get("AFI_ECON_GOLDEN_TEST"):
        footer_text = f"afi-econ-kit | git:{stamp['git_short_hash']} | {stamp['timestamp']}"
        ax.text(0.99, 0.02, footer_text, transform=ax.transAxes,
                ha="right", va="bottom", fontsize=8, alpha=0.7)

    plt.tight_layout()

    output_path = output_dir / "econ_budget.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    return output_path


def plot_gauge_shares(gauge_series: List[Dict], output_dir: Path, stamp: Dict[str, Any]) -> Path:
    """Plot gauge share evolution over time.

    Args:
        gauge_series: List of gauge data per epoch
        output_dir: Output directory for plots
        stamp: Reproducibility stamp

    Returns:
        Path to saved plot
    """
    df = pd.DataFrame(gauge_series)

    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot each role's share
    roles = [col for col in df.columns if col != "epoch"]
    for role in roles:
        ax.plot(df["epoch"], df[role], label=role.title(), linewidth=2)

    ax.set_xlabel("Epoch")
    ax.set_ylabel("Share")
    ax.set_title("Gauge Share Evolution")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1)

    # Add provenance footer
    if not os.environ.get("AFI_ECON_GOLDEN_TEST"):
        footer_text = f"afi-econ-kit | git:{stamp['git_short_hash']} | {stamp['timestamp']}"
        ax.text(0.99, 0.02, footer_text, transform=ax.transAxes,
                ha="right", va="bottom", fontsize=8, alpha=0.7)

    plt.tight_layout()

    output_path = output_dir / "econ_gauge_shares.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    return output_path


def plot_breaker_events(breaker_events: List[Dict], output_dir: Path, stamp: Dict[str, Any]) -> Path:
    """Plot circuit breaker events over time.

    Args:
        breaker_events: List of breaker events
        output_dir: Output directory for plots
        stamp: Reproducibility stamp

    Returns:
        Path to saved plot
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    if breaker_events:
        epochs = [event["epoch"] for event in breaker_events]
        reasons = [event["reason"] for event in breaker_events]

        # Simple scatter plot of breaker events
        ax.scatter(epochs, [1] * len(epochs), c="red", s=50, alpha=0.7)

        # Add reason annotations for first few events
        for i, (epoch, reason) in enumerate(zip(epochs[:5], reasons[:5])):
            ax.annotate(reason[:20] + "...", (epoch, 1),
                       xytext=(5, 5), textcoords="offset points", fontsize=8)

    ax.set_xlabel("Epoch")
    ax.set_ylabel("Breaker Events")
    ax.set_title("Circuit Breaker Events")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 2)

    if not breaker_events:
        ax.text(0.5, 0.5, "No breaker events", transform=ax.transAxes,
                ha="center", va="center", fontsize=12, alpha=0.5)

    # Add provenance footer
    if not os.environ.get("AFI_ECON_GOLDEN_TEST"):
        footer_text = f"afi-econ-kit | git:{stamp['git_short_hash']} | {stamp['timestamp']}"
        ax.text(0.99, 0.02, footer_text, transform=ax.transAxes,
                ha="right", va="bottom", fontsize=8, alpha=0.7)

    plt.tight_layout()

    output_path = output_dir / "econ_breakers.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    return output_path


def save_simulation_outputs(results: Dict[str, Any], output_dir: Path) -> List[Path]:
    """Save all simulation outputs to files.

    Args:
        results: Complete simulation results
        output_dir: Output directory

    Returns:
        List of paths to saved files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = []

    # Save CSV files
    budget_df = pd.DataFrame(results["series"]["budget"])

    from afi_econ_kit.data_io import compute_emission_and_cum_guarded

    budget_df = budget_df.copy()
    _emission_incr, _cum_guard = compute_emission_and_cum_guarded(budget_df)
    budget_df["emission"] = _emission_incr.values
    budget_df["cum_supply"] = _cum_guard.values

    budget_path = output_dir / "econ_pool_series.csv"
    budget_df.to_csv(budget_path, index=False)
    saved_paths.append(budget_path)

    gauge_df = pd.DataFrame(results["series"]["gauge"])
    gauge_path = output_dir / "econ_gauge_series.csv"
    gauge_df.to_csv(gauge_path, index=False)
    saved_paths.append(gauge_path)

    # Save payouts summary
    payouts_summary = []
    for epoch_result in results["epochs"]:
        epoch = epoch_result["epoch"]
        payout_summary = epoch_result["payouts"]["summary"]
        payout_summary["epoch"] = epoch
        payouts_summary.append(payout_summary)

    payouts_df = pd.DataFrame(payouts_summary)
    payouts_path = output_dir / "econ_payouts_summary.csv"
    payouts_df.to_csv(payouts_path, index=False)
    saved_paths.append(payouts_path)

    # Save JSON summary
    summary_data = {
        "stamp": results["stamp"],
        "summary": results["summary"],
        "config_hash": hash(str(results["config"]))  # Simple config hash
    }
    summary_path = output_dir / "econ_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary_data, f, indent=2)
    saved_paths.append(summary_path)

    # Save plots
    saved_paths.append(plot_budget_series(results["series"]["budget"], output_dir, results["stamp"]))
    saved_paths.append(plot_gauge_shares(results["series"]["gauge"], output_dir, results["stamp"]))
    saved_paths.append(plot_breaker_events(results["series"]["breaker_events"], output_dir, results["stamp"]))

    return saved_paths
