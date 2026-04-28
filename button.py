"""Button platform for NeoPool MQTT Controller."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CMD_NPESCAPE,
    CMD_NPTIME,
    CMD_NPSAVE,
    CMD_NPEXEC,
)
from .entity import NeoPoolEntity
from .coordinator import NeoPoolCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NeoPool buttons from config entry."""
    coordinator: NeoPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        NeoPoolTimeSyncButton(coordinator),
        NeoPoolClearErrorsButton(coordinator),
        NeoPoolSaveButton(coordinator),
        NeoPoolExecButton(coordinator),
    ]

    async_add_entities(entities)


class NeoPoolTimeSyncButton(NeoPoolEntity, ButtonEntity):
    """Sync device time with Tasmota."""

    _attr_icon = "mdi:clock-check"

    def __init__(self, coordinator):
        super().__init__(coordinator, "time_sync", "Sync Time")

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(CMD_NPTIME, "0")


class NeoPoolClearErrorsButton(NeoPoolEntity, ButtonEntity):
    """Clear device errors."""

    _attr_icon = "mdi:alert-remove"

    def __init__(self, coordinator):
        super().__init__(coordinator, "clear_errors", "Clear Errors")

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(CMD_NPESCAPE, "")


class NeoPoolSaveButton(NeoPoolEntity, ButtonEntity):
    """Save settings to EEPROM."""

    _attr_icon = "mdi:content-save"

    def __init__(self, coordinator):
        super().__init__(coordinator, "save_eeprom", "Save to EEPROM")
        self._attr_entity_registry_enabled_default = False

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(CMD_NPSAVE, "")


class NeoPoolExecButton(NeoPoolEntity, ButtonEntity):
    """Execute pending changes."""

    _attr_icon = "mdi:play-circle"

    def __init__(self, coordinator):
        super().__init__(coordinator, "exec", "Execute Changes")
        self._attr_entity_registry_enabled_default = False

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(CMD_NPEXEC, "")
