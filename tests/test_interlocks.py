"""Controls that must refuse, or grey out, in the situation they cannot work.

Two different mechanisms, and the difference is the point:

* ``available = False`` for a control the panel would ignore anyway. It greys out
  everywhere, but note that ``entity_service_call`` silently drops an unavailable
  entity from a service call - so this is never used for anything safety related.
* a refusal inside the command, limited to calls made by a person, for the interlocks.
  An automation keeps its say; the dry-run protection switches Aux4 off from an
  automation and may never be blocked. A ServiceValidationError, so it comes back as
  a plain message instead of a stack trace.
"""
from types import SimpleNamespace

import pytest
from homeassistant.core import Context
from homeassistant.exceptions import ServiceValidationError

from conftest import load_module

const = load_module("const")
coordinator_mod = load_module("coordinator")
number_mod = load_module("number")
select_mod = load_module("select")
switch_mod = load_module("switch")

BY_HAND = Context(user_id="ed84f6ebf8444161a2d0725bd8915735")
BY_AUTOMATION = Context()  # what an automation, script or scene leaves behind


def _entry(data=None, options=None):
    return SimpleNamespace(entry_id="abc", data=data or {}, options=options or {})


@pytest.fixture
def coord(monkeypatch):
    monkeypatch.setattr(coordinator_mod, "async_dispatcher_send", lambda *a, **k: None)
    c = coordinator_mod.NeoPoolCoordinator(
        hass=None, mqtt_topic="SmartPool", device_name="Pool", entry_id="abc"
    )
    c._available = True
    return c


@pytest.fixture
def sent(coord, monkeypatch):
    calls = []

    async def collect(cmd, payload=""):
        calls.append((cmd, payload))

    monkeypatch.setattr(coord, "async_send_command", collect)
    return calls


def _filtration(coord, state=1, mode=1, aux=None):
    coord.data = {
        "Filtration": {"State": state, "Mode": mode, "Speed": 1},
        "Relay": {"Aux": aux or [0, 0, 0, 0]},
    }


# --- Option resolution ----------------------------------------------------------


def test_no_interlock_for_an_entry_that_predates_the_option():
    """REGEL 0: an update must not start refusing commands on existing installs."""
    assert const.flow_required_aux(_entry()) == frozenset()
    assert const.speed_controller(_entry()) == ""


def test_flow_required_aux_comes_back_as_numbers():
    entry = _entry(options={const.CONF_FLOW_REQUIRED_AUX: ["4", "1"]})
    assert const.flow_required_aux(entry) == frozenset({1, 4})


def test_flow_required_aux_ignores_rubbish():
    entry = _entry(options={const.CONF_FLOW_REQUIRED_AUX: ["4", "", "aux2"]})
    assert const.flow_required_aux(entry) == frozenset({4})


def test_speed_controller_options_override_data():
    entry = _entry(
        data={const.CONF_SPEED_CONTROLLER: "automation.old"},
        options={const.CONF_SPEED_CONTROLLER: "automation.new"},
    )
    assert const.speed_controller(entry) == "automation.new"


# --- Filtration off while an aux needs the flow ---------------------------------


async def test_filtration_cannot_be_switched_off_by_hand_under_a_running_aux(
    coord, sent
):
    coord.flow_required_aux = frozenset({4})
    _filtration(coord, aux=[0, 0, 0, 1])
    entity = switch_mod.NeoPoolFiltrationSwitch(coord)
    entity._context = BY_HAND

    with pytest.raises(ServiceValidationError):
        await entity.async_turn_off()
    assert sent == []


async def test_an_automation_may_still_switch_filtration_off(coord, sent):
    """The dry-run automations are the layer that works; never stand in their way."""
    coord.flow_required_aux = frozenset({4})
    _filtration(coord, aux=[0, 0, 0, 1])
    entity = switch_mod.NeoPoolFiltrationSwitch(coord)
    entity._context = BY_AUTOMATION

    await entity.async_turn_off()
    assert sent == [("NPFiltration", "0")]


async def test_filtration_off_by_hand_is_fine_with_the_aux_idle(coord, sent):
    coord.flow_required_aux = frozenset({4})
    _filtration(coord, aux=[1, 0, 0, 0])
    entity = switch_mod.NeoPoolFiltrationSwitch(coord)
    entity._context = BY_HAND

    await entity.async_turn_off()
    assert sent == [("NPFiltration", "0")]


async def test_filtration_off_by_hand_is_fine_without_the_interlock(coord, sent):
    _filtration(coord, aux=[0, 0, 0, 1])
    entity = switch_mod.NeoPoolFiltrationSwitch(coord)
    entity._context = BY_HAND

    await entity.async_turn_off()
    assert sent == [("NPFiltration", "0")]


# --- Aux on without flow --------------------------------------------------------


async def test_aux_cannot_be_switched_on_by_hand_without_filtration(coord, sent):
    coord.flow_required_aux = frozenset({4})
    _filtration(coord, state=0)
    entity = switch_mod.NeoPoolAuxSwitch(coord, 4)
    entity._context = BY_HAND

    with pytest.raises(ServiceValidationError):
        await entity.async_turn_on()
    assert sent == []


async def test_the_refusal_names_the_aux_as_the_panel_calls_it(coord):
    coord.flow_required_aux = frozenset({4})
    _filtration(coord, state=0)
    coord.registers = {}
    assert coord.aux_label(4) == "Aux 4"


async def test_another_aux_is_left_alone(coord, sent):
    coord.flow_required_aux = frozenset({4})
    _filtration(coord, state=0)
    entity = switch_mod.NeoPoolAuxSwitch(coord, 1)
    entity._context = BY_HAND

    await entity.async_turn_on()
    assert sent == [("NPAux1", "1")]


async def test_aux_on_is_allowed_while_filtration_runs(coord, sent):
    coord.flow_required_aux = frozenset({4})
    _filtration(coord, state=1)
    entity = switch_mod.NeoPoolAuxSwitch(coord, 4)
    entity._context = BY_HAND

    await entity.async_turn_on()
    assert sent == [("NPAux4", "1")]


async def test_aux_on_is_allowed_while_the_panel_has_not_said(coord, sent):
    """Silence is not proof of a dry pump, and the panel interlocks on FL1 itself."""
    coord.flow_required_aux = frozenset({4})
    coord.data = {}
    entity = switch_mod.NeoPoolAuxSwitch(coord, 4)
    entity._context = BY_HAND

    await entity.async_turn_on()
    assert sent == [("NPAux4", "1")]


async def test_an_automation_may_switch_the_aux_on(coord, sent):
    coord.flow_required_aux = frozenset({4})
    _filtration(coord, state=0)
    entity = switch_mod.NeoPoolAuxSwitch(coord, 4)
    entity._context = BY_AUTOMATION

    await entity.async_turn_on()
    assert sent == [("NPAux4", "1")]


async def test_switching_an_aux_off_is_never_refused(coord, sent):
    coord.flow_required_aux = frozenset({4})
    _filtration(coord, state=0, aux=[0, 0, 0, 1])
    entity = switch_mod.NeoPoolAuxSwitch(coord, 4)
    entity._context = BY_HAND

    await entity.async_turn_off()
    assert sent == [("NPAux4", "0")]


# --- The two speed selects no longer say the same thing -------------------------


def test_default_speed_is_unavailable_inside_a_timer_interval(coord):
    """Auto mode with the pump running: the interval speed applies, not this field."""
    _filtration(coord, state=1, mode=1)
    assert select_mod.NeoPoolFiltrationSpeedSelect(coord).available is False


def test_default_speed_is_available_in_manual_mode(coord):
    _filtration(coord, state=1, mode=const.FILTRATION_MODE_MANUAL)
    assert select_mod.NeoPoolFiltrationSpeedSelect(coord).available is True


def test_default_speed_is_available_while_the_pump_is_off(coord):
    _filtration(coord, state=0, mode=1)
    assert select_mod.NeoPoolFiltrationSpeedSelect(coord).available is True


def test_interval_speed_is_unavailable_in_manual_mode(coord):
    _filtration(coord, state=1, mode=const.FILTRATION_MODE_MANUAL)
    coord.registers = {const.REG_PAR_FILTRATION_CONF: 0x0081}
    assert select_mod.NeoPoolIntervalSpeedSelect(coord).available is False


def test_interval_speed_is_available_in_auto_mode(coord):
    _filtration(coord, state=1, mode=1)
    coord.registers = {const.REG_PAR_FILTRATION_CONF: 0x0081}
    assert select_mod.NeoPoolIntervalSpeedSelect(coord).available is True


def test_interval_speed_stays_available_before_the_mode_is_known(coord):
    """Grey out on a reading, never on silence."""
    coord.data = {}
    coord.registers = {const.REG_PAR_FILTRATION_CONF: 0x0081}
    assert select_mod.NeoPoolIntervalSpeedSelect(coord).available is True


# --- The speed is owned by an automation ----------------------------------------


def _with_controller(coord, entity_id, state):
    coord.speed_controller = entity_id
    coord.hass = SimpleNamespace(
        states=SimpleNamespace(
            get=lambda eid: (
                SimpleNamespace(
                    state=state, attributes={"friendly_name": "Snelheid volgt pomp"}
                )
                if eid == entity_id
                else None
            )
        )
    )


async def test_the_speed_cannot_be_set_by_hand_while_its_automation_is_on(coord, sent):
    _filtration(coord, state=1, mode=1)
    coord.registers = {const.REG_PAR_FILTRATION_CONF: 0x0081}
    _with_controller(coord, "automation.speed", "on")
    entity = select_mod.NeoPoolIntervalSpeedSelect(coord)
    entity._context = BY_HAND

    with pytest.raises(ServiceValidationError):
        await entity.async_select_option("High")
    assert sent == []


async def test_that_very_automation_is_not_locked_out(coord, sent):
    _filtration(coord, state=1, mode=1)
    coord.registers = {const.REG_PAR_FILTRATION_CONF: 0x0081}
    _with_controller(coord, "automation.speed", "on")
    entity = select_mod.NeoPoolIntervalSpeedSelect(coord)
    entity._context = BY_AUTOMATION

    await entity.async_select_option("Mid")
    assert sent[0] == ("NPWrite", "0x050F 129")


async def test_switching_the_automation_off_gives_the_speed_back(coord, sent):
    _filtration(coord, state=1, mode=1)
    coord.registers = {const.REG_PAR_FILTRATION_CONF: 0x0081}
    _with_controller(coord, "automation.speed", "off")
    entity = select_mod.NeoPoolIntervalSpeedSelect(coord)
    entity._context = BY_HAND

    await entity.async_select_option("Mid")
    assert sent[0] == ("NPWrite", "0x050F 129")


# --- Smart and Intelligent parameters -------------------------------------------


def _register_number(coord, key):
    desc = next(d for d in number_mod.REGISTER_NUMBERS if d.key == key)
    return number_mod.NeoPoolRegisterNumber(coord, desc)


@pytest.mark.parametrize(
    ("key", "register"),
    (
        ("smart_temp_high", const.REG_PAR_SMART_TEMP_HIGH),
        ("intelligent_temp", const.REG_PAR_INTELLIGENT_TEMP),
    ),
)
def test_mode_parameters_are_unavailable_in_another_mode(coord, key, register):
    _filtration(coord, mode=1)  # Auto
    coord.registers = {register: 28}
    assert _register_number(coord, key).available is False


def test_smart_parameters_are_available_in_smart_mode(coord):
    _filtration(coord, mode=const.FILTRATION_MODE_SMART)
    coord.registers = {const.REG_PAR_SMART_TEMP_HIGH: 28}
    assert _register_number(coord, "smart_temp_high").available is True


def test_intelligent_parameters_are_available_in_intelligent_mode(coord):
    _filtration(coord, mode=const.FILTRATION_MODE_INTELLIGENT)
    coord.registers = {const.REG_PAR_INTELLIGENT_TEMP: 24}
    assert _register_number(coord, "intelligent_temp").available is True


def test_a_parameter_without_a_mode_rule_is_unaffected(coord):
    _filtration(coord, mode=1)
    coord.registers = {const.REG_PAR_FILTVALVE_PERIOD_MINUTES: 10080}
    assert _register_number(coord, "backwash_period").available is True
