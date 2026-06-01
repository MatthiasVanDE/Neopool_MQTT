"""Smoke test: the integration modules import and fixtures parse."""
from conftest import load_fixture, load_module


def test_imports():
    for name in (
        "const",
        "coordinator",
        "entity",
        "sensor",
        "binary_sensor",
        "switch",
        "select",
        "number",
        "button",
        "config_flow",
    ):
        assert load_module(name) is not None


def test_fixtures_parse():
    full = load_fixture("sensor_full")
    minimal = load_fixture("sensor_minimal")
    assert full["NeoPool"]["Type"] == "OxiLife"
    assert minimal["NeoPool"]["Type"] == "OxiLife"
