"""Root conftest.

When pytest runs from the repo root, it prepends the repo root to ``sys.path``.
Because this integration ships flat (``const.py``, ``select.py``, ... at the root),
that would shadow stdlib modules such as ``select`` and break Home Assistant's
imports. Strip the repo root from ``sys.path`` before any test imports HA; tests
reach the integration through the synthetic ``neopool_mqtt`` package set up in
``tests/conftest.py``.
"""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent)
sys.path[:] = [p for p in sys.path if p not in ("", ".", _ROOT)]
