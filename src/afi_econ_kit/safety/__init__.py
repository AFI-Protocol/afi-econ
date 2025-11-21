"""Namespace package exposing lightweight safety helpers alongside legacy APIs."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable

__all__ = ["exponential_smoothing", "rate_limit_scalar"]


def _load_legacy_module() -> ModuleType:
    module_name = "afi_econ_kit._legacy_safety"
    if module_name in sys.modules:
        return sys.modules[module_name]

    legacy_path = Path(__file__).resolve().parent.parent / "safety.py"
    spec = importlib.util.spec_from_file_location(module_name, legacy_path)
    if spec is None or spec.loader is None:
        raise ImportError("Unable to load legacy safety module")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _reexport(module: ModuleType, names: Iterable[str]) -> None:
    for name in names:
        if name.startswith("_"):
            continue
        globals()[name] = getattr(module, name)
        if name not in __all__:
            __all__.append(name)


_legacy = _load_legacy_module()
legacy_names = getattr(_legacy, "__all__", None)
if not legacy_names:
    legacy_names = dir(_legacy)
_reexport(_legacy, legacy_names)

from .smoothing import exponential_smoothing
from .rate_limits import rate_limit_scalar
