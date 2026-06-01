"""Tests for the Berry (neopoolcmd.be) option and conditional Aux switches."""
from types import SimpleNamespace

import pytest

from conftest import load_module

const = load_module("const")
switch_mod = load_module("switch")
coordinator_mod = load_module("coordinator")
config_flow_mod = load_module("config_flow")


def _entry(data=None, options=None):
    return SimpleNamespace(
        entry_id="abc", data=data or {}, options=options or {}
    )


# --- berry_enabled resolution --------------------------------------------------


def test_berry_default_true_when_absent():
    """REGEL 0: pre-existing entries (no key) keep Aux switches -> default True."""
    assert const.berry_enabled(_entry()) is True


def test_berry_from_data_false():
    assert const.berry_enabled(_entry(data={const.CONF_BERRY_ENABLED: False})) is False


def test_berry_options_override_data():
    entry = _entry(
        data={const.CONF_BERRY_ENABLED: False},
        options={const.CONF_BERRY_ENABLED: True},
    )
    assert const.berry_enabled(entry) is True


# --- conditional Aux switch creation -------------------------------------------


@pytest.fixture
def coord(monkeypatch):
    monkeypatch.setattr(coordinator_mod, "async_dispatcher_send", lambda *a, **k: None)
    return coordinator_mod.NeoPoolCoordinator(
        hass=None, mqtt_topic="SmartPool", device_name="Pool", entry_id="abc"
    )


async def _setup_keys(coord, entry):
    hass = SimpleNamespace(data={const.DOMAIN: {entry.entry_id: coord}})
    added = []
    await switch_mod.async_setup_entry(hass, entry, lambda items: added.extend(items))
    return [e._key for e in added]


async def test_aux_created_when_berry_enabled(coord):
    keys = await _setup_keys(coord, _entry(data={const.CONF_BERRY_ENABLED: True}))
    assert {"aux1", "aux2", "aux3", "aux4"}.issubset(set(keys))
    assert "filtration" in keys and "light" in keys


async def test_aux_absent_when_berry_disabled(coord):
    keys = await _setup_keys(coord, _entry(data={const.CONF_BERRY_ENABLED: False}))
    assert not any(k.startswith("aux") for k in keys)
    assert "filtration" in keys and "light" in keys


async def test_aux_preserved_for_legacy_entry(coord):
    """No key set (legacy entry) -> Aux switches still created."""
    keys = await _setup_keys(coord, _entry())
    assert {"aux1", "aux2", "aux3", "aux4"}.issubset(set(keys))


# --- OptionsFlow deprecation (Fase 1.6) ----------------------------------------


def test_options_flow_does_not_set_config_entry():
    """Modern HA: config_entry is a base-class property; we must not assign it."""
    flow = config_flow_mod.NeoPoolMQTTConfigFlow.async_get_options_flow(_entry())
    assert isinstance(flow, config_flow_mod.NeoPoolMQTTOptionsFlowHandler)
    # The deprecated/broken pattern was `self.config_entry = config_entry`.
    assert "config_entry" not in flow.__dict__

