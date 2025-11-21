"""Global test configuration ensuring repo-local imports resolve."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
SRC_STR = str(SRC_PATH)

if SRC_STR not in sys.path:
    sys.path.insert(0, SRC_STR)

existing = os.environ.get("PYTHONPATH")
if existing:
    paths = existing.split(os.pathsep)
    if SRC_STR not in paths:
        os.environ["PYTHONPATH"] = os.pathsep.join([SRC_STR, *paths])
else:
    os.environ["PYTHONPATH"] = SRC_STR
