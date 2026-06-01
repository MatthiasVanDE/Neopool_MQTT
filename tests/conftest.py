"""Test configuration for the neopool_mqtt integration.

The integration files live at the repository root (flat layout, as deployed under
``custom_components/neopool_mqtt``). To import them with their relative imports
(``from .const import ...``) intact, and to avoid the local ``select.py`` shadowing
the stdlib ``select`` module, we register a synthetic package named ``neopool_mqtt``
whose ``__path__`` points at the repo root.
"""
from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
PKG = "neopool_mqtt"

if PKG not in sys.modules:
    pkg = types.ModuleType(PKG)
    pkg.__path__ = [str(ROOT)]
    sys.modules[PKG] = pkg


def load_module(name: str):
    """Import a submodule of the integration, e.g. ``coordinator``."""
    return importlib.import_module(f"{PKG}.{name}")


def load_fixture(name: str) -> dict:
    """Load and parse a JSON fixture by file name (without extension)."""
    return json.loads((FIXTURES / f"{name}.json").read_text())
