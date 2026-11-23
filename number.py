"""Number platform for NeoPool MQTT Controller."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_NPCHLORINE,
    CMD_NPEXEC,
    CMD_NPHYDROLYSIS,
    CMD_NPIONIZATION,
    CMD_NPPHMAX,
    CMD_NPPHMIN,
    CMD_NPREDOX,
    CMD_NPWRITE,
    DOMAIN,
    FILTRATION_MODE_INTELLIGENT,
    FILTRATION_MODE_SMART,
    REG_HEATING_TEMP,
    REG_PAR_FILTVALVE_INTERVAL,
    REG_PAR_FILTVALVE_PERIOD_MINUTES,
    REG_PAR_INTELLIGENT_FILT_MIN_TIME,
    REG_PAR_INTELLIGENT_TEMP,
    REG_PAR_RELAY_MAX_TIME,
    REG_PAR_SMART_TEMP_HIGH,
    REG_PAR_SMART_TEMP_LOW,
)
from .coordinator import NeoPoolCoordinator
from .entity import NeoPoolEntity


@dataclass(frozen=True, kw_only=True)
class NeoPoolNumberDescription(NumberEntityDescription):
    """Description of a NeoPool number entity."""

    command: str
    value_fn: Callable[[dict[str, Any]], Any]
    is_integer: bool = False
    max_fn: Callable[[dict[str, Any]], float] | None = None
    unit_fn: Callable[["NeoPoolCoordinator"], str | None] | None = None
    available_fn: Callable[[dict[str, Any]], bool] | None = None


def _path(*keys: str) -> Callable[[dict[str, Any]], Any]:
    def get(data: dict[str, Any]) -> Any:
        node: Any = data
        for key in keys:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        return node

    return get


def _hydrolysis_unit(coordinator: NeoPoolCoordinator) -> str:
    # Debounced in the coordinator: a single telemetry message can carry the wrong
    # unit, and a unit change suppresses Home Assistant's long-term statistics.
    return coordinator.hydrolysis_unit


def _hydrolysis_max(data: dict[str, Any]) -> float:
    return (data.get("Hydrolysis") or {}).get("Max") or 100


def _ionization_max(data: dict[str, Any]) -> float:
    return (data.get("Ionization") or {}).get("Max") or 100


NUMBERS: tuple[NeoPoolNumberDescription, ...] = (
    NeoPoolNumberDescription(
        key="ph_min",
        name="pH Min Setpoint",
        command=CMD_NPPHMIN,
        native_min_value=0.0,
        native_max_value=14.0,
        native_step=0.1,
        icon="mdi:ph",
        value_fn=_path("pH", "Min"),
    ),
    NeoPoolNumberDescription(
        key="ph_max",
        name="pH Max Setpoint",
        command=CMD_NPPHMAX,
        native_min_value=0.0,
        native_max_value=14.0,
        native_step=0.1,
        icon="mdi:ph",
        value_fn=_path("pH", "Max"),
    ),
    NeoPoolNumberDescription(
        key="redox_setpoint_number",
        name="Redox Setpoint",
        command=CMD_NPREDOX,
        native_min_value=0,
        native_max_value=1000,
        native_step=1,
        native_unit_of_measurement="mV",
        icon="mdi:flash",
        value_fn=_path("Redox", "Setpoint"),
        is_integer=True,
    ),
    NeoPoolNumberDescription(
        key="hydrolysis_setpoint",
        name="Hydrolysis Setpoint",
        command=CMD_NPHYDROLYSIS,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        icon="mdi:water-percent",
        value_fn=_path("Hydrolysis", "Setpoint"),
        is_integer=True,
        max_fn=_hydrolysis_max,
        unit_fn=_hydrolysis_unit,
    ),
    NeoPoolNumberDescription(
        key="ionization_setpoint",
        name="Ionization Setpoint",
        command=CMD_NPIONIZATION,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        icon="mdi:atom",
        value_fn=_path("Ionization", "Setpoint"),
        is_integer=True,
        max_fn=_ionization_max,
        available_fn=lambda data: data.get("Ionization") is not None,
    ),
    NeoPoolNumberDescription(
        key="chlorine_setpoint",
        name="Chlorine Setpoint",
        command=CMD_NPCHLORINE,
        native_min_value=0.0,
        native_max_value=10.0,
        native_step=0.1,
        native_unit_of_measurement="ppm",
        icon="mdi:flask-round-bottom",
        value_fn=_path("Chlorine", "Setpoint"),
        available_fn=lambda data: data.get("Chlorine") is not None,
    ),
)


# --- Register-backed numbers --------------------------------------------------
# Installer settings that Tasmota does not publish in its SENSOR JSON. Each one
# reads back from the register cache and writes with NPWrite + NPExec, so the value
# shown is what the panel stored, not what we asked for. Writes are RAM-only: use
# the "Save to EEPROM" button to make them survive a power cycle.


@dataclass(frozen=True, kw_only=True)
class NeoPoolRegisterNumberDescription(NumberEntityDescription):
    """Description of a number entity backed by one raw Modbus register."""

    register: int
    # Filtration mode the panel has to be in for this parameter to mean anything.
    # None means it always applies.
    requires_mode: int | None = None


REGISTER_NUMBERS: tuple[NeoPoolRegisterNumberDescription, ...] = (
    NeoPoolRegisterNumberDescription(
        key="smart_temp_high",
        requires_mode=FILTRATION_MODE_SMART,
        name="Smart Mode Upper Temperature",
        register=REG_PAR_SMART_TEMP_HIGH,
        native_min_value=0,
        native_max_value=40,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-high",
    ),
    NeoPoolRegisterNumberDescription(
        key="smart_temp_low",
        requires_mode=FILTRATION_MODE_SMART,
        name="Smart Mode Lower Temperature",
        register=REG_PAR_SMART_TEMP_LOW,
        native_min_value=0,
        native_max_value=40,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-low",
    ),
    NeoPoolRegisterNumberDescription(
        key="intelligent_temp",
        requires_mode=FILTRATION_MODE_INTELLIGENT,
        name="Intelligent Mode Temperature",
        register=REG_PAR_INTELLIGENT_TEMP,
        native_min_value=0,
        native_max_value=40,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
    ),
    NeoPoolRegisterNumberDescription(
        key="intelligent_filt_min_time",
        requires_mode=FILTRATION_MODE_INTELLIGENT,
        name="Intelligent Mode Minimum Filtration Time",
        register=REG_PAR_INTELLIGENT_FILT_MIN_TIME,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:timer-cog-outline",
    ),
    NeoPoolRegisterNumberDescription(
        key="backwash_period",
        name="Backwash Period",
        register=REG_PAR_FILTVALVE_PERIOD_MINUTES,
        native_min_value=0,
        native_max_value=43200,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:calendar-clock",
    ),
    NeoPoolRegisterNumberDescription(
        key="backwash_duration",
        name="Backwash Duration",
        register=REG_PAR_FILTVALVE_INTERVAL,
        native_min_value=0,
        native_max_value=600,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        icon="mdi:valve-open",
    ),
    NeoPoolRegisterNumberDescription(
        key="dosing_pump_max_time",
        name="Dosing Pump Maximum Run Time",
        register=REG_PAR_RELAY_MAX_TIME,
        native_min_value=0,
        native_max_value=3600,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        icon="mdi:pump-alert",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NeoPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[NumberEntity] = [
        NeoPoolNumber(coordinator, desc) for desc in NUMBERS
    ]
    entities += [
        NeoPoolRegisterNumber(coordinator, desc) for desc in REGISTER_NUMBERS
    ]
    entities.append(NeoPoolHeatingSetpointNumber(coordinator))
    async_add_entities(entities)


class NeoPoolNumber(NeoPoolEntity, NumberEntity):
    """Generic NeoPool number entity driven by a description."""

    entity_description: NeoPoolNumberDescription
    _attr_mode = NumberMode.BOX

    def __init__(
        self, coordinator: NeoPoolCoordinator, description: NeoPoolNumberDescription
    ) -> None:
        super().__init__(coordinator, description.key, description.name)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def native_max_value(self) -> float:
        if self.entity_description.max_fn is not None:
            return self.entity_description.max_fn(self.coordinator.data)
        return self.entity_description.native_max_value

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

    async def async_set_native_value(self, value: float) -> None:
        if self.entity_description.is_integer:
            payload = str(int(round(value)))
        else:
            payload = f"{value:g}"
        await self.coordinator.async_send_command(
            self.entity_description.command, payload
        )


class NeoPoolHeatingSetpointNumber(NeoPoolEntity, NumberEntity):
    """Experimental heating setpoint (Fase 2.4).

    WARNING: this writes a low-level Modbus register (MBF_PAR_HEATING_TEMP, 0x0416)
    via NPWrite + NPExec. It is default-disabled and only available when a Heating
    relay function is reported. Verify the register address and value scaling for
    your specific model before enabling. Changes are applied to RAM (NPExec); they
    are NOT persisted (no NPSave) to protect the EEPROM. The heating setpoint is not
    present in the SENSOR JSON, so the value shown reflects the last value set here.
    """

    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 40
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: NeoPoolCoordinator) -> None:
        super().__init__(coordinator, "heating_setpoint", "Heating Setpoint")
        self._optimistic_value: float | None = None

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return (self.coordinator.data.get("Relay") or {}).get("Heating") is not None

    @property
    def native_value(self) -> float | None:
        return self._optimistic_value

    async def async_set_native_value(self, value: float) -> None:
        degrees = int(round(value))
        # NPWrite <register> <value> writes to RAM; NPExec activates without NPSave.
        await self.coordinator.async_send_command(
            CMD_NPWRITE, f"{REG_HEATING_TEMP} {degrees}"
        )
        await self.coordinator.async_send_command(CMD_NPEXEC)
        self._optimistic_value = degrees
        self.async_write_ha_state()


class NeoPoolRegisterNumber(NeoPoolEntity, NumberEntity):
    """Installer setting stored in one raw Modbus register.

    Reads from the register cache and writes with NPWrite + NPExec (RAM only, no
    NPSave). Default-disabled and categorised as configuration: these are panel
    settings, not day-to-day controls.
    """

    entity_description: NeoPoolRegisterNumberDescription
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: NeoPoolCoordinator,
        description: NeoPoolRegisterNumberDescription,
    ) -> None:
        super().__init__(coordinator, description.key, description.name)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.coordinator.register(self.entity_description.register)

    @property
    def available(self) -> bool:
        if not super().available or self.native_value is None:
            return False
        # The panel consults the Smart block only in Smart mode and the Intelligent
        # block only in Intelligent mode; in any other mode these parameters sit
        # there doing nothing. Mode not read yet does not count as a mismatch.
        requires = self.entity_description.requires_mode
        if requires is not None and self.coordinator.filtration_mode not in (
            None,
            requires,
        ):
            return False
        return True

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write_register(
            self.entity_description.register, int(round(value))
        )
