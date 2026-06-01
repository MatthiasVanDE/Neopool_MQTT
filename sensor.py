"""Sensor platform for NeoPool MQTT Controller."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    FILTRATION_MODES,
    FILTRATION_SPEEDS,
    HYDROLYSIS_STATES,
    PH_STATES,
)
from .coordinator import NeoPoolCoordinator
from .entity import NeoPoolEntity


@dataclass(frozen=True, kw_only=True)
class NeoPoolSensorDescription(SensorEntityDescription):
    """Description of a NeoPool sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    available_fn: Callable[[dict[str, Any]], bool] | None = None
    extra_attrs_fn: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None
    unit_fn: Callable[[dict[str, Any]], str | None] | None = None


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


def _hydrolysis_unit(data: dict[str, Any]) -> str:
    unit = (data.get("Hydrolysis") or {}).get("Unit")
    return unit if unit else PERCENTAGE


def _filtration_speed(data: dict[str, Any]) -> Any:
    speed = (data.get("Filtration") or {}).get("Speed")
    return FILTRATION_SPEEDS.get(speed, speed)


def _filtration_mode(data: dict[str, Any]) -> Any:
    mode = (data.get("Filtration") or {}).get("Mode")
    if mode is None:
        return None
    return FILTRATION_MODES.get(mode, f"Unknown ({mode})")


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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NeoPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(NeoPoolSensor(coordinator, desc) for desc in SENSORS)


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
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.unit_fn is not None:
            return self.entity_description.unit_fn(self.coordinator.data)
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
