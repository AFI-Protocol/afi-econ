from pathlib import Path

from afi_econ_kit.config import load_config
from afi_econ_kit.data_io import load_timeseries
from afi_econ_kit.emissions import assert_monotone_cum_supply


def test_cumulative_supply_monotone() -> None:
    config = load_config(Path("config.yaml"))
    ts = load_timeseries(config)
    assert_monotone_cum_supply(ts.data)
