"""Data loading helpers with flexible column resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd

from .config import Config


@dataclass(frozen=True)
class TimeseriesDataset:
    data: pd.DataFrame
    resolved: Dict[str, str]
    source: Path


@dataclass(frozen=True)
class IndexDataset:
    data: pd.DataFrame
    resolved: Dict[str, str]
    source: Path


_TIMESERIES_SYNONYMS: Dict[str, list[str]] = {
    "epoch": ["epoch", "epoch_id"],
    "emission": ["e_t", "emission", "emissions", "issuance"],
    "aim": ["aim", "aim_t", "aimmult", "mult_aim", "aim_multiplier"],
    "cum_supply": ["s_t", "minted", "cumulative", "cum_supply", "supply_cum"],
    "cum_fraction": ["cum_frac", "minted_frac", "fractional_supply"],
    "baseline_cum": ["cum_base", "baseline_cum", "baseline_cumulative"],
    "year": ["year", "calendar_year"],
}

_INDEX_SYNONYMS: Dict[str, list[str]] = {
    "epoch": ["epoch", "epoch_id"],
    "AN_t": ["AN_t", "AN", "an"],
    "EG_t": ["EG_t", "EG", "eg"],
    "Cov_t": ["Cov_t", "Cov", "cov"],
    "R_t": ["R_t", "R", "reliability"],
    "I_t": ["I_t", "index", "impact"],
}


def _normalise(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _match_column(columns: Iterable[str], target: Optional[str]) -> Optional[str]:
    if not target:
        return None
    target_norm = _normalise(target)
    for col in columns:
        if col == target:
            return col
    for col in columns:
        if col.lower() == target.lower():
            return col
    for col in columns:
        if _normalise(col) == target_norm and target_norm:
            return col
    return None


def _resolve_column(
    df: pd.DataFrame,
    logical: str,
    mapping: Dict[str, str],
    synonyms: Dict[str, list[str]],
) -> Optional[str]:
    # 1) explicit mapping from config
    explicit = mapping.get(logical)
    match = _match_column(df.columns, explicit)
    if match:
        return match

    # 2) per-logical synonyms
    for candidate in synonyms.get(logical, []):
        match = _match_column(df.columns, candidate)
        if match:
            return match

    # 3) fall back to logical name direct
    return _match_column(df.columns, logical)


def _resolve_columns(
    df: pd.DataFrame,
    mapping: Dict[str, str],
    required: Iterable[str],
    optional: Iterable[str],
    synonyms: Dict[str, list[str]],
    *,
    context: str,
) -> Dict[str, str]:
    resolved: Dict[str, str] = {}
    missing: list[str] = []
    for logical in required:
        column = _resolve_column(df, logical, mapping, synonyms)
        if column is None:
            missing.append(logical)
        else:
            resolved[logical] = column

    for logical in optional:
        column = _resolve_column(df, logical, mapping, synonyms)
        if column is not None:
            resolved[logical] = column

    if missing:
        details = []
        for logical in missing:
            expected = mapping.get(logical)
            synonym_list = synonyms.get(logical, [])
            candidates = [c for c in [expected, logical, *synonym_list] if c]
            details.append(f"{logical} (expected like: {', '.join(dict.fromkeys(candidates))})")
        raise ValueError(
            f"Missing required {context} column(s): {', '.join(details)}. "
            f"Available columns: {list(df.columns)}"
        )

    return resolved


def _compute_robust_cum_supply(ts: pd.DataFrame) -> None:
    """Compute robust cumulative supply from emission data with multipliers.

    This function ensures cum_supply is derived from per-epoch increments
    and is strictly non-decreasing, even if the original data has issues.
    """
    # Compute final per-epoch emission after all multipliers
    emission = ts["emission"].astype(float)

    # Apply multipliers if they exist
    mult_aim = ts.get("mult_aim", 1.0)
    mult_ce = ts.get("mult_ce", 1.0)
    mult_all = ts.get("mult_all", 1.0)

    emission_final = (emission * mult_aim * mult_ce * mult_all)
    emission_final = emission_final.fillna(0.0).clip(lower=0.0)

    # Store the final emission for reference
    ts["emission_final"] = emission_final

    # Compute cumulative supply from the final emissions
    ts["cum_supply"] = emission_final.cumsum()

    # Guardrail: enforce monotone non-decreasing even if future code introduces edge cases
    vals = ts["cum_supply"].to_numpy(dtype=float, copy=False)
    np.maximum.accumulate(vals, out=vals)
    ts["cum_supply"] = vals


def load_timeseries(config: Config) -> TimeseriesDataset:
    path = Path(config.timeseries_csv)
    if not path.exists():
        raise FileNotFoundError(f"Timeseries CSV not found: {path}")

    df = pd.read_csv(path)
    resolved = _resolve_columns(
        df,
        mapping=config.columns,
        required=("epoch", "emission", "aim", "cum_supply", "year"),
        optional=("cum_fraction", "baseline_cum"),
        synonyms=_TIMESERIES_SYNONYMS,
        context="timeseries",
    )

    rename_map = {actual: logical for logical, actual in resolved.items()}
    canonical = df.rename(columns=rename_map).copy()

    # Robust cumulative supply derivation
    _compute_robust_cum_supply(canonical)

    return TimeseriesDataset(data=canonical, resolved=resolved, source=path)


def load_index(config: Config) -> Optional[IndexDataset]:
    if not config.index_csv:
        return None
    path = Path(config.index_csv)
    if not path.exists():
        return None

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Index CSV {path} is empty; no data to plot.")

    resolved = _resolve_columns(
        df,
        mapping={},  # index uses intrinsic column names
        required=("epoch",),
        optional=("AN_t", "EG_t", "Cov_t", "R_t", "I_t"),
        synonyms=_INDEX_SYNONYMS,
        context="index",
    )

    rename_map = {actual: logical for logical, actual in resolved.items()}
    canonical = df.rename(columns=rename_map).copy()
    return IndexDataset(data=canonical, resolved=resolved, source=path)


def load_scenarios(config: Config) -> Optional[pd.DataFrame]:
    if not config.scenarios_csv:
        return None
    path = Path(config.scenarios_csv)
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Scenario CSV {path} is empty; unable to summarise.")
    return df


from typing import Tuple
import numpy as np
import pandas as pd

def compute_emission_and_cum_guarded(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """
    Returns (emission_increments, cum_supply_guarded).

    Increment source preference:
      1) 'E_t' if present (epoch pool increments),
      2) else 'emission' if present (treated as increments),
      3) else 'budget' if present (budget per epoch),
      4) else 'total_pool' if present (pool per epoch),
      else raises ValueError.

    Effective increments = increments * mult_aim * mult_ce * mult_all (default 1.0 if missing).
    Negative/NaNs are clipped to 0.0, then cumsum, then np.maximum.accumulate to guarantee monotonicity.
    """
    inc_col = None
    for candidate in ["E_t", "emission", "budget", "total_pool"]:
        if candidate in df.columns:
            inc_col = candidate
            break

    if inc_col is None:
        raise ValueError("Could not locate an emission-like column (expected 'E_t', 'emission', 'budget', or 'total_pool').")

    inc = pd.to_numeric(df[inc_col], errors="coerce").fillna(0.0)
    for m in ("mult_aim", "mult_ce", "mult_all"):
        if m in df.columns:
            inc = inc * pd.to_numeric(df[m], errors="coerce").fillna(1.0)

    inc = inc.fillna(0.0).clip(lower=0.0)
    cum = inc.cumsum()
    cum_guard = pd.Series(np.maximum.accumulate(cum.to_numpy()), index=cum.index)
    return inc, cum_guard
