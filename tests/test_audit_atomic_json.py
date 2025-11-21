# Fast, hermetic test for atomic write behavior (no sibling repos required).
import json, sys, subprocess
from pathlib import Path

def run_audit(outdir: Path, extra=None):
    args = [sys.executable, "scripts/end_to_end_audit.py", "--out", str(outdir)]
    if extra:
        args += extra
    return subprocess.run(args, check=False, capture_output=True, text=True)

def test_atomic_json_write(tmp_path):
    r1 = run_audit(tmp_path)
    assert r1.returncode == 0, r1.stderr or r1.stdout
    report = tmp_path / "audit_report.json"
    assert report.exists()
    data1 = json.loads(report.read_text())
    assert isinstance(data1, dict) and "summary" in data1

    # second run should cleanly overwrite; no *.tmp litter
    r2 = run_audit(tmp_path)
    assert r2.returncode == 0, r2.stderr or r2.stdout
    leftovers = list(tmp_path.glob("*.tmp"))
    assert not leftovers
    data2 = json.loads(report.read_text())
    assert isinstance(data2, dict) and "summary" in data2
