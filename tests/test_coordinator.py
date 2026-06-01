"""Unit tests for NeoPoolCoordinator: LWT availability, optimistic updates, commands."""
from types import SimpleNamespace

import pytest

from conftest import load_fixture, load_module

coordinator_mod = load_module("coordinator")
NeoPoolCoordinator = coordinator_mod.NeoPoolCoordinator


def _msg(payload):
    return SimpleNamespace(payload=payload)


@pytest.fixture
def coord(monkeypatch):
    """A coordinator whose dispatcher is stubbed so it needs no running hass."""
    monkeypatch.setattr(coordinator_mod, "async_dispatcher_send", lambda *a, **k: None)
    return NeoPoolCoordinator(
        hass=None, mqtt_topic="SmartPool", device_name="Pool", entry_id="abc"
    )


# --- LWT availability (Fase 1.1) ------------------------------------------------


def test_lwt_offline_makes_unavailable(coord):
    coord._on_sensor_message(_msg('{"NeoPool": {"Type": "OxiLife"}}'))
    assert coord.available is True

    coord._on_lwt_message(_msg("Offline"))
    assert coord.available is False

    coord._on_lwt_message(_msg("Online"))
    assert coord.available is True


def test_lwt_offline_wins_over_data(coord):
    """An explicit Offline LWT overrides the data-driven availability flag."""
    coord._on_lwt_message(_msg("Offline"))
    coord._on_sensor_message(_msg('{"NeoPool": {"Type": "OxiLife"}}'))
    assert coord._available is True  # data was seen
    assert coord.available is False  # but LWT Offline wins


def test_lwt_bytes_payload(coord):
    coord._on_sensor_message(_msg('{"NeoPool": {}}'))
    coord._on_lwt_message(_msg(b"Offline"))
    assert coord.available is False


def test_lwt_unknown_payload_ignored(coord):
    coord._on_lwt_message(_msg("garbage"))
    assert coord._lwt_online is None


# --- SENSOR parsing (Fase 5) ----------------------------------------------------


def test_parse_full_fixture(coord):
    import json

    coord._on_sensor_message(_msg(json.dumps(load_fixture("sensor_full"))))
    assert coord.data["pH"]["Data"] == 7.2
    assert coord.data["Hydrolysis"]["State"] == "POL1"


def test_parse_minimal_fixture_no_crash(coord):
    import json

    coord._on_sensor_message(_msg(json.dumps(load_fixture("sensor_minimal"))))
    assert coord.data["Filtration"]["State"] == 0
    assert "Hydrolysis" not in coord.data


def test_invalid_json_ignored(coord):
    coord._on_sensor_message(_msg("not json"))
    assert coord.data == {}


# --- Optimistic updates / _apply_result ----------------------------------------


def test_apply_filtration_onoff(coord):
    assert coord._apply_result("NPFiltration", "ON") is True
    assert coord.data["Filtration"]["State"] == 1
    assert coord._apply_result("NPFiltration", 0) is True
    assert coord.data["Filtration"]["State"] == 0


def test_apply_aux(coord):
    assert coord._apply_result("NPAux2", "ON") is True
    assert coord.data["Relay"]["Aux"][1] == 1


# --- NodeID not exposed (Fase 1.2) ---------------------------------------------


def test_nodeid_not_in_device_info(coord):
    import json

    coord._on_sensor_message(_msg(json.dumps(load_fixture("sensor_full"))))
    info = coord.device_info
    assert "serial_number" not in info
    assert "0xANONYMISED" not in json.dumps(info, default=str)
    assert info["identifiers"] == {("neopool_mqtt", "SmartPool")}
