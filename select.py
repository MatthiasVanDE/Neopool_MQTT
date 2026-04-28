"""Select platform for NeoPool MQTT Controller."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BOOST_MODES,
    BOOST_MODES_REVERSE,
    CMD_NPBOOST,
    CMD_NPFILTRATIONMODE,
    CMD_NPFILTRATIONSPEED,
    DOMAIN,
    FILTRATION_MODE_MANUAL,
    FILTRATION_MODES,
    FILTRATION_MODES_REVERSE,
    FILTRATION_SPEEDS,
    FILTRATION_SPEEDS_REVERSE,
)
from .coordinator import NeoPoolCoordinator
from .entity import NeoPoolEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NeoPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            NeoPoolFiltrationModeSelect(coordinator),
            NeoPoolFiltrationSpeedSelect(coordinator),
            NeoPoolBoostModeSelect(coordinator),
        ]
    )


class NeoPoolFiltrationModeSelect(NeoPoolEntity, SelectEntity):
    _attr_icon = "mdi:cog"

    def __init__(self, coordinator: NeoPoolCoordinator) -> None:
        super().__init__(coordinator, "filtration_mode", "Filtration Mode")
        self._attr_options = list(FILTRATION_MODES.values())

    @property
    def current_option(self) -> str | None:
        return FILTRATION_MODES.get(self._get("Filtration", "Mode"))

    async def async_select_option(self, option: str) -> None:
        mode = FILTRATION_MODES_REVERSE.get(option)
        if mode is not None:
            await self.coordinator.async_send_command(CMD_NPFILTRATIONMODE, str(mode))


class NeoPoolFiltrationSpeedSelect(NeoPoolEntity, SelectEntity):
    """Filtration speed select.

    NPFiltrationspeed only applies when filtration mode = Manual on the device.
    To make picking a speed actually do something, switch the device into Manual
    mode first when needed.
    """

    _attr_icon = "mdi:speedometer"

    def __init__(self, coordinator: NeoPoolCoordinator) -> None:
        super().__init__(coordinator, "filtration_speed", "Filtration Speed")
        self._attr_options = list(FILTRATION_SPEEDS.values())

    @property
    def current_option(self) -> str | None:
        return FILTRATION_SPEEDS.get(self._get("Filtration", "Speed"))

    async def async_select_option(self, option: str) -> None:
        speed = FILTRATION_SPEEDS_REVERSE.get(option)
        if speed is None:
            return
        current_mode = self._get("Filtration", "Mode")
        if current_mode != FILTRATION_MODE_MANUAL:
            _LOGGER.info(
                "Switching filtration to Manual mode so speed change takes effect "
                "(was mode=%s)",
                current_mode,
            )
            await self.coordinator.async_send_command(
                CMD_NPFILTRATIONMODE, str(FILTRATION_MODE_MANUAL)
            )
        await self.coordinator.async_send_command(CMD_NPFILTRATIONSPEED, str(speed))


class NeoPoolBoostModeSelect(NeoPoolEntity, SelectEntity):
    _attr_icon = "mdi:rocket-launch"

    def __init__(self, coordinator: NeoPoolCoordinator) -> None:
        super().__init__(coordinator, "boost_mode", "Boost Mode")
        self._attr_options = list(BOOST_MODES.values())

    @property
    def current_option(self) -> str | None:
        return BOOST_MODES.get(self._get("Hydrolysis", "Boost"))

    async def async_select_option(self, option: str) -> None:
        boost = BOOST_MODES_REVERSE.get(option)
        if boost is not None:
            await self.coordinator.async_send_command(CMD_NPBOOST, str(boost))
