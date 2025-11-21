import shutil
import subprocess
import sys
from pathlib import Path


def test_cli_plot_creates_figures() -> None:
    config_path = Path("config.yaml")
    assert config_path.exists()

    figures_dir = Path("tests") / "tmp_figures"
    if figures_dir.exists():
        shutil.rmtree(figures_dir)

    cmd = [
        sys.executable,
        "-m",
        "afi_econ_kit.cli",
        "plot",
        "--config",
        str(config_path),
        "--output-dir",
        str(figures_dir),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr or result.stdout

        expected = figures_dir / "emissions_by_epoch.png"
        assert expected.exists(), "Expected emissions_by_epoch.png to be created"
    finally:
        if figures_dir.exists():
            shutil.rmtree(figures_dir)
