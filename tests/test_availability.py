"""Entities that cannot work on a given panel must say so, not sit there looking fine.

Measured on the reference installation (18-09-2026): no relay is assigned to the
lighting function (MBF_PAR_LIGHTING_GPIO = 0), so Tasmota leaves "Light" out of the
SENSOR JSON and answers NPLight with {"Command":"Error"}. And the hydrolysis cover
reduction is switched off, so the cover bit in the hydrolysis status word never rises.
"""
import pytest

from conftest import load_module

const = load_module("const")
coordinator_mod = load_module("coordinator")
binary = load_module("binary_sensor")
button = load_module("button")
select_mod = load_module("select")
switch_mod = load_module("switch")


@pytest.fixture
def coord(monkeypatch):
    monkeypatch.setattr(coordinator_mod, "async_dispatcher_send", lambda *a, **k: None)
    c = coordinator_mod.NeoPoolCoordinator(
        hass=None, mqtt_topic="SmartPool", device_name="Pool", entry_id="abc"
    )
    c._available = True
    return c


# --- Lighting -------------------------------------------------------------------


def test_light_switch_unavailable_without_a_lighting_relay(coord):
    coord.data = {"Filtration": {"State": 1}}
    assert switch_mod.NeoPoolLightSwitch(coord).available is False


def test_light_switch_available_when_the_panel_reports_a_light(coord):
    coord.data = {"Light": 0}
    entity = switch_mod.NeoPoolLightSwitch(coord)
    assert entity.available is True
    assert entity.is_on is False


def test_light_mode_select_unavailable_without_a_lighting_relay(coord):
    coord.data = {"Filtration": {"State": 1}}
    assert select_mod.NeoPoolLightModeSelect(coord).available is False


def test_light_mode_select_available_with_a_light(coord):
    coord.data = {"Light": 1}
    assert select_mod.NeoPoolLightModeSelect(coord).available is True


def test_light_next_program_button_follows_the_light(coord):
    desc = next(d for d in button.BUTTONS if d.key == "light_next_program")
    entity = button.NeoPoolButton(coord, desc)
    coord.data = {}
    assert entity.available is False
    coord.data = {"Light": 0}
    assert entity.available is True


def test_buttons_without_an_availability_rule_stay_available(coord):
    coord.data = {}
    for key in ("clear_errors", "save_eeprom", "exec"):
        desc = next(d for d in button.BUTTONS if d.key == key)
        assert button.NeoPoolButton(coord, desc).available is True


# --- The old cover bit ----------------------------------------------------------


def _cover_active(coord):
    desc = next(d for d in binary.BINARY_SENSORS if d.key == "cover_active")
    return binary.NeoPoolBinarySensor(coord, desc)


def test_cover_active_unavailable_when_the_reduction_is_off(coord):
    """0x042C bit 0 clear: the bit never rises, so 'off' would be a false claim."""
    coord.data = {"Hydrolysis": {"Cover": 0}}
    coord.registers = {const.REG_PAR_HIDRO_COVER_ENABLE: 0x0000}
    assert _cover_active(coord).available is False


def test_cover_active_available_when_the_reduction_is_on(coord):
    coord.data = {"Hydrolysis": {"Cover": 1}}
    coord.registers = {const.REG_PAR_HIDRO_COVER_ENABLE: const.MASK_HIDRO_COVER_ENABLE}
    entity = _cover_active(coord)
    assert entity.available is True
    assert entity.is_on is True


def test_cover_active_unavailable_before_the_register_is_read(coord):
    coord.data = {"Hydrolysis": {"Cover": 0}}
    assert _cover_active(coord).available is False


def test_other_binary_sensors_are_unaffected(coord):
    coord.data = {"pH": {"State": 0}}
    desc = next(d for d in binary.BINARY_SENSORS if d.key == "ph_alarm")
    assert binary.NeoPoolBinarySensor(coord, desc).available is True
