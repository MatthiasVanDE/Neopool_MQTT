"""Select platform for NeoPool MQTT Controller."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BOOST_MODES,
    BOOST_MODES_REVERSE,
    CMD_NPBOOST,
    CMD_NPFILTRATION,
    CMD_NPFILTRATIONMODE,
    CMD_NPFILTRATIONSPEED,
    CMD_NPLIGHT,
    DOMAIN,
    FILTRATION_MODES,
    FILTRATION_MODES_REVERSE,
    FILTRATION_SPEEDS,
    FILTRATION_SPEEDS_REVERSE,
    LIGHT_MODES,
    LIGHT_MODES_REVERSE,
)
from .coordinator import NeoPoolCoordinator
from .entity import NeoPoolEntity


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
            NeoPoolIntervalSpeedSelect(coordinator),
            NeoPoolBoostModeSelect(coordinator),
            NeoPoolLightModeSelect(coordinator),
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

    Behaviour (explicit, documented):
    - When filtration is running, the speed is changed in a single command using the
      documented two-parameter form ``NPFiltration 1 <speed>`` (e.g. "NPFiltration 1 2").
      This sets state+speed atomically and does NOT silently force the filtration mode.
    - When filtration is off, only the desired speed is set (``NPFiltrationspeed``);
      it takes effect once filtration runs.
    """

    _attr_icon = "mdi:speedometer"

    def __init__(self, coordinator: NeoPoolCoordinator) -> None:
        super().__init__(coordinator, "filtration_speed", "Filtration Speed")
        self._attr_options = list(FILTRATION_SPEEDS.values())

    @property
    def current_option(self) -> str | None:
        """The speed actually being driven, falling back to Tasmota's own value.

        The relay lines are the truth; Tasmota's Speed field misreports pumps whose
        speed lines are wired additively. Until the relay register has been read
        once, the reported value is all we have.
        """
        actual = FILTRATION_SPEEDS.get(self.coordinator.filtration_speed)
        if actual is not None:
            return actual
        if self.coordinator.filtration_speed_bits is not None:
            # Register read, but no speed line active: the pump is not being driven.
            return None
        return FILTRATION_SPEEDS.get(self._get("Filtration", "Speed"))

    async def async_select_option(self, option: str) -> None:
        speed = FILTRATION_SPEEDS_REVERSE.get(option)
        if speed is None:
            return
        if self._get("Filtration", "State") == 1:
            # Combined state+speed form: payload must be exactly "1 2" (space-separated).
            await self.coordinator.async_send_command(
                CMD_NPFILTRATION, f"1 {speed}"
            )
        else:
            await self.coordinator.async_send_command(
                CMD_NPFILTRATIONSPEED, str(speed)
            )


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


class NeoPoolLightModeSelect(NeoPoolEntity, SelectEntity):
    """Light mode select: Off / On / Auto.

    Complements the existing ``light`` on/off switch (kept for backward compat).
    The device reports Light as 0/1 in SENSOR, so when in Auto it may read back as
    On/Off after the next SENSOR; the optimistic update reflects Auto until then.
    The "next RGB program" action is exposed as a separate button.
    """

    _attr_icon = "mdi:palette"

    def __init__(self, coordinator: NeoPoolCoordinator) -> None:
        super().__init__(coordinator, "light_mode", "Light Mode")
        self._attr_options = list(LIGHT_MODES.values())

    @property
    def current_option(self) -> str | None:
        return LIGHT_MODES.get(self._get("Light"))

    async def async_select_option(self, option: str) -> None:
        mode = LIGHT_MODES_REVERSE.get(option)
        if mode is not None:
            await self.coordinator.async_send_command(CMD_NPLIGHT, str(mode))


class NeoPoolIntervalSpeedSelect(NeoPoolEntity, SelectEntity):
    """Pump speed for filtration timer interval 1 (MBF_PAR_FILTRATION_CONF bits 7-9).

    This is the speed the pump actually runs at while a filtration timer interval is
    active. The Filtration Speed select next to it writes the *default* speed, which
    the panel only applies outside those intervals - so on a panel that filters on a
    timer, this is the one that does something.

    Written with NPWrite + NPExec and read straight back, RAM only: a panel power
    cycle restores whatever its own menu has stored. That is deliberate, because an
    automation may switch this several times a day and EEPROM wears out.
    """

    _attr_icon = "mdi:speedometer-medium"

    def __init__(self, coordinator: NeoPoolCoordinator) -> None:
        super().__init__(
            coordinator, "filtration_interval_speed", "Filtration Interval Speed"
        )
        self._attr_options = list(FILTRATION_SPEEDS.values())

    @property
    def current_option(self) -> str | None:
        return FILTRATION_SPEEDS.get(self.coordinator.configured_speed)

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.configured_speed is not None

    async def async_select_option(self, option: str) -> None:
        speed = FILTRATION_SPEEDS_REVERSE.get(option)
        if speed is not None:
            await self.coordinator.async_set_interval_speed(speed)
