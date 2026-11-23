"""Sensor platform for NeoPool MQTT Controller."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    FILTRATION_MODES,
    FILTRATION_SPEEDS,
    HYDROLYSIS_STATES,
    MASK_HIDRO_COVER_REDUCTION,
    PH_STATES,
    REG_AUX_NAME_LENGTH,
    REG_HIDRO_SWITCH_VALUE,
    REG_HIDRO_VOLTAGE,
    REG_INPUT_STATUS,
    REG_PAR_FILTVALVE_GPIO,
    REG_PAR_FILTVALVE_PERIOD_MINUTES,
    REG_PAR_FILTVALVE_REMAINING,
    REG_PAR_FILTVALVE_START,
    REG_PAR_HIDRO_COVER_REDUCTION,
    REG_PAR_HIDRO_POL0,
    REG_PAR_HIDRO_POL1,
    REG_PAR_HIDRO_POL2,
    REG_PAR_INTELLIGENT_BONUS_TIME,
    REG_PAR_INTELLIGENT_INTERVALS,
    REG_PAR_INTELLIGENT_TT_NEXT_INTERVAL,
    REG_PAR_PUMP_RELAY_TIME_OFF,
    REG_PAR_PUMP_RELAY_TIME_ON,
    REG_PAR_SMART_INTERVAL_REDUCTION,
    REG_PAR_TIME,
    REG_PAR_UICFG_MACH_NAME_AUX,
    decode_pump_time,
)
from .coordinator import NeoPoolCoordinator
from .entity import NeoPoolEntity


@dataclass(frozen=True, kw_only=True)
class NeoPoolSensorDescription(SensorEntityDescription):
    """Description of a NeoPool sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    available_fn: Callable[[dict[str, Any]], bool] | None = None
    extra_attrs_fn: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None
    unit_fn: Callable[["NeoPoolCoordinator"], str | None] | None = None
    # Takes precedence over value_fn: for values that need the raw register cache
    # rather than the SENSOR JSON.
    coordinator_value_fn: Callable[["NeoPoolCoordinator"], Any] | None = None


def _path(*keys: str) -> Callable[[dict[str, Any]], Any]:
    """Build a value_fn that walks a nested dict path."""

    def get(data: dict[str, Any]) -> Any:
        node: Any = data
        for key in keys:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        return node

    return get


def _relay_state(idx: int) -> Callable[[dict[str, Any]], str | None]:
    def get(data: dict[str, Any]) -> str | None:
        states = (data.get("Relay") or {}).get("State")
        if isinstance(states, list) and len(states) >= idx:
            return "On" if states[idx - 1] == 1 else "Off"
        return None

    return get


def _relay_present(name: str) -> Callable[[dict[str, Any]], bool]:
    """available_fn: the named relay subkey exists (function assigned to a relay)."""

    def get(data: dict[str, Any]) -> bool:
        return (data.get("Relay") or {}).get(name) is not None

    return get


def _on_off(*path: str) -> Callable[[dict[str, Any]], str | None]:
    def get(data: dict[str, Any]) -> str | None:
        node: Any = data
        for key in path:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        if node == 1:
            return "On"
        if node == 0:
            return "Off"
        return None

    return get


def _ph_pump(data: dict[str, Any]) -> Any:
    pump = (data.get("pH") or {}).get("Pump")
    return {0: "Inactive", 1: "On", 2: "Off"}.get(pump, pump)


def _ph_tank(data: dict[str, Any]) -> Any:
    tank = (data.get("pH") or {}).get("Tank")
    return {0: "Empty", 1: "OK"}.get(tank, tank)


def _ph_state(data: dict[str, Any]) -> Any:
    state = (data.get("pH") or {}).get("State")
    if state is None:
        return None
    return PH_STATES.get(state, f"Unknown ({state})")


def _ph_extra(data: dict[str, Any]) -> dict[str, Any]:
    ph = data.get("pH") or {}
    return {"min_setpoint": ph.get("Min"), "max_setpoint": ph.get("Max")}


def _hydrolysis_state(data: dict[str, Any]) -> Any:
    state = (data.get("Hydrolysis") or {}).get("State")
    if not state:
        return None
    return HYDROLYSIS_STATES.get(state, state)


def _hydrolysis_extra(data: dict[str, Any]) -> dict[str, Any]:
    hydro = data.get("Hydrolysis") or {}
    return {
        "cover": hydro.get("Cover"),
        "boost": hydro.get("Boost"),
        "low_alarm": hydro.get("Low"),
        "flow_alarm": hydro.get("FL1"),
        "redox_activated": hydro.get("Redox"),
    }


def _hydrolysis_unit(coordinator: NeoPoolCoordinator) -> str:
    # Debounced in the coordinator: a single telemetry message can carry the wrong
    # unit, and a unit change suppresses Home Assistant's long-term statistics.
    return coordinator.hydrolysis_unit


def _filtration_speed(data: dict[str, Any]) -> Any:
    speed = (data.get("Filtration") or {}).get("Speed")
    return FILTRATION_SPEEDS.get(speed, speed)


def _filtration_speed_actual(coordinator: NeoPoolCoordinator) -> str | None:
    """The speed the panel is really driving, decoded from the relay lines.

    Tasmota's own Speed field is unreliable on pumps whose speed lines are wired
    additively: it only recognises one-hot combinations and silently reports the
    configured default speed for anything else. See const.filtration_speed_from_relays.
    """
    return FILTRATION_SPEEDS.get(coordinator.filtration_speed)


def _filtration_mode(data: dict[str, Any]) -> Any:
    mode = (data.get("Filtration") or {}).get("Mode")
    if mode is None:
        return None
    return FILTRATION_MODES.get(mode, f"Unknown ({mode})")


def _mb_error_rate(data: dict[str, Any]) -> float | None:
    """Derived Modbus error rate (%) = (MBRequests - MBNoError) / MBRequests * 100."""
    conn = data.get("Connection") or {}
    requests = conn.get("MBRequests")
    no_error = conn.get("MBNoError")
    if not isinstance(requests, (int, float)) or not isinstance(no_error, (int, float)):
        return None
    if requests <= 0:
        return None
    return round((requests - no_error) / requests * 100, 3)


SENSORS: tuple[NeoPoolSensorDescription, ...] = (
    NeoPoolSensorDescription(
        key="temperature",
        name="Water Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=_path("Temperature"),
    ),
    NeoPoolSensorDescription(
        key="ph_data",
        name="pH",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:ph",
        value_fn=_path("pH", "Data"),
        extra_attrs_fn=_ph_extra,
    ),
    NeoPoolSensorDescription(
        key="ph_state",
        name="pH State",
        icon="mdi:alert-circle-outline",
        value_fn=_ph_state,
    ),
    NeoPoolSensorDescription(
        key="ph_pump",
        name="pH Pump",
        icon="mdi:pump",
        value_fn=_ph_pump,
    ),
    NeoPoolSensorDescription(
        key="ph_tank",
        name="pH Tank",
        icon="mdi:cup-water",
        value_fn=_ph_tank,
    ),
    NeoPoolSensorDescription(
        key="redox_data",
        name="Redox (ORP)",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        icon="mdi:flash",
        value_fn=_path("Redox", "Data"),
    ),
    NeoPoolSensorDescription(
        key="redox_setpoint",
        name="Redox Setpoint",
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        icon="mdi:flash-outline",
        value_fn=_path("Redox", "Setpoint"),
    ),
    NeoPoolSensorDescription(
        key="hydrolysis_data",
        name="Hydrolysis Level",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-percent",
        value_fn=_path("Hydrolysis", "Data"),
        unit_fn=_hydrolysis_unit,
    ),
    NeoPoolSensorDescription(
        key="hydrolysis_setpoint_sensor",
        name="Hydrolysis Setpoint (sensor)",
        icon="mdi:water-percent",
        entity_registry_enabled_default=False,
        value_fn=_path("Hydrolysis", "Setpoint"),
        unit_fn=_hydrolysis_unit,
    ),
    NeoPoolSensorDescription(
        key="hydrolysis_state",
        name="Hydrolysis State",
        icon="mdi:state-machine",
        value_fn=_hydrolysis_state,
        extra_attrs_fn=_hydrolysis_extra,
    ),
    NeoPoolSensorDescription(
        key="hydrolysis_runtime_total",
        name="Cell Runtime Total",
        icon="mdi:timer-outline",
        value_fn=_path("Hydrolysis", "Runtime", "Total"),
    ),
    NeoPoolSensorDescription(
        key="hydrolysis_runtime_part",
        name="Cell Runtime Part",
        icon="mdi:timer-outline",
        entity_registry_enabled_default=False,
        value_fn=_path("Hydrolysis", "Runtime", "Part"),
    ),
    NeoPoolSensorDescription(
        key="hydrolysis_pol1",
        name="Cell Polarization 1 Runtime",
        icon="mdi:timer-outline",
        entity_registry_enabled_default=False,
        value_fn=_path("Hydrolysis", "Runtime", "Pol1"),
    ),
    NeoPoolSensorDescription(
        key="hydrolysis_pol2",
        name="Cell Polarization 2 Runtime",
        icon="mdi:timer-outline",
        entity_registry_enabled_default=False,
        value_fn=_path("Hydrolysis", "Runtime", "Pol2"),
    ),
    NeoPoolSensorDescription(
        key="hydrolysis_changes",
        name="Polarization Changes",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:swap-horizontal",
        value_fn=_path("Hydrolysis", "Runtime", "Changes"),
    ),
    NeoPoolSensorDescription(
        key="filtration_state_sensor",
        name="Filtration State (sensor)",
        icon="mdi:pump",
        entity_registry_enabled_default=False,
        value_fn=_on_off("Filtration", "State"),
    ),
    NeoPoolSensorDescription(
        key="filtration_speed_sensor",
        name="Filtration Speed (sensor)",
        icon="mdi:speedometer",
        entity_registry_enabled_default=False,
        value_fn=_filtration_speed,
        coordinator_value_fn=_filtration_speed_actual,
    ),
    NeoPoolSensorDescription(
        key="filtration_mode_sensor",
        name="Filtration Mode (sensor)",
        icon="mdi:cog",
        entity_registry_enabled_default=False,
        value_fn=_filtration_mode,
    ),
    *(
        NeoPoolSensorDescription(
            key=f"relay_{i}",
            name=f"Relay {i}",
            icon="mdi:electric-switch",
            value_fn=_relay_state(i),
        )
        for i in range(1, 8)
    ),
    NeoPoolSensorDescription(
        key="relay_acid",
        name="Acid Pump Relay",
        icon="mdi:flask",
        value_fn=_on_off("Relay", "Acid"),
    ),
    NeoPoolSensorDescription(
        key="relay_valve",
        name="Valve Relay",
        icon="mdi:valve",
        value_fn=_on_off("Relay", "Valve"),
    ),
    NeoPoolSensorDescription(
        key="relay_base",
        name="Base Pump Relay",
        icon="mdi:flask-outline",
        value_fn=_on_off("Relay", "Base"),
        available_fn=_relay_present("Base"),
    ),
    NeoPoolSensorDescription(
        key="relay_redox",
        name="Redox Relay",
        icon="mdi:flash",
        value_fn=_on_off("Relay", "Redox"),
        available_fn=_relay_present("Redox"),
    ),
    NeoPoolSensorDescription(
        key="relay_chlorine",
        name="Chlorine Relay",
        icon="mdi:flask-round-bottom",
        value_fn=_on_off("Relay", "Chlorine"),
        available_fn=_relay_present("Chlorine"),
    ),
    NeoPoolSensorDescription(
        key="relay_conductivity",
        name="Conductivity Relay",
        icon="mdi:flash-triangle",
        value_fn=_on_off("Relay", "Conductivity"),
        available_fn=_relay_present("Conductivity"),
    ),
    NeoPoolSensorDescription(
        key="relay_heating",
        name="Heating Relay",
        icon="mdi:radiator",
        value_fn=_on_off("Relay", "Heating"),
        available_fn=_relay_present("Heating"),
    ),
    NeoPoolSensorDescription(
        key="relay_uv",
        name="UV Relay",
        icon="mdi:weather-sunny",
        value_fn=_on_off("Relay", "UV"),
        available_fn=_relay_present("UV"),
    ),
    NeoPoolSensorDescription(
        key="device_type",
        name="Device Type",
        icon="mdi:pool",
        value_fn=_path("Type"),
    ),
    NeoPoolSensorDescription(
        key="firmware_version",
        name="Firmware Version",
        icon="mdi:chip",
        entity_registry_enabled_default=False,
        value_fn=_path("Powerunit", "Version"),
    ),
    NeoPoolSensorDescription(
        key="voltage_5v",
        name="5V Supply",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="V",
        entity_registry_enabled_default=False,
        value_fn=_path("Powerunit", "5V"),
    ),
    NeoPoolSensorDescription(
        key="voltage_12v",
        name="12V Supply",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="V",
        entity_registry_enabled_default=False,
        value_fn=_path("Powerunit", "12V"),
    ),
    NeoPoolSensorDescription(
        key="voltage_24v",
        name="24-30V Supply",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="V",
        entity_registry_enabled_default=False,
        value_fn=_path("Powerunit", "24-30V"),
    ),
    NeoPoolSensorDescription(
        key="current_420ma",
        name="4-20mA Output",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="mA",
        entity_registry_enabled_default=False,
        value_fn=_path("Powerunit", "4-20mA"),
    ),
    NeoPoolSensorDescription(
        key="mb_requests",
        name="Modbus Requests",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:database-arrow-right",
        entity_registry_enabled_default=False,
        value_fn=_path("Connection", "MBRequests"),
    ),
    NeoPoolSensorDescription(
        key="mb_no_error",
        name="Modbus Successful",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:check-circle",
        entity_registry_enabled_default=False,
        value_fn=_path("Connection", "MBNoError"),
    ),
    NeoPoolSensorDescription(
        key="mb_no_response",
        name="Modbus No Response",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:alert",
        entity_registry_enabled_default=False,
        value_fn=_path("Connection", "MBNoResponse"),
    ),
    NeoPoolSensorDescription(
        key="mb_error_rate",
        name="Modbus Error Rate",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:percent",
        entity_registry_enabled_default=False,
        value_fn=_mb_error_rate,
        available_fn=lambda data: _mb_error_rate(data) is not None,
    ),
    NeoPoolSensorDescription(
        key="chlorine_data",
        name="Chlorine",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="ppm",
        icon="mdi:flask-round-bottom",
        value_fn=_path("Chlorine", "Data"),
        available_fn=lambda data: _path("Chlorine", "Data")(data) is not None,
    ),
    NeoPoolSensorDescription(
        key="chlorine_setpoint_sensor",
        name="Chlorine Setpoint (sensor)",
        native_unit_of_measurement="ppm",
        icon="mdi:flask-round-bottom-outline",
        entity_registry_enabled_default=False,
        value_fn=_path("Chlorine", "Setpoint"),
        available_fn=lambda data: data.get("Chlorine") is not None,
    ),
    NeoPoolSensorDescription(
        key="conductivity",
        name="Conductivity",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:flash-triangle",
        value_fn=_path("Conductivity"),
        available_fn=lambda data: data.get("Conductivity") is not None,
    ),
    NeoPoolSensorDescription(
        key="ionization_data",
        name="Ionization",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:atom",
        value_fn=_path("Ionization", "Data"),
        available_fn=lambda data: _path("Ionization", "Data")(data) is not None,
    ),
    NeoPoolSensorDescription(
        key="ionization_setpoint_sensor",
        name="Ionization Setpoint (sensor)",
        icon="mdi:atom-variant",
        entity_registry_enabled_default=False,
        value_fn=_path("Ionization", "Setpoint"),
        available_fn=lambda data: data.get("Ionization") is not None,
    ),
)


# --- Register-backed sensors --------------------------------------------------
# These read NeoPoolCoordinator.registers (filled by NPRead), not the SENSOR JSON.


@dataclass(frozen=True, kw_only=True)
class NeoPoolRegisterSensorDescription(SensorEntityDescription):
    """Description of a sensor backed by raw Modbus registers."""

    value_fn: Callable[[NeoPoolCoordinator], Any]


def _panel_datetime(raw: int | None) -> datetime | None:
    """Convert a panel timestamp to an aware datetime.

    The panel stores local wall-clock time in a field that looks like a unix
    timestamp, so the seconds are read as UTC and then labelled with Home
    Assistant's own timezone. During the DST changeover an hour is ambiguous; that
    is inherent to how the panel stores time, not something we can resolve here.
    """
    if raw is None or raw <= 0:
        return None
    wall_clock = datetime(1970, 1, 1) + timedelta(seconds=raw)
    return wall_clock.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)


def _reg(address: int) -> Callable[[NeoPoolCoordinator], Any]:
    def get(coordinator: NeoPoolCoordinator) -> Any:
        return coordinator.register(address)

    return get


def _backwash_last_start(coordinator: NeoPoolCoordinator) -> datetime | None:
    return _panel_datetime(coordinator.register_long(REG_PAR_FILTVALVE_START))


def _backwash_next_start(coordinator: NeoPoolCoordinator) -> datetime | None:
    """Last cleaning plus the configured period."""
    last = _backwash_last_start(coordinator)
    period = coordinator.register(REG_PAR_FILTVALVE_PERIOD_MINUTES)
    if last is None or not period:
        return None
    return last + timedelta(minutes=period)


def _panel_time(coordinator: NeoPoolCoordinator) -> datetime | None:
    return _panel_datetime(coordinator.register_long(REG_PAR_TIME))


def _panel_clock_drift(coordinator: NeoPoolCoordinator) -> int | None:
    """Seconds the panel clock runs ahead of Home Assistant (negative = behind)."""
    panel = _panel_time(coordinator)
    if panel is None:
        return None
    return round((panel - dt_util.now()).total_seconds())


def _cover_reduction(coordinator: NeoPoolCoordinator) -> int | None:
    value = coordinator.register(REG_PAR_HIDRO_COVER_REDUCTION)
    if value is None:
        return None
    return value & MASK_HIDRO_COVER_REDUCTION


def _cover_shutdown_temp(coordinator: NeoPoolCoordinator) -> int | None:
    value = coordinator.register(REG_PAR_HIDRO_COVER_REDUCTION)
    if value is None:
        return None
    return (value >> 8) & 0xFF


def _pump_time(address: int) -> Callable[[NeoPoolCoordinator], int | None]:
    def get(coordinator: NeoPoolCoordinator) -> int | None:
        return decode_pump_time(coordinator.register(address))

    return get


def _aux_name(index: int) -> Callable[[NeoPoolCoordinator], str | None]:
    address = REG_PAR_UICFG_MACH_NAME_AUX[index - 1]

    def get(coordinator: NeoPoolCoordinator) -> str | None:
        return coordinator.register_string(address, REG_AUX_NAME_LENGTH)

    return get


_DIAG = {
    "entity_category": EntityCategory.DIAGNOSTIC,
    "entity_registry_enabled_default": False,
}

REGISTER_SENSORS: tuple[NeoPoolRegisterSensorDescription, ...] = (
    NeoPoolRegisterSensorDescription(
        key="backwash_remaining",
        name="Backwash Remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        icon="mdi:valve",
        value_fn=_reg(REG_PAR_FILTVALVE_REMAINING),
    ),
    NeoPoolRegisterSensorDescription(
        key="backwash_last_start",
        name="Backwash Last Start",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:valve-open",
        value_fn=_backwash_last_start,
    ),
    NeoPoolRegisterSensorDescription(
        key="backwash_next_start",
        name="Backwash Next Start",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:calendar-clock",
        value_fn=_backwash_next_start,
    ),
    NeoPoolRegisterSensorDescription(
        key="backwash_relay",
        name="Backwash Relay",
        icon="mdi:electric-switch",
        value_fn=_reg(REG_PAR_FILTVALVE_GPIO),
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="input_status_raw",
        name="Input Status Register",
        icon="mdi:import",
        # Hex, because this register is a bit field: bit 8 is the cover, bit 9 the
        # Aux4 relay, bit 5 follows the pump speed. Useful when the cover misreads.
        value_fn=lambda coordinator: (
            None
            if coordinator.register(REG_INPUT_STATUS) is None
            else f"0x{coordinator.register(REG_INPUT_STATUS):04X}"
        ),
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="filtration_speed_bits",
        name="Filtration Speed Relay Lines",
        icon="mdi:numeric",
        value_fn=lambda coordinator: coordinator.filtration_speed_bits,
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="cell_pwm",
        name="Cell PWM Opening",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sine-wave",
        value_fn=_reg(REG_HIDRO_SWITCH_VALUE),
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="cell_voltage",
        name="Cell Voltage (raw)",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash",
        value_fn=_reg(REG_HIDRO_VOLTAGE),
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="panel_time",
        name="Panel Clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
        value_fn=_panel_time,
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="panel_clock_drift",
        name="Panel Clock Drift",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        icon="mdi:clock-alert-outline",
        value_fn=_panel_clock_drift,
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="smart_interval_reduction",
        name="Smart Interval Reduction",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:percent",
        value_fn=_reg(REG_PAR_SMART_INTERVAL_REDUCTION),
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="intelligent_bonus_time",
        name="Intelligent Bonus Time",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:timer-plus-outline",
        value_fn=_reg(REG_PAR_INTELLIGENT_BONUS_TIME),
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="intelligent_next_interval",
        name="Intelligent Time To Next Interval",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:timer-sand",
        value_fn=_reg(REG_PAR_INTELLIGENT_TT_NEXT_INTERVAL),
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="intelligent_intervals",
        name="Intelligent Intervals Started",
        icon="mdi:counter",
        value_fn=_reg(REG_PAR_INTELLIGENT_INTERVALS),
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="cell_pol_positive_time",
        name="Cell Positive Polarization Time",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:swap-horizontal",
        value_fn=_reg(REG_PAR_HIDRO_POL0),
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="cell_pol_negative_time",
        name="Cell Negative Polarization Time",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:swap-horizontal",
        value_fn=_reg(REG_PAR_HIDRO_POL1),
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="cell_pol_dead_time",
        name="Cell Polarization Dead Time",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:timer-off-outline",
        value_fn=_reg(REG_PAR_HIDRO_POL2),
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="cover_reduction_percent",
        name="Cover Reduction",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:shield-sun",
        value_fn=_cover_reduction,
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="cover_shutdown_temp",
        name="Hydrolysis Shutdown Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-low",
        value_fn=_cover_shutdown_temp,
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="dosing_pump_time_on",
        name="Dosing Pump On Time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        icon="mdi:pump",
        value_fn=_pump_time(REG_PAR_PUMP_RELAY_TIME_ON),
        **_DIAG,
    ),
    NeoPoolRegisterSensorDescription(
        key="dosing_pump_time_off",
        name="Dosing Pump Off Time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        icon="mdi:pump-off",
        value_fn=_pump_time(REG_PAR_PUMP_RELAY_TIME_OFF),
        **_DIAG,
    ),
    *(
        NeoPoolRegisterSensorDescription(
            key=f"aux{i}_name",
            name=f"Aux {i} Name",
            icon="mdi:tag-outline",
            value_fn=_aux_name(i),
            **_DIAG,
        )
        for i in range(1, 5)
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NeoPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[SensorEntity] = [NeoPoolSensor(coordinator, desc) for desc in SENSORS]
    entities += [
        NeoPoolRegisterSensor(coordinator, desc) for desc in REGISTER_SENSORS
    ]
    entities.append(NeoPoolBerryVersionSensor(coordinator))
    async_add_entities(entities)


class NeoPoolSensor(NeoPoolEntity, SensorEntity):
    """Generic NeoPool sensor driven by an entity description."""

    entity_description: NeoPoolSensorDescription

    def __init__(
        self, coordinator: NeoPoolCoordinator, description: NeoPoolSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key, description.name)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        if self.entity_description.coordinator_value_fn is not None:
            return self.entity_description.coordinator_value_fn(self.coordinator)
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.unit_fn is not None:
            return self.entity_description.unit_fn(self.coordinator)
        return self.entity_description.native_unit_of_measurement

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        if self.entity_description.available_fn is not None:
            return self.entity_description.available_fn(self.coordinator.data)
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.extra_attrs_fn is None:
            return None
        return self.entity_description.extra_attrs_fn(self.coordinator.data)


class NeoPoolBerryVersionSensor(NeoPoolEntity, SensorEntity):
    """Berry driver (neopoolcmd.be) version (Fase 4, diagnostic).

    Populated from the NPVersion RESULT, which the coordinator requests once at
    setup when the Berry option is enabled. Default-disabled; unavailable on devices
    without the Berry script (no NPVersion RESULT).
    """

    _attr_icon = "mdi:script-text"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: NeoPoolCoordinator) -> None:
        super().__init__(coordinator, "berry_version", "Berry Version")

    @property
    def native_value(self) -> str | None:
        return self.coordinator.berry_version

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.berry_version is not None


class NeoPoolRegisterSensor(NeoPoolEntity, SensorEntity):
    """Sensor backed by a raw Modbus register read with NPRead.

    Unavailable until the register has actually been read, so a device that never
    answers an NPRead shows "unavailable" rather than a silent "unknown".
    """

    entity_description: NeoPoolRegisterSensorDescription

    def __init__(
        self,
        coordinator: NeoPoolCoordinator,
        description: NeoPoolRegisterSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key, description.name)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator)

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None
