"""Switch platform for NeoPool MQTT Controller."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
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
    """Filtration pump.

    Switching this off while an aux output that needs flow is running is what dry-runs
    the equipment behind it, so a person is stopped and told which output to switch off
    first. Which aux outputs those are is configured (CONF_FLOW_REQUIRED_AUX); with
    none configured nothing changes.

    Deliberately NOT done by reporting unavailable: entity_service_call drops
    unavailable entities from a service call without telling the caller, which would
    silently disarm any automation that switches the pump. The refusal is limited to
    calls made by a person for the same reason. It is a ServiceValidationError and not
    a HomeAssistantError: asking for something that is wrong right now is not a
    failure of the integration, and it should not leave a stack trace in the log.
    """

    def __init__(self, coordinator: NeoPoolCoordinator) -> None:
        super().__init__(
            coordinator, "filtration", "Filtration", CMD_NPFILTRATION, icon="mdi:pump"
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        running = [
            self.coordinator.aux_label(num)
            for num in sorted(self.coordinator.flow_required_aux)
            if self.coordinator.aux_on(num)
        ]
        if running and self._called_by_user():
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="filtration_off_while_aux_runs",
                translation_placeholders={"aux": ", ".join(running)},
            )
        await super().async_turn_off(**kwargs)

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
    """Pool light.

    Tasmota only publishes ``Light`` when the panel has a relay assigned to the
    lighting function (MBF_PAR_LIGHTING_GPIO). Without one, ``NPLight`` answers
    ``Error`` and the switch can neither read nor set anything - so report
    unavailable instead of offering a control that silently does nothing.
    """

    def __init__(self, coordinator: NeoPoolCoordinator) -> None:
        super().__init__(coordinator, "light", "Light", CMD_NPLIGHT, icon="mdi:pool")

    @property
    def available(self) -> bool:
        return super().available and self._get("Light") is not None

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Refuse to energise an aux that needs flow while the pump is off.

        Only when the panel has actually told us filtration is off - not when we have
        not heard yet - and only for a person. An automation keeps its say: the panel
        itself interlocks on FL1, and the dry-run automations are the layer that has
        been tested, so a stale SENSOR message must not be able to block them.
        """
        if (
            self._aux_num in self.coordinator.flow_required_aux
            and self.coordinator.filtration_running is False
            and self._called_by_user()
        ):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="aux_on_without_filtration",
                translation_placeholders={
                    "aux": self.coordinator.aux_label(self._aux_num)
                },
            )
        await super().async_turn_on(**kwargs)
