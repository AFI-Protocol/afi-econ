# Fast, hermetic test for --fresh-outdir and safety guards.
import json, os, sys, subprocess
from pathlib import Path

def test_fresh_outdir_recreates(tmp_path):
    marker = tmp_path / "marker.txt"
    marker.write_text("hello")
    proc = subprocess.run(
        [sys.executable, "scripts/end_to_end_audit.py", "--out", str(tmp_path), "--fresh-outdir"],
        check=False, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert not marker.exists()
    rep = tmp_path / "audit_report.json"
    assert rep.exists()
    data = json.loads(rep.read_text())
    assert "summary" in data

def test_fresh_outdir_safety_guards_home_and_root(monkeypatch):
    # HOME
    proc_home = subprocess.run(
        [sys.executable, "scripts/end_to_end_audit.py", "--out", str(Path.home()), "--fresh-outdir"],
        check=False, capture_output=True, text=True
    )
    assert proc_home.returncode != 0
    assert "Refusing to operate" in (proc_home.stderr + proc_home.stdout)

    # ROOT
    proc_root = subprocess.run(
        [sys.executable, "scripts/end_to_end_audit.py", "--out", "/", "--fresh-outdir"],
        check=False, capture_output=True, text=True
    )
    assert proc_root.returncode != 0
    assert "Refusing to operate" in (proc_root.stderr + proc_root.stdout)
