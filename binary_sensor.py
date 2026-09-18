"""Binary sensor platform for NeoPool MQTT Controller."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    MASK_CAUDAL_FL1,
    MASK_HIDRO_COVER_ENABLE,
    MASK_HIDRO_TEMPERATURE_SHUTDOWN,
    REG_PAR_FILTVALVE_ENABLE,
    REG_PAR_FILTVALVE_REMAINING,
    REG_PAR_HEATING_MODE,
    REG_PAR_HIDRO_COVER_ENABLE,
    REG_PAR_HIDRO_ION_CAUDAL,
    REG_PAR_SMART_ANTI_FREEZE,
)
from .coordinator import NeoPoolCoordinator
from .entity import NeoPoolEntity


@dataclass(frozen=True, kw_only=True)
class NeoPoolBinarySensorDescription(BinarySensorEntityDescription):
    """Description of a NeoPool binary sensor."""

    is_on_fn: Callable[[dict[str, Any]], bool | None]


def _ph_alarm(data: dict[str, Any]) -> bool | None:
    state = (data.get("pH") or {}).get("State")
    return state is not None and state != 0


def _eq(path: tuple[str, ...], target: int) -> Callable[[dict[str, Any]], bool | None]:
    def get(data: dict[str, Any]) -> bool | None:
        node: Any = data
        for key in path:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        if node is None:
            return None
        return node == target

    return get


def _module_present(name: str) -> Callable[[dict[str, Any]], bool | None]:
    def get(data: dict[str, Any]) -> bool | None:
        modules = data.get("Modules")
        if not isinstance(modules, dict) or name not in modules:
            return None
        return modules.get(name) == 1

    return get


# Diagnostic, default-disabled sensors exposing the Modules flags. (Name, key suffix).
_MODULES = (
    ("pH", "ph"),
    ("Redox", "redox"),
    ("Hydrolysis", "hydrolysis"),
    ("Chlorine", "chlorine"),
    ("Conductivity", "conductivity"),
    ("Ionization", "ionization"),
)


BINARY_SENSORS: tuple[NeoPoolBinarySensorDescription, ...] = (
    NeoPoolBinarySensorDescription(
        key="ph_alarm",
        name="pH Alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert",
        is_on_fn=_ph_alarm,
    ),
    NeoPoolBinarySensorDescription(
        key="ph_tank_empty",
        name="pH Tank Empty",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:cup-water",
        is_on_fn=_eq(("pH", "Tank"), 0),
    ),
    # FL1 is een ALARM-bit, geen aanwezigheidsbit: 1 betekent "flowprobleem", 0
    # betekent "geen flowprobleem". Dit stond tot 18-09-2026 als "pH Flow Detection"
    # en meldde daardoor het omgekeerde van de werkelijkheid: bij draaiende filtratie
    # is FL1 nul, dus de sensor stond 'off' terwijl er water stroomde. Geverifieerd op
    # het referentietoestel: de hydrolysecel produceerde en haar bedrijfsteller liep
    # door terwijl pH.FL1 en Hydrolysis.FL1 allebei 0 waren. De key blijft "ph_flow"
    # zodat bestaande entiteiten hun unique_id houden (REGEL 0).
    NeoPoolBinarySensorDescription(
        key="ph_flow",
        name="pH Flow Alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:waves-arrow-up",
        is_on_fn=_eq(("pH", "FL1"), 1),
    ),
    NeoPoolBinarySensorDescription(
        key="hydrolysis_flow_alarm",
        name="Hydrolysis Flow Alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:waves-arrow-up",
        is_on_fn=_eq(("Hydrolysis", "FL1"), 1),
    ),
    NeoPoolBinarySensorDescription(
        key="hydrolysis_low_alarm",
        name="Hydrolysis Low Alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert-circle",
        is_on_fn=_eq(("Hydrolysis", "Low"), 1),
    ),
    NeoPoolBinarySensorDescription(
        key="cover_active",
        name="Cover Active",
        icon="mdi:shield-sun",
        is_on_fn=_eq(("Hydrolysis", "Cover"), 1),
    ),
    NeoPoolBinarySensorDescription(
        key="filtration_running",
        name="Filtration Running",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        is_on_fn=_eq(("Filtration", "State"), 1),
    ),
    *(
        NeoPoolBinarySensorDescription(
            key=f"module_{suffix}",
            name=f"Module {mod_name}",
            icon="mdi:puzzle",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            is_on_fn=_module_present(mod_name),
        )
        for mod_name, suffix in _MODULES
    ),
)


# --- Register-backed binary sensors -------------------------------------------


@dataclass(frozen=True, kw_only=True)
class NeoPoolRegisterBinarySensorDescription(BinarySensorEntityDescription):
    """Description of a binary sensor backed by a raw Modbus register."""

    is_on_fn: Callable[[NeoPoolCoordinator], bool | None]


def _bit(address: int, mask: int) -> Callable[[NeoPoolCoordinator], bool | None]:
    def get(coordinator: NeoPoolCoordinator) -> bool | None:
        value = coordinator.register(address)
        if value is None:
            return None
        return bool(value & mask)

    return get


def _reg_eq(address: int, target: int) -> Callable[[NeoPoolCoordinator], bool | None]:
    def get(coordinator: NeoPoolCoordinator) -> bool | None:
        value = coordinator.register(address)
        if value is None:
            return None
        return value == target

    return get


def _backwash_active(coordinator: NeoPoolCoordinator) -> bool | None:
    remaining = coordinator.register(REG_PAR_FILTVALVE_REMAINING)
    if remaining is None:
        return None
    return remaining > 0


_DIAG = {
    "entity_category": EntityCategory.DIAGNOSTIC,
    "entity_registry_enabled_default": False,
}

REGISTER_BINARY_SENSORS: tuple[NeoPoolRegisterBinarySensorDescription, ...] = (
    NeoPoolRegisterBinarySensorDescription(
        key="cover_closed",
        name="Pool Cover Closed",
        icon="mdi:shield-sun",
        is_on_fn=lambda coordinator: coordinator.cover_closed,
    ),
    NeoPoolRegisterBinarySensorDescription(
        key="backwash_active",
        name="Backwash Running",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:valve-open",
        is_on_fn=_backwash_active,
    ),
    NeoPoolRegisterBinarySensorDescription(
        key="backwash_enabled",
        name="Backwash Enabled",
        icon="mdi:valve",
        is_on_fn=_reg_eq(REG_PAR_FILTVALVE_ENABLE, 1),
        **_DIAG,
    ),
    NeoPoolRegisterBinarySensorDescription(
        key="cover_reduction_enabled",
        name="Cover Reduction Enabled",
        icon="mdi:shield-sun",
        is_on_fn=_bit(REG_PAR_HIDRO_COVER_ENABLE, MASK_HIDRO_COVER_ENABLE),
        **_DIAG,
    ),
    NeoPoolRegisterBinarySensorDescription(
        key="temperature_shutdown_enabled",
        name="Hydrolysis Temperature Shutdown Enabled",
        icon="mdi:thermometer-off",
        is_on_fn=_bit(REG_PAR_HIDRO_COVER_ENABLE, MASK_HIDRO_TEMPERATURE_SHUTDOWN),
        **_DIAG,
    ),
    NeoPoolRegisterBinarySensorDescription(
        key="smart_antifreeze",
        name="Smart Antifreeze",
        icon="mdi:snowflake-alert",
        is_on_fn=_reg_eq(REG_PAR_SMART_ANTI_FREEZE, 1),
        **_DIAG,
    ),
    NeoPoolRegisterBinarySensorDescription(
        key="fl1_interlock",
        name="FL1 Interlock Active",
        icon="mdi:water-alert-outline",
        is_on_fn=_bit(REG_PAR_HIDRO_ION_CAUDAL, MASK_CAUDAL_FL1),
        **_DIAG,
    ),
    NeoPoolRegisterBinarySensorDescription(
        key="heating_active",
        name="Panel Heating Active",
        device_class=BinarySensorDeviceClass.HEAT,
        icon="mdi:radiator",
        is_on_fn=_reg_eq(REG_PAR_HEATING_MODE, 1),
        **_DIAG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NeoPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[BinarySensorEntity] = [
        NeoPoolBinarySensor(coordinator, desc) for desc in BINARY_SENSORS
    ]
    entities += [
        NeoPoolRegisterBinarySensor(coordinator, desc)
        for desc in REGISTER_BINARY_SENSORS
    ]
    async_add_entities(entities)


class NeoPoolBinarySensor(NeoPoolEntity, BinarySensorEntity):
    """Generic NeoPool binary sensor driven by a description."""

    entity_description: NeoPoolBinarySensorDescription

    def __init__(
        self,
        coordinator: NeoPoolCoordinator,
        description: NeoPoolBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key, description.name)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.is_on_fn(self.coordinator.data)


class NeoPoolRegisterBinarySensor(NeoPoolEntity, BinarySensorEntity):
    """Binary sensor backed by a raw Modbus register read with NPRead."""

    entity_description: NeoPoolRegisterBinarySensorDescription

    def __init__(
        self,
        coordinator: NeoPoolCoordinator,
        description: NeoPoolRegisterBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key, description.name)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.is_on_fn(self.coordinator)

    @property
    def available(self) -> bool:
        return super().available and self.is_on is not None
