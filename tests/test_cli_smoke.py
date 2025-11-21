import shutil
import subprocess
import sys
from pathlib import Path


def test_cli_check_smoke() -> None:
    config_path = Path("config.yaml")
    assert config_path.exists()

    executable = shutil.which("afi-econ-kit")
    if executable:
        cmd = [executable, "check", "--config", str(config_path)]
    else:
        cmd = [sys.executable, "-m", "afi_econ_kit.cli", "check", "--config", str(config_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr or result.stdout
