"""Switch platform for NeoPool MQTT Controller."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CMD_NPFILTRATION, CMD_NPLIGHT, CMD_NPAUX
from .entity import NeoPoolEntity
from .coordinator import NeoPoolCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NeoPool switches from config entry."""
    coordinator: NeoPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        NeoPoolFiltrationSwitch(coordinator),
        NeoPoolLightSwitch(coordinator),
        NeoPoolAux1Switch(coordinator),
        NeoPoolAux2Switch(coordinator),
        NeoPoolAux3Switch(coordinator),
        NeoPoolAux4Switch(coordinator),
    ]

    async_add_entities(entities)


class NeoPoolSwitch(NeoPoolEntity, SwitchEntity):
    """Base NeoPool switch."""

    def __init__(self, coordinator, key, name, command, icon=None):
        """Initialize."""
        super().__init__(coordinator, key, name)
        self._command = command
        self._attr_icon = icon

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on."""
        await self.coordinator.async_send_command(self._command, "1")

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off."""
        await self.coordinator.async_send_command(self._command, "0")


class NeoPoolFiltrationSwitch(NeoPoolSwitch):
    """Filtration pump switch."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "filtration", "Filtration",
                         CMD_NPFILTRATION, icon="mdi:pump")

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.data.get("Filtration", {}).get("State")
        return state == 1 if state is not None else None

    @property
    def extra_state_attributes(self):
        filt = self.coordinator.data.get("Filtration", {})
        from .const import FILTRATION_SPEEDS, FILTRATION_MODES
        return {
            "speed": FILTRATION_SPEEDS.get(filt.get("Speed"), filt.get("Speed")),
            "mode": FILTRATION_MODES.get(filt.get("Mode"), filt.get("Mode")),
        }


class NeoPoolLightSwitch(NeoPoolSwitch):
    """Light switch."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "light", "Light",
                         CMD_NPLIGHT, icon="mdi:pool")

    @property
    def is_on(self) -> bool | None:
        light = self.coordinator.data.get("Light")
        return light == 1 if light is not None else None


class NeoPoolAuxSwitch(NeoPoolSwitch):
    """Aux relay switch."""

    def __init__(self, coordinator, aux_num):
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
        aux = self.coordinator.data.get("Relay", {}).get("Aux")
        if isinstance(aux, list) and len(aux) >= self._aux_num:
            return aux[self._aux_num - 1] == 1
        return None


class NeoPoolAux1Switch(NeoPoolAuxSwitch):
    def __init__(self, coordinator):
        super().__init__(coordinator, 1)


class NeoPoolAux2Switch(NeoPoolAuxSwitch):
    def __init__(self, coordinator):
        super().__init__(coordinator, 2)


class NeoPoolAux3Switch(NeoPoolAuxSwitch):
    def __init__(self, coordinator):
        super().__init__(coordinator, 3)


class NeoPoolAux4Switch(NeoPoolAuxSwitch):
    def __init__(self, coordinator):
        super().__init__(coordinator, 4)
