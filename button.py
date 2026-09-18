"""Button platform for NeoPool MQTT Controller."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_NPESCAPE,
    CMD_NPEXEC,
    CMD_NPLIGHT,
    CMD_NPSAVE,
    DOMAIN,
    LIGHT_NEXT_PROGRAM,
)
from .coordinator import NeoPoolCoordinator
from .entity import NeoPoolEntity


@dataclass(frozen=True, kw_only=True)
class NeoPoolButtonDescription(ButtonEntityDescription):
    """Description of a NeoPool button."""

    command: str
    payload: str = ""
    available_fn: Callable[[dict[str, Any]], bool] | None = None


BUTTONS: tuple[NeoPoolButtonDescription, ...] = (
    NeoPoolButtonDescription(
        key="clear_errors",
        name="Clear Errors",
        icon="mdi:alert-remove",
        command=CMD_NPESCAPE,
    ),
    NeoPoolButtonDescription(
        key="save_eeprom",
        name="Save to EEPROM",
        icon="mdi:content-save",
        entity_registry_enabled_default=False,
        command=CMD_NPSAVE,
    ),
    NeoPoolButtonDescription(
        key="exec",
        name="Execute Changes",
        icon="mdi:play-circle",
        entity_registry_enabled_default=False,
        command=CMD_NPEXEC,
    ),
    NeoPoolButtonDescription(
        key="light_next_program",
        name="Light Next Program",
        icon="mdi:skip-next",
        command=CMD_NPLIGHT,
        payload=str(LIGHT_NEXT_PROGRAM),
        # No lighting relay assigned means NPLight answers Error; do not offer it.
        available_fn=lambda data: data.get("Light") is not None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NeoPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(NeoPoolButton(coordinator, desc) for desc in BUTTONS)


class NeoPoolButton(NeoPoolEntity, ButtonEntity):
    """Generic NeoPool button driven by a description."""

    entity_description: NeoPoolButtonDescription

    def __init__(
        self, coordinator: NeoPoolCoordinator, description: NeoPoolButtonDescription
    ) -> None:
        super().__init__(coordinator, description.key, description.name)
        self.entity_description = description

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        if self.entity_description.available_fn is not None:
            return self.entity_description.available_fn(self.coordinator.data)
        return True

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(
            self.entity_description.command, self.entity_description.payload
        )
