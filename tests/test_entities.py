"""Tests for entity command-payload construction across platforms."""
import json

import pytest

from conftest import load_fixture, load_module

coordinator_mod = load_module("coordinator")
select_mod = load_module("select")
button_mod = load_module("button")
number_mod = load_module("number")
switch_mod = load_module("switch")


@pytest.fixture
def coord(monkeypatch):
    monkeypatch.setattr(coordinator_mod, "async_dispatcher_send", lambda *a, **k: None)
    c = coordinator_mod.NeoPoolCoordinator(
        hass=None, mqtt_topic="SmartPool", device_name="Pool", entry_id="abc"
    )
    c.sent = []

    async def _capture(command, payload=""):
        c.sent.append((command, str(payload)))

    c.async_send_command = _capture
    c._on_sensor_message(type("M", (), {"payload": json.dumps(load_fixture("sensor_full"))}))
    return c


async def test_light_mode_select_payloads(coord):
    sel = select_mod.NeoPoolLightModeSelect(coord)
    await sel.async_select_option("Auto")
    await sel.async_select_option("On")
    await sel.async_select_option("Off")
    assert coord.sent == [("NPLight", "3"), ("NPLight", "1"), ("NPLight", "0")]


async def test_light_next_program_button_payload(coord):
    desc = next(d for d in button_mod.BUTTONS if d.key == "light_next_program")
    btn = button_mod.NeoPoolButton(coord, desc)
    await btn.async_press()
    assert coord.sent == [("NPLight", "4")]


def test_light_mode_current_option(coord):
    sel = select_mod.NeoPoolLightModeSelect(coord)
    coord.data["Light"] = 3
    assert sel.current_option == "Auto"
    coord.data["Light"] = 1
    assert sel.current_option == "On"
