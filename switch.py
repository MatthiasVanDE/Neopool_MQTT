"""Switch platform for NeoPool MQTT Controller."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_NPAUX,
    CMD_NPFILTRATION,
    CMD_NPLIGHT,
    DOMAIN,
    FILTRATION_MODES,
    FILTRATION_SPEEDS,
    berry_enabled,
)
from .coordinator import NeoPoolCoordinator
from .entity import NeoPoolEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NeoPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[SwitchEntity] = [
        NeoPoolFiltrationSwitch(coordinator),
        NeoPoolLightSwitch(coordinator),
    ]
    # NPAux<x> only exists when the Berry script neopoolcmd.be is loaded. Only create
    # the Aux switches when enabled. For entries predating this option the helper
    # defaults to True, so existing aux1..aux4 entities are preserved (REGEL 0).
    if berry_enabled(config_entry):
        entities.extend(NeoPoolAuxSwitch(coordinator, i) for i in range(1, 5))
    async_add_entities(entities)


class _BaseSwitch(NeoPoolEntity, SwitchEntity):
    """Common on/off command pattern."""

    def __init__(
        self,
        coordinator: NeoPoolCoordinator,
        key: str,
        name: str,
        command: str,
        icon: str | None = None,
    ) -> None:
        super().__init__(coordinator, key, name)
        self._command = command
        self._attr_icon = icon

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(self._command, "1")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(self._command, "0")


class NeoPoolFiltrationSwitch(_BaseSwitch):
    def __init__(self, coordinator: NeoPoolCoordinator) -> None:
        super().__init__(
            coordinator, "filtration", "Filtration", CMD_NPFILTRATION, icon="mdi:pump"
        )

    @property
    def is_on(self) -> bool | None:
        state = self._get("Filtration", "State")
        return state == 1 if state is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        filt = self.coordinator.data.get("Filtration") or {}
        return {
            "speed": FILTRATION_SPEEDS.get(filt.get("Speed"), filt.get("Speed")),
            "mode": FILTRATION_MODES.get(filt.get("Mode"), filt.get("Mode")),
        }


class NeoPoolLightSwitch(_BaseSwitch):
    def __init__(self, coordinator: NeoPoolCoordinator) -> None:
        super().__init__(coordinator, "light", "Light", CMD_NPLIGHT, icon="mdi:pool")

    @property
    def is_on(self) -> bool | None:
        light = self._get("Light")
        return light == 1 if light is not None else None


class NeoPoolAuxSwitch(_BaseSwitch):
    def __init__(self, coordinator: NeoPoolCoordinator, aux_num: int) -> None:
        self._aux_num = aux_num
        super().__init__(
            coordinator,
            f"aux{aux_num}",
            f"Aux {aux_num}",
            f"{CMD_NPAUX}{aux_num}",
            icon="mdi:electric-switch",
        )

    @property
    def is_on(self) -> bool | None:
        aux = self._get("Relay", "Aux")
        if isinstance(aux, list) and len(aux) >= self._aux_num:
            return aux[self._aux_num - 1] == 1
        return None
