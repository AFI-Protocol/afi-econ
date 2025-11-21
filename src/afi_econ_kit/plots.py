"""Plotting utilities for AFI Econ Kit."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .data_io import IndexDataset, TimeseriesDataset

_PROVENANCE_FOOTER_Y = 0.02


@dataclass(frozen=True)
class Provenance:
    text: str


def get_git_short_hash() -> str:
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "n/a"
    return result.stdout.strip() or "n/a"


def build_provenance_text(config_hash: str) -> Provenance:
    commit = get_git_short_hash()
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    text = f"afi-econ-kit | git:{commit} cfg:{config_hash[:8]} | {timestamp}"
    return Provenance(text=text)


def draw_provenance(ax: plt.Axes, text: Provenance) -> None:
    ax.text(
        0.99,
        _PROVENANCE_FOOTER_Y,
        text.text,
        ha="right",
        va="bottom",
        fontsize=8,
        color="#555555",
        transform=ax.transAxes,
        alpha=0.8,
    )


def _finalise(fig: plt.Figure, output: Path) -> Path:
    fig.tight_layout()
    fig.savefig(output, dpi=240)
    plt.close(fig)
    return output


def plot_emission_by_epoch(ts: TimeseriesDataset, output_dir: Path, provenance: Provenance) -> Path:
    df = ts.data
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(df["epoch"], df["emission"], color="#005f73", linewidth=1.6)
    ax.set_title("Emissions by Epoch")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Emission")
    ax.grid(True, linestyle="--", alpha=0.4)
    draw_provenance(ax, provenance)
    return _finalise(fig, output_dir / "emissions_by_epoch.png")


def plot_cumulative_supply(ts: TimeseriesDataset, output_dir: Path, provenance: Provenance) -> Path:
    df = ts.data
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(df["epoch"], df["cum_supply"], color="#0a9396", linewidth=1.6)
    ax.set_title("Cumulative Supply")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Supply")
    ax.grid(True, linestyle="--", alpha=0.4)
    draw_provenance(ax, provenance)
    return _finalise(fig, output_dir / "cumulative_supply.png")


def plot_cumulative_fraction(
    ts: TimeseriesDataset,
    output_dir: Path,
    provenance: Provenance,
) -> Optional[Path]:
    if "cum_fraction" not in ts.data.columns:
        return None
    df = ts.data
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(df["epoch"], df["cum_fraction"], color="#ae2012", linewidth=1.6)
    ax.set_title("Cumulative Fraction of Supply")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Fraction of Cap")
    ax.grid(True, linestyle="--", alpha=0.4)
    draw_provenance(ax, provenance)
    return _finalise(fig, output_dir / "cumulative_fraction.png")


def plot_baseline_vs_actual_cum(
    ts: TimeseriesDataset,
    output_dir: Path,
    provenance: Provenance,
) -> Optional[Path]:
    if "baseline_cum" not in ts.data.columns:
        return None
    df = ts.data
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(df["epoch"], df["cum_supply"], label="Actual", color="#005f73", linewidth=1.6)
    ax.plot(df["epoch"], df["baseline_cum"], label="Baseline", color="#94d2bd", linewidth=1.6)
    ax.set_title("Baseline vs Actual Cumulative Supply")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Supply")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()
    draw_provenance(ax, provenance)
    return _finalise(fig, output_dir / "baseline_vs_actual_cum.png")


def _min_max(series: pd.Series) -> pd.Series:
    min_val = float(series.min())
    max_val = float(series.max())
    if np.isclose(min_val, max_val):
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - min_val) / (max_val - min_val)


def plot_index_components(idx: IndexDataset, output_dir: Path, provenance: Provenance) -> Path:
    df = idx.data.sort_values("epoch")
    components: list[str] = [col for col in ("AN_t", "EG_t", "Cov_t", "R_t") if col in df.columns]
    if not components:
        raise ValueError("Index dataset does not contain any component columns to plot.")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for col in components:
        ax.plot(df["epoch"], _min_max(df[col]), linewidth=1.5, label=col)
    ax.set_title("Index Components (Scaled)")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Scaled Value")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()
    draw_provenance(ax, provenance)
    return _finalise(fig, output_dir / "index_components.png")


def plot_index_series(idx: IndexDataset, output_dir: Path, provenance: Provenance) -> Path:
    df = idx.data.sort_values("epoch")
    fig, ax = plt.subplots(figsize=(9, 4.5))

    if "I_t" in df.columns:
        series = df["I_t"].astype(float)
        label = "I_t"
    elif all(col in df.columns for col in ("AN_t", "EG_t", "Cov_t", "R_t")):
        series = df["R_t"].astype(float) * (
            df["AN_t"].astype(float) + df["EG_t"].astype(float) + df["Cov_t"].astype(float)
        )
        label = "Composite I'_t"
    else:
        raise ValueError("Index dataset lacks I_t and sufficient components for composite series.")

    ax.plot(df["epoch"], series, color="#001219", linewidth=1.6, label=label)
    ax.set_title("Index Series")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Index Value")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()
    draw_provenance(ax, provenance)
    return _finalise(fig, output_dir / "index_series.png")


def plot_scenario_distributions(
    scen: pd.DataFrame,
    columns: Iterable[str],
    output_dir: Path,
    provenance: Provenance,
) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = plt.rcParams["axes.prop_cycle"].by_key().get("color", [])
    color_cycle = colors or ["#005f73", "#9b2226", "#0a9396", "#ca6702", "#bb3e03"]

    for idx_col, col in enumerate(columns):
        values = scen[col].dropna().astype(float)
        if values.empty:
            continue
        percentiles = np.percentile(values, [10, 50, 90])
        label = (
            f"{col} (p10={percentiles[0]:.2f}, p50={percentiles[1]:.2f}, p90={percentiles[2]:.2f})"
        )
        ax.hist(
            values,
            bins=40,
            density=True,
            alpha=0.35,
            color=color_cycle[idx_col % len(color_cycle)],
            label=label,
        )

    ax.set_title("Scenario Distributions")
    ax.set_xlabel("Value")
    ax.set_ylabel("Density")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper right", fontsize=8)
    draw_provenance(ax, provenance)
    return _finalise(fig, output_dir / "scenario_distributions.png")


def plot_scenario_totals(
    scen: pd.DataFrame,
    output_dir: Path,
    provenance: Provenance,
) -> Path:
    if "total_minted" not in scen.columns:
        raise ValueError("Scenario dataframe lacks 'total_minted' column required for totals plot.")
    values = scen["total_minted"].dropna().astype(float)
    if values.empty:
        raise ValueError("'total_minted' column contains no data to plot.")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(values, bins=50, color="#005f73", alpha=0.6, edgecolor="black")
    ax.set_title("Scenario Total Minted")
    ax.set_xlabel("Total Minted")
    ax.set_ylabel("Count")
    ax.grid(True, linestyle="--", alpha=0.4)

    sorted_vals = np.sort(values)
    ecdf = np.arange(1, len(sorted_vals) + 1, dtype=float) / len(sorted_vals)
    ax2 = ax.twinx()
    ax2.plot(sorted_vals, ecdf, color="#ae2012", linewidth=1.4, label="CDF")
    ax2.set_ylabel("CDF")
    ax2.set_ylim(0, 1)
    ax2.grid(False)
    ax2.legend(loc="lower right")

    draw_provenance(ax, provenance)
    return _finalise(fig, output_dir / "scenario_totals.png")
