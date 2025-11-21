"""Configuration loading utilities for AFI Econ Kit."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


_DEFAULT_COLUMNS: Dict[str, str] = {
    "epoch": "epoch",
    "emission": "E_t",
    "aim": "AIM_t",
    "cum_supply": "S_t",
    "cum_fraction": "cum_frac",
    "baseline_cum": "cum_base",
    "year": "year",
    "scenario": "scenario",
    "scenario_emissions": "emissions",
}


@dataclass
class Config:
    """Runtime configuration for loading data and generating figures."""

    timeseries_csv: str
    scenarios_csv: str
    index_csv: Optional[str] = None
    output_dir: str = "./figures"
    columns: Dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_COLUMNS))


def _read_yaml(path: Optional[Path]) -> Dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in config file: {path}")
    return data


def _merge_columns(base: Dict[str, str], overrides: Optional[Dict[str, str]]) -> Dict[str, str]:
    merged = dict(base)
    if overrides:
        merged.update({str(k): str(v) for k, v in overrides.items()})
    return merged


def load_config(
    config_path: Optional[Path] = None,
    *,
    overrides: Optional[Dict[str, Optional[str]]] = None,
) -> Config:
    """Load configuration, applying CLI overrides where supplied."""

    yaml_data = _read_yaml(config_path)
    overrides = overrides or {}

    timeseries_csv = overrides.get("timeseries_csv") or yaml_data.get("timeseries_csv")
    scenarios_csv = overrides.get("scenarios_csv") or yaml_data.get("scenarios_csv")

    if not timeseries_csv:
        raise ValueError("timeseries_csv must be provided via config or CLI override")
    if not scenarios_csv:
        raise ValueError("scenarios_csv must be provided via config or CLI override")

    index_csv = overrides.get("index_csv")
    if index_csv is None:
        index_csv = yaml_data.get("index_csv")

    output_dir = overrides.get("output_dir") or yaml_data.get("output_dir") or "./figures"

    columns_from_yaml = yaml_data.get("columns") if isinstance(yaml_data.get("columns"), dict) else None
    columns = _merge_columns(_DEFAULT_COLUMNS, columns_from_yaml)
    columns_override = overrides.get("columns")
    if isinstance(columns_override, dict):
        columns = _merge_columns(columns, columns_override)

    return Config(
        timeseries_csv=str(timeseries_csv),
        scenarios_csv=str(scenarios_csv),
        index_csv=str(index_csv) if index_csv else None,
        output_dir=str(output_dir),
        columns=columns,
    )


def config_hash(config: Config) -> str:
    """Compute a stable SHA256 hash from the configuration contents."""

    payload = asdict(config)
    payload["columns"] = dict(sorted(payload["columns"].items()))
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
