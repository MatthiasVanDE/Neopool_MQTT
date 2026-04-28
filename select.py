"""Select platform for NeoPool MQTT Controller."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CMD_NPFILTRATIONMODE,
    CMD_NPFILTRATIONSPEED,
    CMD_NPBOOST,
    FILTRATION_MODES,
    FILTRATION_MODES_REVERSE,
    FILTRATION_SPEEDS,
    FILTRATION_SPEEDS_REVERSE,
    BOOST_MODES,
    BOOST_MODES_REVERSE,
)
from .entity import NeoPoolEntity
from .coordinator import NeoPoolCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NeoPool selects from config entry."""
    coordinator: NeoPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        NeoPoolFiltrationModeSelect(coordinator),
        NeoPoolFiltrationSpeedSelect(coordinator),
        NeoPoolBoostModeSelect(coordinator),
    ]

    async_add_entities(entities)


class NeoPoolFiltrationModeSelect(NeoPoolEntity, SelectEntity):
    """Filtration mode select."""

    _attr_icon = "mdi:cog"

    def __init__(self, coordinator):
        super().__init__(coordinator, "filtration_mode", "Filtration Mode")
        self._attr_options = list(FILTRATION_MODES.values())

    @property
    def current_option(self) -> str | None:
        mode = self.coordinator.data.get("Filtration", {}).get("Mode")
        return FILTRATION_MODES.get(mode)

    async def async_select_option(self, option: str) -> None:
        mode_int = FILTRATION_MODES_REVERSE.get(option)
        if mode_int is not None:
            await self.coordinator.async_send_command(CMD_NPFILTRATIONMODE, str(mode_int))


class NeoPoolFiltrationSpeedSelect(NeoPoolEntity, SelectEntity):
    """Filtration speed select."""

    _attr_icon = "mdi:speedometer"

    def __init__(self, coordinator):
        super().__init__(coordinator, "filtration_speed", "Filtration Speed")
        self._attr_options = list(FILTRATION_SPEEDS.values())

    @property
    def current_option(self) -> str | None:
        speed = self.coordinator.data.get("Filtration", {}).get("Speed")
        return FILTRATION_SPEEDS.get(speed)

    async def async_select_option(self, option: str) -> None:
        speed_int = FILTRATION_SPEEDS_REVERSE.get(option)
        if speed_int is not None:
            await self.coordinator.async_send_command(CMD_NPFILTRATIONSPEED, str(speed_int))


class NeoPoolBoostModeSelect(NeoPoolEntity, SelectEntity):
    """Boost mode select."""

    _attr_icon = "mdi:rocket-launch"

    def __init__(self, coordinator):
        super().__init__(coordinator, "boost_mode", "Boost Mode")
        self._attr_options = list(BOOST_MODES.values())

    @property
    def current_option(self) -> str | None:
        boost = self.coordinator.data.get("Hydrolysis", {}).get("Boost")
        return BOOST_MODES.get(boost)

    async def async_select_option(self, option: str) -> None:
        boost_int = BOOST_MODES_REVERSE.get(option)
        if boost_int is not None:
            await self.coordinator.async_send_command(CMD_NPBOOST, str(boost_int))
