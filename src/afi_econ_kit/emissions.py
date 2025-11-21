"""Sanity checks for emissions data."""

from __future__ import annotations

import numpy as np
import pandas as pd


def assert_monotone_cum_supply(ts: pd.DataFrame, column: str = "cum_supply") -> None:
    """Ensure cumulative supply S_t is non-decreasing."""

    if column not in ts.columns:
        raise ValueError(f"Column '{column}' not found for cumulative supply check.")
    values = ts[column].to_numpy(dtype=float)
    diffs = np.diff(values)
    if np.any(diffs < -1e-9):
        drop_idx = int(np.where(diffs < -1e-9)[0][0])
        prev_val = values[drop_idx]
        next_val = values[drop_idx + 1]
        raise ValueError(
            "Cumulative supply is not monotone non-decreasing: "
            f"row {drop_idx} -> {drop_idx + 1} ({prev_val} > {next_val})."
        )


def assert_bounds_aim(
    ts: pd.DataFrame,
    *,
    aim_column: str = "aim",
    amin: float | None = None,
    amax: float | None = None,
) -> None:
    """Ensure AIM_t stays within bounds when bounds are available."""

    if aim_column not in ts.columns:
        raise ValueError(f"Column '{aim_column}' not found for AIM bound check.")

    candidate_bounds = {
        "amin": amin,
        "amax": amax,
    }
    for col in ("amin", "AIM_min", "aim_min"):
        if candidate_bounds["amin"] is None and col in ts.columns:
            candidate_bounds["amin"] = float(ts[col].min())
    for col in ("amax", "AIM_max", "aim_max"):
        if candidate_bounds["amax"] is None and col in ts.columns:
            candidate_bounds["amax"] = float(ts[col].max())

    lower = candidate_bounds["amin"]
    upper = candidate_bounds["amax"]

    if lower is None or upper is None:
        return  # Not enough information; skip check gracefully.

    values = ts[aim_column].to_numpy(dtype=float)
    under = values < lower - 1e-9
    over = values > upper + 1e-9
    if under.any() or over.any():
        idx_under = int(np.where(under)[0][0]) if under.any() else None
        idx_over = int(np.where(over)[0][0]) if over.any() else None
        if idx_under is not None:
            raise ValueError(
                f"AIM_t below lower bound {lower} at row {idx_under}: {values[idx_under]}"
            )
        if idx_over is not None:
            raise ValueError(
                f"AIM_t above upper bound {upper} at row {idx_over}: {values[idx_over]}"
            )
