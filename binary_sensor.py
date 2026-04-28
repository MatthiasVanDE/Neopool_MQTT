"""Binary sensor platform for NeoPool MQTT Controller."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NeoPoolCoordinator
from .entity import NeoPoolEntity


@dataclass(frozen=True, kw_only=True)
class NeoPoolBinarySensorDescription(BinarySensorEntityDescription):
    """Description of a NeoPool binary sensor."""

    is_on_fn: Callable[[dict[str, Any]], bool | None]


def _ph_alarm(data: dict[str, Any]) -> bool | None:
    state = (data.get("pH") or {}).get("State")
    return state is not None and state != 0


def _eq(path: tuple[str, ...], target: int) -> Callable[[dict[str, Any]], bool | None]:
    def get(data: dict[str, Any]) -> bool | None:
        node: Any = data
        for key in path:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        if node is None:
            return None
        return node == target

    return get


BINARY_SENSORS: tuple[NeoPoolBinarySensorDescription, ...] = (
    NeoPoolBinarySensorDescription(
        key="ph_alarm",
        name="pH Alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert",
        is_on_fn=_ph_alarm,
    ),
    NeoPoolBinarySensorDescription(
        key="ph_tank_empty",
        name="pH Tank Empty",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:cup-water",
        is_on_fn=_eq(("pH", "Tank"), 0),
    ),
    NeoPoolBinarySensorDescription(
        key="ph_flow",
        name="pH Flow Detection",
        icon="mdi:waves",
        is_on_fn=_eq(("pH", "FL1"), 1),
    ),
    NeoPoolBinarySensorDescription(
        key="hydrolysis_flow_alarm",
        name="Hydrolysis Flow Alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:waves-arrow-up",
        is_on_fn=_eq(("Hydrolysis", "FL1"), 1),
    ),
    NeoPoolBinarySensorDescription(
        key="hydrolysis_low_alarm",
        name="Hydrolysis Low Alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert-circle",
        is_on_fn=_eq(("Hydrolysis", "Low"), 1),
    ),
    NeoPoolBinarySensorDescription(
        key="cover_active",
        name="Cover Active",
        icon="mdi:shield-sun",
        is_on_fn=_eq(("Hydrolysis", "Cover"), 1),
    ),
    NeoPoolBinarySensorDescription(
        key="filtration_running",
        name="Filtration Running",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        is_on_fn=_eq(("Filtration", "State"), 1),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NeoPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        NeoPoolBinarySensor(coordinator, desc) for desc in BINARY_SENSORS
    )


class NeoPoolBinarySensor(NeoPoolEntity, BinarySensorEntity):
    """Generic NeoPool binary sensor driven by a description."""

    entity_description: NeoPoolBinarySensorDescription

    def __init__(
        self,
        coordinator: NeoPoolCoordinator,
        description: NeoPoolBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key, description.name)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.is_on_fn(self.coordinator.data)
