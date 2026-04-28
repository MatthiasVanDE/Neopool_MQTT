"""Base entity for NeoPool MQTT Controller."""
from __future__ import annotations

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.core import callback

from .const import DOMAIN
from .coordinator import NeoPoolCoordinator, SIGNAL_NEOPOOL_UPDATE


class NeoPoolEntity(Entity):
    """Base class for NeoPool entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NeoPoolCoordinator, key: str, name: str) -> None:
        """Initialize the entity."""
        self.coordinator = coordinator
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.mqtt_topic}_{key}"

    @property
    def device_info(self):
        """Return device info."""
        return self.coordinator.device_info

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.available

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_NEOPOOL_UPDATE}_{self.coordinator.entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        """Handle updated data."""
        self.async_write_ha_state()
