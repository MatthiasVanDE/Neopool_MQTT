"""Tests for sensor/binary_sensor descriptions against both fixtures."""
import pytest

from conftest import load_fixture, load_module

sensor_mod = load_module("sensor")
binary_sensor_mod = load_module("binary_sensor")


@pytest.fixture(params=["sensor_full", "sensor_minimal"])
def data(request):
    return load_fixture(request.param)["NeoPool"]


def test_all_sensor_value_fns_no_crash(data):
    for desc in sensor_mod.SENSORS:
        desc.value_fn(data)  # must not raise on either fixture
        if desc.available_fn is not None:
            assert desc.available_fn(data) in (True, False)
        if desc.unit_fn is not None:
            desc.unit_fn(data)
        if desc.extra_attrs_fn is not None:
            desc.extra_attrs_fn(data)


def test_all_binary_sensor_fns_no_crash(data):
    for desc in binary_sensor_mod.BINARY_SENSORS:
        assert desc.is_on_fn(data) in (True, False, None)


def test_named_relays_available_only_when_present():
    full = load_fixture("sensor_full")["NeoPool"]
    minimal = load_fixture("sensor_minimal")["NeoPool"]
    named = {
        "relay_base",
        "relay_redox",
        "relay_chlorine",
        "relay_conductivity",
        "relay_heating",
        "relay_uv",
    }
    by_key = {d.key: d for d in sensor_mod.SENSORS}
    for key in named:
        assert by_key[key].available_fn(full) is True
        assert by_key[key].available_fn(minimal) is False


def test_relay_values_map_on_off():
    full = load_fixture("sensor_full")["NeoPool"]
    by_key = {d.key: d for d in sensor_mod.SENSORS}
    # Fixture: Relay.Redox == 1 -> "On", Relay.Heating == 0 -> "Off"
    assert by_key["relay_redox"].value_fn(full) == "On"
    assert by_key["relay_heating"].value_fn(full) == "Off"


# --- Module diagnostics (Fase 2.2) ---------------------------------------------


def test_module_binary_sensors():
    full = load_fixture("sensor_full")["NeoPool"]
    minimal = load_fixture("sensor_minimal")["NeoPool"]
    by_key = {d.key: d for d in binary_sensor_mod.BINARY_SENSORS}
    # full fixture: all modules present (==1)
    assert by_key["module_ph"].is_on_fn(full) is True
    assert by_key["module_hydrolysis"].is_on_fn(full) is True
    # minimal fixture: only pH present (==1), others reported as 0
    assert by_key["module_ph"].is_on_fn(minimal) is True
    assert by_key["module_redox"].is_on_fn(minimal) is False


def test_module_absent_modules_dict_returns_none():
    assert binary_sensor_mod._module_present("pH")({}) is None


# --- Modbus error rate (Fase 2.3) ----------------------------------------------


def test_mb_error_rate():
    full = load_fixture("sensor_full")["NeoPool"]
    # 100000 requests, 99950 ok -> 50 errors -> 0.05%
    assert sensor_mod._mb_error_rate(full) == 0.05


def test_mb_error_rate_missing_connection():
    assert sensor_mod._mb_error_rate({}) is None
    assert sensor_mod._mb_error_rate({"Connection": {"MBRequests": 0}}) is None
