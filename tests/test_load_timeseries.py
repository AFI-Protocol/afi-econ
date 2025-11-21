from pathlib import Path

from afi_econ_kit.config import load_config
from afi_econ_kit.data_io import load_timeseries


def test_load_timeseries_has_required_columns() -> None:
    config = load_config(Path("config.yaml"))
    dataset = load_timeseries(config)
    df = dataset.data
    assert not df.empty
    for key in ("epoch", "emission", "aim", "cum_supply", "year"):
        assert key in df.columns
    assert dataset.resolved["emission"] == "E_t"
