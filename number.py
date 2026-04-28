"""Number platform for NeoPool MQTT Controller."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CMD_NPPHMIN,
    CMD_NPPHMAX,
    CMD_NPREDOX,
    CMD_NPHYDROLYSIS,
    CMD_NPIONIZATION,
    CMD_NPCHLORINE,
)
from .entity import NeoPoolEntity
from .coordinator import NeoPoolCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NeoPool numbers from config entry."""
    coordinator: NeoPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        NeoPoolPHMinNumber(coordinator),
        NeoPoolPHMaxNumber(coordinator),
        NeoPoolRedoxSetpointNumber(coordinator),
        NeoPoolHydrolysisSetpointNumber(coordinator),
        NeoPoolIonizationSetpointNumber(coordinator),
        NeoPoolChlorineSetpointNumber(coordinator),
    ]

    async_add_entities(entities)


class NeoPoolNumber(NeoPoolEntity, NumberEntity):
    """Base NeoPool number."""

    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, key, name, command, **kwargs):
        super().__init__(coordinator, key, name)
        self._command = command
        self._attr_native_min_value = kwargs.get("min_value", 0)
        self._attr_native_max_value = kwargs.get("max_value", 100)
        self._attr_native_step = kwargs.get("step", 0.1)
        self._attr_native_unit_of_measurement = kwargs.get("unit")
        self._attr_icon = kwargs.get("icon")
        self._attr_entity_registry_enabled_default = kwargs.get("enabled_default", True)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self.coordinator.async_send_command(self._command, str(value))


class NeoPoolPHMinNumber(NeoPoolNumber):
    """pH minimum setpoint."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "ph_min", "pH Min Setpoint",
                         CMD_NPPHMIN,
                         min_value=0.0, max_value=14.0, step=0.1,
                         icon="mdi:ph")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("pH", {}).get("Min")


class NeoPoolPHMaxNumber(NeoPoolNumber):
    """pH maximum setpoint."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "ph_max", "pH Max Setpoint",
                         CMD_NPPHMAX,
                         min_value=0.0, max_value=14.0, step=0.1,
                         icon="mdi:ph")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("pH", {}).get("Max")


class NeoPoolRedoxSetpointNumber(NeoPoolNumber):
    """Redox setpoint."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "redox_setpoint_number", "Redox Setpoint",
                         CMD_NPREDOX,
                         min_value=0, max_value=1000, step=1,
                         unit="mV",
                         icon="mdi:flash")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("Redox", {}).get("Setpoint")


class NeoPoolHydrolysisSetpointNumber(NeoPoolNumber):
    """Hydrolysis setpoint."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "hydrolysis_setpoint", "Hydrolysis Setpoint",
                         CMD_NPHYDROLYSIS,
                         min_value=0, max_value=100, step=1,
                         icon="mdi:water-percent")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("Hydrolysis", {}).get("Setpoint")

    @property
    def native_unit_of_measurement(self):
        unit = self.coordinator.data.get("Hydrolysis", {}).get("Unit")
        return unit if unit else "%"

    @property
    def native_max_value(self):
        return self.coordinator.data.get("Hydrolysis", {}).get("Max", 100)


class NeoPoolIonizationSetpointNumber(NeoPoolNumber):
    """Ionization setpoint."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "ionization_setpoint", "Ionization Setpoint",
                         CMD_NPIONIZATION,
                         min_value=0, max_value=100, step=1,
                         icon="mdi:atom")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("Ionization", {}).get("Setpoint")

    @property
    def native_max_value(self):
        return self.coordinator.data.get("Ionization", {}).get("Max", 100)

    @property
    def available(self):
        return super().available and self.coordinator.data.get("Ionization") is not None


class NeoPoolChlorineSetpointNumber(NeoPoolNumber):
    """Chlorine setpoint."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "chlorine_setpoint", "Chlorine Setpoint",
                         CMD_NPCHLORINE,
                         min_value=0.0, max_value=10.0, step=0.1,
                         unit="ppm",
                         icon="mdi:flask-round-bottom")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("Chlorine", {}).get("Setpoint")

    @property
    def available(self):
        return super().available and self.coordinator.data.get("Chlorine") is not None
