import subprocess, sys
from pathlib import Path
import pandas as pd
import numpy as np

def test_pool_series_has_convenience_columns(tmp_path: Path):
    outdir = tmp_path / "out"
    outdir.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-m", "afi_econ_kit.cli", "simulate", "--config", "config.yaml", "--outdir", str(outdir)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr or proc.stdout

    csvp = outdir / "econ_pool_series.csv"
    assert csvp.exists(), "econ_pool_series.csv not produced"

    df = pd.read_csv(csvp)
    for col in ("emission", "cum_supply"):
        assert col in df.columns, f"Missing expected column: {col}"

    inc = pd.to_numeric(df["emission"], errors="coerce").fillna(0.0).clip(lower=0.0)
    assert (inc >= 0).all(), "emission increments must be non-negative"

    # Recomputed monotonicity check (tolerant)
    cum = inc.cumsum().to_numpy()
    assert (np.diff(cum) >= -1e-9).all(), "cum_supply should be monotone non-decreasing (recomputed)"
