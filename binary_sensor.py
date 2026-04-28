"""Binary sensor platform for NeoPool MQTT Controller."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import NeoPoolEntity
from .coordinator import NeoPoolCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NeoPool binary sensors from config entry."""
    coordinator: NeoPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        NeoPoolPHAlarmBinarySensor(coordinator),
        NeoPoolPHTankEmptyBinarySensor(coordinator),
        NeoPoolPHFlowBinarySensor(coordinator),
        NeoPoolHydrolysisFlowAlarmBinarySensor(coordinator),
        NeoPoolHydrolysisLowAlarmBinarySensor(coordinator),
        NeoPoolHydrolysisCoverBinarySensor(coordinator),
        NeoPoolFiltrationRunningBinarySensor(coordinator),
    ]

    async_add_entities(entities)


class NeoPoolBinarySensor(NeoPoolEntity, BinarySensorEntity):
    """Base NeoPool binary sensor."""

    def __init__(self, coordinator, key, name, **kwargs):
        super().__init__(coordinator, key, name)
        self._attr_device_class = kwargs.get("device_class")
        self._attr_icon = kwargs.get("icon")
        self._attr_entity_registry_enabled_default = kwargs.get("enabled_default", True)


class NeoPoolPHAlarmBinarySensor(NeoPoolBinarySensor):
    """pH alarm state."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "ph_alarm", "pH Alarm",
                         device_class=BinarySensorDeviceClass.PROBLEM,
                         icon="mdi:alert")

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.data.get("pH", {}).get("State")
        return state is not None and state != 0


class NeoPoolPHTankEmptyBinarySensor(NeoPoolBinarySensor):
    """pH tank empty alarm."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "ph_tank_empty", "pH Tank Empty",
                         device_class=BinarySensorDeviceClass.PROBLEM,
                         icon="mdi:cup-water")

    @property
    def is_on(self) -> bool | None:
        tank = self.coordinator.data.get("pH", {}).get("Tank")
        return tank == 0 if tank is not None else None


class NeoPoolPHFlowBinarySensor(NeoPoolBinarySensor):
    """pH flow detection."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "ph_flow", "pH Flow Detection",
                         icon="mdi:waves")

    @property
    def is_on(self) -> bool | None:
        fl1 = self.coordinator.data.get("pH", {}).get("FL1")
        return fl1 == 1 if fl1 is not None else None


class NeoPoolHydrolysisFlowAlarmBinarySensor(NeoPoolBinarySensor):
    """Hydrolysis flow alarm."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "hydrolysis_flow_alarm", "Hydrolysis Flow Alarm",
                         device_class=BinarySensorDeviceClass.PROBLEM,
                         icon="mdi:waves-arrow-up")

    @property
    def is_on(self) -> bool | None:
        fl1 = self.coordinator.data.get("Hydrolysis", {}).get("FL1")
        return fl1 == 1 if fl1 is not None else None


class NeoPoolHydrolysisLowAlarmBinarySensor(NeoPoolBinarySensor):
    """Hydrolysis low production alarm."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "hydrolysis_low_alarm", "Hydrolysis Low Alarm",
                         device_class=BinarySensorDeviceClass.PROBLEM,
                         icon="mdi:alert-circle")

    @property
    def is_on(self) -> bool | None:
        low = self.coordinator.data.get("Hydrolysis", {}).get("Low")
        return low == 1 if low is not None else None


class NeoPoolHydrolysisCoverBinarySensor(NeoPoolBinarySensor):
    """Pool cover active."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "cover_active", "Cover Active",
                         icon="mdi:shield-sun")

    @property
    def is_on(self) -> bool | None:
        cover = self.coordinator.data.get("Hydrolysis", {}).get("Cover")
        return cover == 1 if cover is not None else None


class NeoPoolFiltrationRunningBinarySensor(NeoPoolBinarySensor):
    """Filtration pump running."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "filtration_running", "Filtration Running",
                         device_class=BinarySensorDeviceClass.RUNNING,
                         icon="mdi:pump")

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.data.get("Filtration", {}).get("State")
        return state == 1 if state is not None else None
