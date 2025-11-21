"""Command-line interface for AFI Econ Kit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from .config import Config, config_hash, load_config
from .data_io import IndexDataset, TimeseriesDataset, load_index, load_scenarios, load_timeseries
from .emissions import assert_bounds_aim, assert_monotone_cum_supply
from .plots import (
    Provenance,
    build_provenance_text,
    plot_baseline_vs_actual_cum,
    plot_cumulative_fraction,
    plot_cumulative_supply,
    plot_emission_by_epoch,
    plot_index_components,
    plot_index_series,
    plot_scenario_distributions,
    plot_scenario_totals,
)
from .scenarios import run_monte_carlo_simulation, save_simulation_outputs
from .gauge import allocation_gauge, compute_merit_inputs
from .safety import apply_safety_controls
from .payouts import compute_epoch_payouts

_SCENARIO_DIST_COLUMNS: tuple[str, ...] = ("avgMult", "y33", "y80", "y100", "total_minted")
_SUMMARY_METRICS: tuple[str, ...] = ("count", "mean", "std", "min", "p10", "p50", "p90", "max")


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--timeseries", dest="timeseries_csv", type=str)
    parser.add_argument("--scenarios", dest="scenarios_csv", type=str)
    parser.add_argument("--index", dest="index_csv", type=str)
    parser.add_argument("--output-dir", dest="output_dir", type=str)


def _collect_overrides(args: argparse.Namespace) -> dict[str, Optional[str]]:
    overrides: dict[str, Optional[str]] = {}
    for key in ("timeseries_csv", "scenarios_csv", "index_csv", "output_dir"):
        value = getattr(args, key, None)
        if value:
            overrides[key] = value
    return overrides


def _ensure_output_dir(path: str) -> Path:
    output_path = Path(path)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def _format_mapping(title: str, mapping: dict[str, str]) -> None:
    print(title)
    for logical in sorted(mapping):
        print(f"  {logical:>15} -> {mapping[logical]}")


def _timeseries_for_command(args: argparse.Namespace) -> tuple[Config, TimeseriesDataset]:
    overrides = _collect_overrides(args)
    config = load_config(args.config, overrides=overrides)
    ts = load_timeseries(config)
    return config, ts


def _index_for_command(args: argparse.Namespace) -> tuple[Config, Optional[IndexDataset]]:
    overrides = _collect_overrides(args)
    config = load_config(args.config, overrides=overrides)
    idx = load_index(config)
    return config, idx


def _scenarios_for_command(args: argparse.Namespace) -> tuple[Config, Optional[pd.DataFrame]]:
    overrides = _collect_overrides(args)
    config = load_config(args.config, overrides=overrides)
    scen = load_scenarios(config)
    return config, scen


def cmd_check(args: argparse.Namespace) -> int:
    config, ts = _timeseries_for_command(args)
    ts_df = ts.data

    assert_monotone_cum_supply(ts_df)
    try:
        assert_bounds_aim(ts_df)
    except ValueError as exc:
        print(f"AIM bounds check skipped: {exc}")

    _format_mapping("Timeseries column mapping:", ts.resolved)
    print(f"Timeseries rows: {len(ts_df)}")

    idx: Optional[IndexDataset] = load_index(config)
    if idx is not None:
        _format_mapping("Index columns detected:", idx.resolved)
        print(f"Index rows: {len(idx.data)}")
    else:
        print("Index data: not provided or unavailable.")

    print("check: OK")
    return 0


def _provenance(config: Config) -> Provenance:
    digest = config_hash(config)
    return build_provenance_text(digest)


def _print_saved(paths: Iterable[Path]) -> None:
    for path in paths:
        print(path.resolve())


def cmd_plot(args: argparse.Namespace) -> int:
    config, ts = _timeseries_for_command(args)
    output_dir = _ensure_output_dir(config.output_dir)
    provenance = _provenance(config)

    saved: list[Path] = []
    saved.append(plot_emission_by_epoch(ts, output_dir, provenance))
    saved.append(plot_cumulative_supply(ts, output_dir, provenance))

    optional = [
        plot_cumulative_fraction(ts, output_dir, provenance),
        plot_baseline_vs_actual_cum(ts, output_dir, provenance),
    ]
    for maybe in optional:
        if maybe is not None:
            saved.append(maybe)

    _print_saved(saved)
    print("plot: OK")
    return 0


def cmd_plot_index(args: argparse.Namespace) -> int:
    config, idx = _index_for_command(args)
    if idx is None:
        raise FileNotFoundError("Index CSV not provided; cannot generate index plots.")

    output_dir = _ensure_output_dir(config.output_dir)
    provenance = _provenance(config)

    saved: list[Path] = []
    try:
        saved.append(plot_index_components(idx, output_dir, provenance))
    except ValueError as exc:
        print(f"Index components skipped: {exc}")

    try:
        saved.append(plot_index_series(idx, output_dir, provenance))
    except ValueError as exc:
        print(f"Index series skipped: {exc}")

    if not saved:
        raise ValueError("No index plots were generated; check index CSV columns.")
    _print_saved(saved)
    print("plot-index: OK")
    return 0


def _scenario_columns(df: pd.DataFrame) -> list[str]:
    columns: list[str] = [col for col in _SCENARIO_DIST_COLUMNS if col in df.columns]
    if not columns:
        raise ValueError(
            "Scenario CSV does not contain any of the expected summary columns: "
            f"{_SCENARIO_DIST_COLUMNS}. Available: {list(df.columns)}"
        )
    return columns


def cmd_plot_scenarios(args: argparse.Namespace) -> int:
    config, scen = _scenarios_for_command(args)
    if scen is None:
        raise FileNotFoundError("Scenario CSV not provided; cannot generate scenario plots.")

    columns = _scenario_columns(scen)
    output_dir = _ensure_output_dir(config.output_dir)
    provenance = _provenance(config)

    saved = [
        plot_scenario_distributions(scen, columns, output_dir, provenance),
        plot_scenario_totals(scen, output_dir, provenance),
    ]
    _print_saved(saved)
    print("plot-scenarios: OK")
    return 0


def _format_metric(metric: str, value: float) -> str:
    if metric == "count":
        return f"{int(value)}"
    return f"{value:.3f}"


def _summary_table(df: pd.DataFrame, columns: Iterable[str]) -> tuple[str, list[str]]:
    present_columns = [col for col in columns if col in df.columns]
    if not present_columns:
        raise ValueError("No matching columns available for scenario summary table.")

    stats: dict[str, dict[str, float]] = {col: {} for col in present_columns}
    for col in present_columns:
        series = df[col].dropna().astype(float)
        if series.empty:
            continue
        stats[col]["count"] = float(len(series))
        stats[col]["mean"] = float(series.mean())
        stats[col]["std"] = float(series.std(ddof=1)) if len(series) > 1 else 0.0
        stats[col]["min"] = float(series.min())
        percentiles = np.percentile(series, [10, 50, 90])
        stats[col]["p10"], stats[col]["p50"], stats[col]["p90"] = (float(x) for x in percentiles)
        stats[col]["max"] = float(series.max())

    header = ["metric", *present_columns]
    rows = ["| " + " | ".join(header) + " |"]
    rows.append("| " + " | ".join(["---"] * len(header)) + " |")

    for metric in _SUMMARY_METRICS:
        row = [metric]
        for col in present_columns:
            value = stats[col].get(metric)
            row.append(_format_metric(metric, value) if value is not None else "-")
        rows.append("| " + " | ".join(row) + " |")

    return "\n".join(rows) + "\n", present_columns


def cmd_summarize_scenarios(args: argparse.Namespace) -> int:
    config, scen = _scenarios_for_command(args)
    if scen is None:
        raise FileNotFoundError("Scenario CSV not provided; cannot summarise scenarios.")

    table, columns = _summary_table(scen, _SCENARIO_DIST_COLUMNS)
    print(table, end="")

    output_dir = _ensure_output_dir(config.output_dir)
    summary_path = output_dir / "scenarios_summary.md"
    summary_path.write_text(table, encoding="utf-8")
    print(summary_path.resolve())
    print("summarize-scenarios: OK")
    return 0


def _load_econ_config(args: argparse.Namespace) -> Dict[str, Any]:
    """Load economic configuration from YAML file."""
    import yaml

    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError(f"Expected mapping in config file: {config_path}")

    return config


def _load_benchkit_scores(scores_path: Optional[str]) -> Optional[Dict[str, Any]]:
    """Load and validate BenchKit scores JSON file.

    Args:
        scores_path: Path to scores JSON file, or None

    Returns:
        Dictionary with validated scores, or None if no file provided
    """
    if not scores_path:
        return None

    import json

    scores_file = Path(scores_path)
    if not scores_file.exists():
        raise FileNotFoundError(f"Scores file not found: {scores_path}")

    try:
        with scores_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in scores file {scores_path}: {e}")

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in scores file: {scores_path}")

    # Validate required reputation score
    if "reputation" not in data or not isinstance(data["reputation"], dict):
        raise ValueError(f"Missing 'reputation' object in scores file: {scores_path}")

    if "score" not in data["reputation"]:
        raise ValueError(f"Missing 'reputation.score' in scores file: {scores_path}")

    # Extract and validate scores, clipping to [0,1]
    bench_merit = {}
    warnings = []

    for component in ["reputation", "poi", "poinsight"]:
        if component in data and isinstance(data[component], dict) and "score" in data[component]:
            score = data[component]["score"]
            if isinstance(score, (int, float)):
                clipped_score = max(0.0, min(1.0, float(score)))
                bench_merit[component] = clipped_score
                if clipped_score != score:
                    warnings.append(f"{component}.score clipped from {score} to {clipped_score}")
            else:
                warnings.append(f"{component}.score is not numeric, using default 0.5")
                bench_merit[component] = 0.5
        else:
            warnings.append(f"Missing {component}.score, using default 0.5")
            bench_merit[component] = 0.5

    # Extract n if available
    n = data.get("n", 0)
    if not isinstance(n, int):
        n = 0

    # Compute scores file hash for provenance
    from afi_econ_kit.scenarios import compute_file_sha256
    scores_hash = compute_file_sha256(scores_file)

    # Extract BenchKit stamp if present (pass-through)
    benchkit_stamp = data.get("stamp", None)

    return {
        "scores": bench_merit,
        "n": n,
        "warnings": warnings,
        "path": str(scores_file.resolve()),
        "hash": scores_hash,
        "benchkit_stamp": benchkit_stamp
    }


def _load_budget_data(budget_path: str) -> dict:
    """Load AFI emissions budget and compute hash.

    Returns:
        dict: Budget data with provenance fields
    """
    if not budget_path:
        return {
            "budget": None,
            "path": None,
            "hash": None,
            "stamp": None
        }

    import json
    from pathlib import Path
    from afi_econ_kit.scenarios import compute_file_sha256

    budget_file = Path(budget_path)
    if not budget_file.exists():
        raise FileNotFoundError(f"Budget file not found: {budget_path}")

    # Compute hash of the budget file
    budget_hash = compute_file_sha256(budget_file)

    # Load budget data
    with budget_file.open("r") as f:
        budget_data = json.load(f)

    # Validate required schema fields
    required_fields = ["epoch", "B_t", "AIM", "E_t"]
    for field in required_fields:
        if field not in budget_data:
            raise ValueError(f"Budget file missing required field: {field}")

    # Extract budget stamp if present
    budget_stamp = budget_data.get("stamp", {})

    return {
        "budget": budget_data,
        "path": str(budget_file.resolve()),
        "hash": budget_hash,
        "stamp": budget_stamp
    }


def cmd_econ_simulate(args: argparse.Namespace) -> int:
    """Run economic Monte Carlo simulation."""
    config = _load_econ_config(args)
    output_dir = _ensure_output_dir(args.outdir)

    # Load BenchKit scores if provided
    bench_data = _load_benchkit_scores(getattr(args, 'scores', None))

    if bench_data:
        # Echo absolute path to scores file
        print(f"Scores file: {bench_data['path']}")

        # Print summary line with hash
        scores = bench_data['scores']
        hash_short = bench_data['hash'][:8] if bench_data['hash'] != "none" else "none"
        print(f"Using BenchKit scores: rep={scores['reputation']:.3f}, "
              f"poi={scores['poi']:.3f}, poinsight={scores['poinsight']:.3f} "
              f"(n={bench_data['n']}) hash={hash_short}")

        # Print warnings if any
        for warning in bench_data['warnings']:
            print(f"Warning: {warning}")

    # Load AFI emissions budget if provided
    budget_data = _load_budget_data(getattr(args, 'budget', None))

    if budget_data['budget']:
        # Echo absolute path to budget file
        print(f"Budget file: {budget_data['path']}")

        # Print summary line with hash
        budget = budget_data['budget']
        hash_short = budget_data['hash'][:8] if budget_data['hash'] else "none"
        # Handle both 'factor' and 'm_t' field names for AIM multiplier
        aim_multiplier = budget['AIM'].get('factor', budget['AIM'].get('m_t', 1.0))
        print(f"Using AFI budget: epoch={budget['epoch']}, "
              f"B_t={budget['B_t']:.2f}, E_t={budget['E_t']:.2f}, "
              f"AIM={aim_multiplier:.3f} hash={hash_short}")

    print(f"Running economic simulation with {config['monte_carlo']['runs']} epochs...")

    # Run simulation with bench_data and budget_data
    results = run_monte_carlo_simulation(config, bench_data, budget_data)

    # Save outputs
    saved_paths = save_simulation_outputs(results, output_dir)

    # Print absolute paths
    _print_saved(saved_paths)

    print("econ simulate: OK")
    return 0


def cmd_econ_replay(args: argparse.Namespace) -> int:
    """Replay single epoch with provided data."""
    import json

    config = _load_econ_config(args)
    output_dir = _ensure_output_dir(args.outdir)

    # Load BenchKit scores if provided
    bench_data = _load_benchkit_scores(getattr(args, 'scores', None))

    if bench_data:
        # Echo absolute path to scores file
        print(f"Scores file: {bench_data['path']}")

        # Print summary line with hash
        scores = bench_data['scores']
        hash_short = bench_data['hash'][:8] if bench_data['hash'] != "none" else "none"
        print(f"Using BenchKit scores: rep={scores['reputation']:.3f}, "
              f"poi={scores['poi']:.3f}, poinsight={scores['poinsight']:.3f} "
              f"(n={bench_data['n']}) hash={hash_short}")

        # Print warnings if any
        for warning in bench_data['warnings']:
            print(f"Warning: {warning}")

    # Load AFI emissions budget if provided
    budget_data = _load_budget_data(getattr(args, 'budget', None))

    if budget_data['budget']:
        # Echo absolute path to budget file
        print(f"Budget file: {budget_data['path']}")

        # Print summary line with hash
        budget = budget_data['budget']
        hash_short = budget_data['hash'][:8] if budget_data['hash'] else "none"
        print(f"Using AFI budget: epoch={budget['epoch']}, "
              f"B_t={budget['B_t']:.2f}, E_t={budget['E_t']:.2f}, "
              f"AIM={budget['AIM']['factor']:.3f} hash={hash_short}")

    # Load input data
    receipts_df = pd.read_csv(args.receipts)
    credits_df = pd.read_csv(args.credits)

    with open(args.prev_state, "r") as f:
        prev_state = json.load(f)

    print("Replaying single epoch...")

    # Compute merit inputs
    merit = compute_merit_inputs(receipts_df)

    # Apply allocation gauge with bench_data
    gauge_config = config["gauge"]
    gauge_result = allocation_gauge(
        weights=gauge_config["weights"],
        caps=gauge_config["caps"],
        merit=merit,
        blend=gauge_config["policy_merit_blend"],
        bench_merit=bench_data['scores'] if bench_data else None
    )

    # Prepare new state
    budget = config["budget"]["baseline"]
    new_state = {
        "epoch": prev_state.get("epoch", 0) + 1,
        "budget": budget,
        "weights": gauge_result["capped"],
        "metrics": {
            "dispute_rate": 0.05,  # Would be computed from actual data
            "network_load": 0.7
        }
    }

    # Apply safety controls
    safe_state = apply_safety_controls(prev_state, new_state, config["safety"])

    # Group credits by role (assuming role column exists)
    role_credits = {}
    if "role" in credits_df.columns:
        for role in config["gauge"]["weights"].keys():
            role_credits[role] = credits_df[credits_df["role"] == role]
    else:
        # If no role column, distribute evenly
        roles = list(config["gauge"]["weights"].keys())
        n_per_role = len(credits_df) // len(roles)
        for i, role in enumerate(roles):
            start_idx = i * n_per_role
            end_idx = start_idx + n_per_role if i < len(roles) - 1 else len(credits_df)
            role_credits[role] = credits_df.iloc[start_idx:end_idx].copy()

    # Compute payouts
    payout_results = compute_epoch_payouts(
        budget=safe_state["budget"],
        aim_config=config["budget"],
        gauge_shares=safe_state["weights"],
        role_credits=role_credits,
        maturity_hold_frac=config["payouts"]["maturity_hold_frac"]
    )

    # Save next state
    state_next_path = output_dir / "state_next.json"
    with open(state_next_path, "w") as f:
        json.dump(safe_state, f, indent=2)

    # Save epoch payouts
    payouts_data = []
    for role, payouts_df in payout_results["payouts"].items():
        if not payouts_df.empty:
            payouts_df_copy = payouts_df.copy()
            payouts_df_copy["role"] = role
            payouts_data.append(payouts_df_copy)

    if payouts_data:
        all_payouts = pd.concat(payouts_data, ignore_index=True)
        payouts_path = output_dir / "payouts_epoch.csv"
        all_payouts.to_csv(payouts_path, index=False)
        saved_paths = [state_next_path, payouts_path]
    else:
        saved_paths = [state_next_path]

    # Print absolute paths
    _print_saved(saved_paths)

    print("econ replay: OK")
    return 0


def cmd_econ_index(args: argparse.Namespace) -> int:
    """Compute AFI Index from receipts and payouts data."""
    import json
    from pathlib import Path
    from afi_econ_kit.index import (
        compute_index_from_receipts,
        create_index_stamp,
        save_index_results,
        create_index_plot
    )

    output_dir = _ensure_output_dir(args.outdir)

    # Load receipts data
    receipts_path = Path(args.receipts)
    if not receipts_path.exists():
        print(f"Error: Receipts file not found: {args.receipts}", file=sys.stderr)
        return 1

    with receipts_path.open("r") as f:
        receipts_data = json.load(f)

    # Load payouts data (optional)
    payouts_data = []
    if hasattr(args, 'payouts') and args.payouts:
        payouts_path = Path(args.payouts)
        if payouts_path.exists():
            with payouts_path.open("r") as f:
                payouts_data = json.load(f)
        else:
            print(f"Warning: Payouts file not found: {args.payouts}")

    # Load previous payouts data (optional)
    prev_payouts_data = None
    if hasattr(args, 'prev_payouts') and args.prev_payouts:
        prev_payouts_path = Path(args.prev_payouts)
        if prev_payouts_path.exists():
            with prev_payouts_path.open("r") as f:
                prev_payouts_data = json.load(f)
        else:
            print(f"Warning: Previous payouts file not found: {args.prev_payouts}")

    # Extract epoch from args or default
    epoch = getattr(args, 'epoch', 1)

    print(f"Computing AFI Index for epoch {epoch}...")
    print(f"Receipts: {len(receipts_data)} records")
    print(f"Payouts: {len(payouts_data)} records")

    # Compute index
    results = compute_index_from_receipts(
        receipts_data=receipts_data,
        payouts_data=payouts_data,
        prev_payouts_data=prev_payouts_data,
        epoch=epoch
    )

    # Create stamp
    stamp = create_index_stamp()

    # Save results
    saved_paths = save_index_results(results, output_dir, stamp)

    # Create plot
    plot_path = output_dir / "afi_index.png"
    create_index_plot(results, plot_path)
    saved_paths.append(plot_path)

    # Print absolute paths
    _print_saved(saved_paths)

    # Print summary
    components = results["components"]
    i_t = results["I_t"]
    print(f"AFI Index: {i_t:.3f} (AN_t={components['AN_t']:.3f}, EG_t={components['EG_t']:.3f}, Cov_t={components['Cov_t']:.3f})")

    print("econ index: OK")
    return 0


def cmd_econ_gauge(args: argparse.Namespace) -> int:
    """Run gauge allocation stage."""
    import json
    from pathlib import Path
    from afi_econ_kit.gauge import compute_gauge_shares
    from afi_econ_kit.scenarios import create_stamp

    output_dir = _ensure_output_dir(args.outdir)

    # Load receipts
    receipts_path = Path(args.receipts)
    if not receipts_path.exists():
        print(f"Error: Receipts file not found: {args.receipts}", file=sys.stderr)
        return 1

    with receipts_path.open("r") as f:
        receipts_data = json.load(f)

    # Load scores if provided
    bench_data = None
    if hasattr(args, 'scores') and args.scores:
        bench_data = _load_benchkit_scores(args.scores)

    # Load config
    config_path = Path(args.config)
    if config_path.exists():
        import yaml
        with config_path.open("r") as f:
            config = yaml.safe_load(f)
    else:
        config = {}  # Use defaults

    print(f"Running gauge allocation...")
    print(f"Receipts: {len(receipts_data)} records")
    if bench_data and bench_data['scores']:
        print(f"BenchKit scores: {len(bench_data['scores'])} participants")

    # Compute gauge shares
    gauge_results = compute_gauge_shares(receipts_data, config, bench_data)

    # Create stamp
    stamp = create_stamp(42, "gauge_stage", args.config, bench_data=bench_data)

    # Save results
    results = {
        "allocations": gauge_results,
        "metadata": {
            "receipts_count": len(receipts_data),
            "config_path": args.config
        },
        "stamp": stamp
    }

    json_path = output_dir / "gauge_allocations.json"
    with json_path.open("w") as f:
        json.dump(results, f, indent=2)

    _print_saved([json_path])
    print(f"Gauge allocations computed for {len(gauge_results)} participants")
    print("econ gauge: OK")
    return 0


def cmd_econ_safety(args: argparse.Namespace) -> int:
    """Run safety smoothing stage."""
    import json
    from pathlib import Path
    from afi_econ_kit.safety import apply_safety_smoothing
    from afi_econ_kit.scenarios import create_stamp

    output_dir = _ensure_output_dir(args.outdir)

    # Load current allocations
    allocations_path = Path(args.allocations)
    if not allocations_path.exists():
        print(f"Error: Allocations file not found: {args.allocations}", file=sys.stderr)
        return 1

    with allocations_path.open("r") as f:
        allocations_data = json.load(f)

    current_allocations = allocations_data.get("allocations", allocations_data)

    # Load previous allocations if provided
    prev_allocations = None
    if hasattr(args, 'prev_allocations') and args.prev_allocations:
        prev_path = Path(args.prev_allocations)
        if prev_path.exists():
            with prev_path.open("r") as f:
                prev_data = json.load(f)
            prev_allocations = prev_data.get("allocations", prev_data)

    # Load config
    config_path = Path(args.config)
    if config_path.exists():
        import yaml
        with config_path.open("r") as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    print(f"Running safety smoothing...")
    print(f"Current allocations: {len(current_allocations)} participants")
    if prev_allocations:
        print(f"Previous allocations: {len(prev_allocations)} participants")

    # Apply safety smoothing
    smoothed_allocations = apply_safety_smoothing(current_allocations, prev_allocations, config)

    # Create stamp
    stamp = create_stamp(42, "safety_stage", args.config)

    # Save results
    results = {
        "smoothed_allocations": smoothed_allocations,
        "metadata": {
            "current_count": len(current_allocations),
            "previous_count": len(prev_allocations) if prev_allocations else 0,
            "config_path": args.config
        },
        "stamp": stamp
    }

    json_path = output_dir / "safety_allocations.json"
    with json_path.open("w") as f:
        json.dump(results, f, indent=2)

    _print_saved([json_path])
    print(f"Safety smoothing applied to {len(smoothed_allocations)} participants")
    print("econ safety: OK")
    return 0


def cmd_econ_payouts(args: argparse.Namespace) -> int:
    """Run payouts distribution stage."""
    import json
    from pathlib import Path
    from afi_econ_kit.payouts import compute_payouts
    from afi_econ_kit.scenarios import create_stamp

    output_dir = _ensure_output_dir(args.outdir)

    # Load allocations
    allocations_path = Path(args.allocations)
    if not allocations_path.exists():
        print(f"Error: Allocations file not found: {args.allocations}", file=sys.stderr)
        return 1

    with allocations_path.open("r") as f:
        allocations_data = json.load(f)

    allocations = allocations_data.get("smoothed_allocations", allocations_data.get("allocations", allocations_data))

    # Load budget if provided
    budget_data = None
    total_pool = args.pool
    if hasattr(args, 'budget') and args.budget:
        budget_data = _load_budget_data(args.budget)
        if budget_data['budget']:
            total_pool = budget_data['budget']['E_t']
            print(f"Using budget pool: {total_pool}")

    print(f"Running payouts distribution...")
    print(f"Allocations: {len(allocations)} participants")
    print(f"Total pool: {total_pool}")

    # Compute payouts
    payouts_list = compute_payouts(allocations, total_pool)

    # Create stamp
    stamp = create_stamp(42, "payouts_stage", budget_data=budget_data)

    # Save results
    results = {
        "payouts": payouts_list,
        "total_distributed": sum(p["amount"] for p in payouts_list),
        "metadata": {
            "allocations_count": len(allocations),
            "total_pool": total_pool
        },
        "stamp": stamp
    }

    json_path = output_dir / "final_payouts.json"
    with json_path.open("w") as f:
        json.dump(results, f, indent=2)

    _print_saved([json_path])
    print(f"Payouts computed for {len(payouts_list)} participants")
    print(f"Total distributed: {results['total_distributed']:.2f}")
    print("econ payouts: OK")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AFI Economic Kit CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_check = subparsers.add_parser("check", help="Validate CSV inputs")
    _add_common_options(parser_check)
    parser_check.set_defaults(func=cmd_check)

    parser_plot = subparsers.add_parser("plot", help="Generate timeseries figures")
    _add_common_options(parser_plot)
    parser_plot.set_defaults(func=cmd_plot)

    parser_index = subparsers.add_parser("plot-index", help="Generate index figures")
    _add_common_options(parser_index)
    parser_index.set_defaults(func=cmd_plot_index)

    parser_plot_scenarios = subparsers.add_parser(
        "plot-scenarios", help="Generate scenario summary figures"
    )
    _add_common_options(parser_plot_scenarios)
    parser_plot_scenarios.set_defaults(func=cmd_plot_scenarios)

    parser_summary = subparsers.add_parser(
        "summarize-scenarios", help="Summarise scenario statistics"
    )
    _add_common_options(parser_summary)
    parser_summary.set_defaults(func=cmd_summarize_scenarios)

    # Economic simulation commands
    parser_simulate = subparsers.add_parser("simulate", help="Run economic Monte Carlo simulation")
    parser_simulate.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser_simulate.add_argument("--outdir", type=str, required=True, help="Output directory")
    parser_simulate.add_argument("--scores", type=str, help="BenchKit scores JSON file (optional)")
    parser_simulate.add_argument("--budget", type=str, help="AFI emissions budget JSON file (optional)")
    parser_simulate.set_defaults(func=cmd_econ_simulate)

    parser_replay = subparsers.add_parser("replay", help="Replay single economic epoch")
    parser_replay.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser_replay.add_argument("--receipts", type=str, required=True, help="Receipts CSV file")
    parser_replay.add_argument("--credits", type=str, required=True, help="Credits CSV file")
    parser_replay.add_argument("--prev-state", type=str, required=True, help="Previous state JSON file")
    parser_replay.add_argument("--outdir", type=str, required=True, help="Output directory")
    parser_replay.add_argument("--scores", type=str, help="BenchKit scores JSON file (optional)")
    parser_replay.add_argument("--budget", type=str, help="AFI emissions budget JSON file (optional)")
    parser_replay.set_defaults(func=cmd_econ_replay)

    parser_index = subparsers.add_parser("index", help="Compute AFI Index from receipts and payouts")
    parser_index.add_argument("--receipts", type=str, required=True, help="Receipts JSON file")
    parser_index.add_argument("--payouts", type=str, help="Payouts JSON file (optional)")
    parser_index.add_argument("--prev-payouts", type=str, help="Previous epoch payouts JSON file (optional)")
    parser_index.add_argument("--epoch", type=int, default=1, help="Epoch number (default: 1)")
    parser_index.add_argument("--outdir", type=str, required=True, help="Output directory")
    parser_index.set_defaults(func=cmd_econ_index)

    parser_gauge = subparsers.add_parser("gauge", help="Run gauge allocation stage")
    parser_gauge.add_argument("--receipts", type=str, required=True, help="Receipts JSON file")
    parser_gauge.add_argument("--config", type=str, default="params/gauge_v0.yaml", help="Gauge config file")
    parser_gauge.add_argument("--scores", type=str, help="BenchKit scores JSON file (optional)")
    parser_gauge.add_argument("--outdir", type=str, required=True, help="Output directory")
    parser_gauge.set_defaults(func=cmd_econ_gauge)

    parser_safety = subparsers.add_parser("safety", help="Run safety smoothing stage")
    parser_safety.add_argument("--allocations", type=str, required=True, help="Current allocations JSON file")
    parser_safety.add_argument("--prev-allocations", type=str, help="Previous allocations JSON file (optional)")
    parser_safety.add_argument("--config", type=str, default="params/gauge_v0.yaml", help="Safety config file")
    parser_safety.add_argument("--outdir", type=str, required=True, help="Output directory")
    parser_safety.set_defaults(func=cmd_econ_safety)

    parser_payouts = subparsers.add_parser("payouts", help="Run payouts distribution stage")
    parser_payouts.add_argument("--allocations", type=str, required=True, help="Final allocations JSON file")
    parser_payouts.add_argument("--budget", type=str, help="Budget JSON file (optional)")
    parser_payouts.add_argument("--pool", type=float, default=1000.0, help="Total payout pool (default: 1000.0)")
    parser_payouts.add_argument("--outdir", type=str, required=True, help="Output directory")
    parser_payouts.set_defaults(func=cmd_econ_payouts)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # pragma: no cover
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
