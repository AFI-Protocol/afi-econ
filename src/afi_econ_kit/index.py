"""AFI Index computation module.

This module computes the AFI Index I_t based on:
- AN_t: Active Network metric (network participation)
- EG_t: Economic Growth metric (economic activity)
- Cov_t: Coverage metric (geographic/demographic coverage)
- I_t: Final AFI Index (weighted combination)
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


_COMPONENT_COLUMNS: List[str] = ["AN_t", "EG_t", "Cov_t"]


def validate_index_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Validate index dataframe has required columns."""
    if df.empty:
        raise ValueError("Index dataframe is empty; nothing to plot.")
    if "epoch" not in df.columns:
        raise ValueError("Index dataframe must include an 'epoch' column.")

    available_components = [col for col in _COMPONENT_COLUMNS if col in df.columns]
    if not available_components:
        raise ValueError(
            "Index dataframe missing required components. Expected one of: "
            + ", ".join(_COMPONENT_COLUMNS)
        )

    # Sort by epoch for deterministic plotting.
    return df.sort_values("epoch").reset_index(drop=True)


def compute_active_network_metric(receipts_data: pd.DataFrame, epoch: int) -> float:
    """Compute Active Network metric AN_t.

    Args:
        receipts_data: DataFrame with receipt data
        epoch: Current epoch number

    Returns:
        AN_t: Active network participation metric (0.0 to 1.0)
    """
    if receipts_data.empty:
        return 0.0

    # Count unique active participants
    unique_participants = receipts_data['participant_id'].nunique() if 'participant_id' in receipts_data.columns else len(receipts_data)

    # Compute activity rate (receipts per participant)
    total_receipts = len(receipts_data)
    activity_rate = total_receipts / max(unique_participants, 1)

    # Normalize to [0, 1] range using sigmoid-like function
    # AN_t = tanh(activity_rate / 10) to cap at reasonable levels
    an_t = np.tanh(activity_rate / 10.0)

    return float(an_t)


def compute_economic_growth_metric(payouts_data: pd.DataFrame, prev_payouts: Optional[pd.DataFrame] = None) -> float:
    """Compute Economic Growth metric EG_t.

    Args:
        payouts_data: DataFrame with current epoch payout data
        prev_payouts: DataFrame with previous epoch payout data (optional)

    Returns:
        EG_t: Economic growth metric (0.0 to 1.0)
    """
    if payouts_data.empty:
        return 0.0

    # Compute total payout value
    current_total = payouts_data['amount'].sum() if 'amount' in payouts_data.columns else len(payouts_data)

    if prev_payouts is None or prev_payouts.empty:
        # No previous data, use normalized current value
        eg_t = np.tanh(current_total / 1000.0)  # Normalize against expected scale
    else:
        # Compute growth rate
        prev_total = prev_payouts['amount'].sum() if 'amount' in prev_payouts.columns else len(prev_payouts)
        if prev_total > 0:
            growth_rate = (current_total - prev_total) / prev_total
            # Map growth rate to [0, 1] with sigmoid
            eg_t = 0.5 + 0.5 * np.tanh(growth_rate)  # Center at 0.5 for zero growth
        else:
            eg_t = np.tanh(current_total / 1000.0)

    return float(np.clip(eg_t, 0.0, 1.0))


def compute_coverage_metric(receipts_data: pd.DataFrame, target_coverage: float = 0.8) -> float:
    """Compute Coverage metric Cov_t.

    Args:
        receipts_data: DataFrame with receipt data
        target_coverage: Target coverage ratio (default 0.8)

    Returns:
        Cov_t: Coverage metric (0.0 to 1.0)
    """
    if receipts_data.empty:
        return 0.0

    # Compute geographic coverage if location data available
    if 'region' in receipts_data.columns:
        unique_regions = receipts_data['region'].nunique()
        total_regions = 10  # Assume 10 target regions
        geographic_coverage = min(unique_regions / total_regions, 1.0)
    else:
        geographic_coverage = 0.5  # Default moderate coverage

    # Compute role coverage if role data available
    if 'role' in receipts_data.columns:
        unique_roles = receipts_data['role'].nunique()
        total_roles = 4  # reputation, poi, poinsight, other
        role_coverage = min(unique_roles / total_roles, 1.0)
    else:
        role_coverage = 0.5  # Default moderate coverage

    # Combine coverage metrics
    cov_t = 0.6 * geographic_coverage + 0.4 * role_coverage

    return float(np.clip(cov_t, 0.0, 1.0))


def compute_afi_index(an_t: float, eg_t: float, cov_t: float,
                      weights: Optional[Dict[str, float]] = None) -> float:
    """Compute final AFI Index I_t.

    Args:
        an_t: Active Network metric
        eg_t: Economic Growth metric
        cov_t: Coverage metric
        weights: Optional custom weights (default: equal weighting)

    Returns:
        I_t: AFI Index (0.0 to 1.0)
    """
    if weights is None:
        weights = {"an": 0.4, "eg": 0.35, "cov": 0.25}

    # Validate weights sum to 1.0
    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > 1e-6:
        # Normalize weights
        weights = {k: v / weight_sum for k, v in weights.items()}

    # Compute weighted index
    i_t = (weights.get("an", 0.4) * an_t +
           weights.get("eg", 0.35) * eg_t +
           weights.get("cov", 0.25) * cov_t)

    return float(np.clip(i_t, 0.0, 1.0))


def compute_index_from_receipts(receipts_data: List[Dict[str, Any]],
                               payouts_data: List[Dict[str, Any]],
                               prev_payouts_data: Optional[List[Dict[str, Any]]] = None,
                               epoch: int = 1,
                               weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Compute AFI Index from receipt and payout data.

    Args:
        receipts_data: List of receipt dictionaries
        payouts_data: List of payout dictionaries
        prev_payouts_data: Optional previous epoch payout data
        epoch: Current epoch number
        weights: Optional custom index weights

    Returns:
        Dictionary with index computation results
    """
    # Convert to DataFrames
    receipts_df = pd.DataFrame(receipts_data) if receipts_data else pd.DataFrame()
    payouts_df = pd.DataFrame(payouts_data) if payouts_data else pd.DataFrame()
    prev_payouts_df = pd.DataFrame(prev_payouts_data) if prev_payouts_data else None

    # Compute component metrics
    an_t = compute_active_network_metric(receipts_df, epoch)
    eg_t = compute_economic_growth_metric(payouts_df, prev_payouts_df)
    cov_t = compute_coverage_metric(receipts_df)

    # Compute final index
    i_t = compute_afi_index(an_t, eg_t, cov_t, weights)

    return {
        "epoch": epoch,
        "components": {
            "AN_t": an_t,
            "EG_t": eg_t,
            "Cov_t": cov_t
        },
        "weights": weights or {"an": 0.4, "eg": 0.35, "cov": 0.25},
        "I_t": i_t,
        "metadata": {
            "receipts_count": len(receipts_data) if receipts_data else 0,
            "payouts_count": len(payouts_data) if payouts_data else 0,
            "unique_participants": receipts_df['participant_id'].nunique() if not receipts_df.empty and 'participant_id' in receipts_df.columns else 0
        }
    }


def create_index_stamp(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Create provenance stamp for index computation.

    Args:
        config_path: Optional path to config file for hashing

    Returns:
        Stamp dictionary with provenance information
    """
    from afi_econ_kit.scenarios import get_git_short_hash, _get_package_version, _compute_file_hash

    stamp = {
        "version": _get_package_version(),
        "git_sha": get_git_short_hash(),
        "utc_ts": datetime.now(timezone.utc).isoformat(),
        "module": "afi_econ_kit.index"
    }

    if config_path and Path(config_path).exists():
        stamp["config_hash"] = _compute_file_hash(config_path)

    return stamp


def save_index_results(results: Dict[str, Any], output_dir: Path,
                      stamp: Optional[Dict[str, Any]] = None) -> List[Path]:
    """Save index computation results to files.

    Args:
        results: Index computation results
        output_dir: Output directory path
        stamp: Optional provenance stamp

    Returns:
        List of saved file paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Add stamp to results
    if stamp:
        results["stamp"] = stamp

    # Save JSON results
    json_path = output_dir / "afi_index.json"
    with json_path.open("w") as f:
        json.dump(results, f, indent=2)

    saved_paths = [json_path]

    return saved_paths


def create_index_plot(results: Dict[str, Any], output_path: Path, title: str = "AFI Index") -> None:
    """Create AFI Index visualization plot.

    Args:
        results: Index computation results
        output_path: Path to save the plot
        title: Plot title
    """
    import matplotlib.pyplot as plt
    import os

    # Environment stabilization for deterministic plotting
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["TZ"] = "UTC"
    os.environ["PYTHONHASHSEED"] = "0"

    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    # Extract data
    epoch = results["epoch"]
    components = results["components"]
    i_t = results["I_t"]
    weights = results["weights"]

    # Plot 1: Component metrics
    component_names = ["AN_t", "EG_t", "Cov_t"]
    component_values = [components[name] for name in component_names]
    component_colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

    bars = ax1.bar(component_names, component_values, color=component_colors, alpha=0.7)
    ax1.set_ylim(0, 1)
    ax1.set_ylabel("Metric Value")
    ax1.set_title(f"AFI Index Components (Epoch {epoch})")
    ax1.grid(True, alpha=0.3)

    # Add value labels on bars
    for bar, value in zip(bars, component_values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{value:.3f}', ha='center', va='bottom')

    # Plot 2: Final index with weights
    ax2.bar(["AFI Index"], [i_t], color="#d62728", alpha=0.7, width=0.5)
    ax2.set_ylim(0, 1)
    ax2.set_ylabel("Index Value")
    ax2.set_title(f"Final AFI Index: {i_t:.3f}")
    ax2.grid(True, alpha=0.3)

    # Add weight information as text
    weight_text = f"Weights: AN={weights['an']:.2f}, EG={weights['eg']:.2f}, Cov={weights['cov']:.2f}"
    ax2.text(0, i_t + 0.05, weight_text, ha='center', va='bottom', fontsize=10)

    # Add value label
    ax2.text(0, i_t + 0.01, f'{i_t:.3f}', ha='center', va='bottom', fontweight='bold')

    # Add footer
    version = results.get("stamp", {}).get("version", "unknown")
    fig.text(0.99, 0.01, f"AFI Econ Kit {version}", ha='right', va='bottom',
             fontsize=8, alpha=0.7)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()