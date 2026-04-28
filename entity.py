"""Base entity for NeoPool MQTT Controller."""
from __future__ import annotations

from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .coordinator import NeoPoolCoordinator


class NeoPoolEntity(Entity):
    """Base class for NeoPool entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: NeoPoolCoordinator, key: str, name: str) -> None:
        self.coordinator = coordinator
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.mqtt_topic}_{key}"

    @property
    def device_info(self) -> dict[str, Any]:
        return self.coordinator.device_info

    @property
    def available(self) -> bool:
        return self.coordinator.available

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self.coordinator.signal, self._handle_update
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    def _get(self, *path: str) -> Any:
        """Read a nested value from coordinator.data, returning None if missing."""
        data: Any = self.coordinator.data
        for key in path:
            if not isinstance(data, dict):
                return None
            data = data.get(key)
        return data
