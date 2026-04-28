"""Sensor platform for NeoPool MQTT Controller."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfElectricPotential,
    PERCENTAGE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PH_STATES, HYDROLYSIS_STATES, FILTRATION_MODES
from .entity import NeoPoolEntity
from .coordinator import NeoPoolCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NeoPool sensors from config entry."""
    coordinator: NeoPoolCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        # Temperature
        NeoPoolTemperatureSensor(coordinator),
        # pH sensors
        NeoPoolPHSensor(coordinator),
        NeoPoolPHStateSensor(coordinator),
        NeoPoolPHPumpSensor(coordinator),
        NeoPoolPHTankSensor(coordinator),
        # Redox
        NeoPoolRedoxSensor(coordinator),
        NeoPoolRedoxSetpointSensor(coordinator),
        # Hydrolysis
        NeoPoolHydrolysisDataSensor(coordinator),
        NeoPoolHydrolysisSetpointSensor(coordinator),
        NeoPoolHydrolysisStateSensor(coordinator),
        NeoPoolHydrolysisRuntimeTotalSensor(coordinator),
        NeoPoolHydrolysisRuntimePartSensor(coordinator),
        NeoPoolHydrolysisPol1Sensor(coordinator),
        NeoPoolHydrolysisPol2Sensor(coordinator),
        NeoPoolHydrolysisChangesSensor(coordinator),
        # Filtration
        NeoPoolFiltrationStateSensor(coordinator),
        NeoPoolFiltrationSpeedSensor(coordinator),
        NeoPoolFiltrationModeSensor(coordinator),
        # Relay states
        NeoPoolRelay1Sensor(coordinator),
        NeoPoolRelay2Sensor(coordinator),
        NeoPoolRelay3Sensor(coordinator),
        NeoPoolRelay4Sensor(coordinator),
        NeoPoolRelay5Sensor(coordinator),
        NeoPoolRelay6Sensor(coordinator),
        NeoPoolRelay7Sensor(coordinator),
        # Special relay sensors
        NeoPoolRelayAcidSensor(coordinator),
        NeoPoolRelayValveSensor(coordinator),
        # Device info sensors
        NeoPoolDeviceTypeSensor(coordinator),
        NeoPoolFirmwareVersionSensor(coordinator),
        NeoPoolVoltage5VSensor(coordinator),
        NeoPoolVoltage12VSensor(coordinator),
        NeoPoolVoltage24VSensor(coordinator),
        NeoPoolCurrent420mASensor(coordinator),
        # Connection stats
        NeoPoolMBRequestsSensor(coordinator),
        NeoPoolMBNoErrorSensor(coordinator),
        NeoPoolMBNoResponseSensor(coordinator),
        # Chlorine (conditional)
        NeoPoolChlorineDataSensor(coordinator),
        NeoPoolChlorineSetpointSensor(coordinator),
        # Conductivity (conditional)
        NeoPoolConductivitySensor(coordinator),
        # Ionization (conditional)
        NeoPoolIonizationDataSensor(coordinator),
        NeoPoolIonizationSetpointSensor(coordinator),
    ]

    async_add_entities(entities)


class NeoPoolSensor(NeoPoolEntity, SensorEntity):
    """Base NeoPool sensor."""

    def __init__(self, coordinator, key, name, **kwargs):
        """Initialize."""
        super().__init__(coordinator, key, name)
        self._attr_device_class = kwargs.get("device_class")
        self._attr_state_class = kwargs.get("state_class")
        self._attr_native_unit_of_measurement = kwargs.get("unit")
        self._attr_icon = kwargs.get("icon")
        self._attr_entity_registry_enabled_default = kwargs.get("enabled_default", True)

    def _get_nested(self, *keys):
        """Get nested value from data."""
        data = self.coordinator.data
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key)
            else:
                return None
        return data


# --- Temperature ---
class NeoPoolTemperatureSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "temperature", "Water Temperature",
                         device_class=SensorDeviceClass.TEMPERATURE,
                         state_class=SensorStateClass.MEASUREMENT,
                         unit=UnitOfTemperature.CELSIUS)

    @property
    def native_value(self):
        return self._get_nested("Temperature")


# --- pH ---
class NeoPoolPHSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "ph_data", "pH",
                         state_class=SensorStateClass.MEASUREMENT,
                         icon="mdi:ph")

    @property
    def native_value(self):
        return self._get_nested("pH", "Data")

    @property
    def extra_state_attributes(self):
        ph = self.coordinator.data.get("pH", {})
        return {
            "min_setpoint": ph.get("Min"),
            "max_setpoint": ph.get("Max"),
        }


class NeoPoolPHStateSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "ph_state", "pH State",
                         icon="mdi:alert-circle-outline")

    @property
    def native_value(self):
        state = self._get_nested("pH", "State")
        return PH_STATES.get(state, f"Unknown ({state})") if state is not None else None


class NeoPoolPHPumpSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "ph_pump", "pH Pump",
                         icon="mdi:pump")

    @property
    def native_value(self):
        pump = self._get_nested("pH", "Pump")
        if pump == 0:
            return "Inactive"
        elif pump == 1:
            return "On"
        elif pump == 2:
            return "Off"
        return pump


class NeoPoolPHTankSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "ph_tank", "pH Tank",
                         icon="mdi:cup-water")

    @property
    def native_value(self):
        tank = self._get_nested("pH", "Tank")
        if tank == 0:
            return "Empty"
        elif tank == 1:
            return "OK"
        return tank


# --- Redox ---
class NeoPoolRedoxSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "redox_data", "Redox (ORP)",
                         state_class=SensorStateClass.MEASUREMENT,
                         unit=UnitOfElectricPotential.MILLIVOLT,
                         icon="mdi:flash")

    @property
    def native_value(self):
        return self._get_nested("Redox", "Data")


class NeoPoolRedoxSetpointSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "redox_setpoint", "Redox Setpoint",
                         unit=UnitOfElectricPotential.MILLIVOLT,
                         icon="mdi:flash-outline")

    @property
    def native_value(self):
        return self._get_nested("Redox", "Setpoint")


# --- Hydrolysis ---
class NeoPoolHydrolysisDataSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "hydrolysis_data", "Hydrolysis Level",
                         state_class=SensorStateClass.MEASUREMENT,
                         icon="mdi:water-percent")

    @property
    def native_value(self):
        return self._get_nested("Hydrolysis", "Data")

    @property
    def native_unit_of_measurement(self):
        unit = self._get_nested("Hydrolysis", "Unit")
        return unit if unit else PERCENTAGE


class NeoPoolHydrolysisSetpointSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "hydrolysis_setpoint_sensor", "Hydrolysis Setpoint (sensor)",
                         icon="mdi:water-percent",
                         enabled_default=False)

    @property
    def native_value(self):
        return self._get_nested("Hydrolysis", "Setpoint")

    @property
    def native_unit_of_measurement(self):
        unit = self._get_nested("Hydrolysis", "Unit")
        return unit if unit else PERCENTAGE


class NeoPoolHydrolysisStateSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "hydrolysis_state", "Hydrolysis State",
                         icon="mdi:state-machine")

    @property
    def native_value(self):
        state = self._get_nested("Hydrolysis", "State")
        return HYDROLYSIS_STATES.get(state, state) if state else None

    @property
    def extra_state_attributes(self):
        hydro = self.coordinator.data.get("Hydrolysis", {})
        return {
            "cover": hydro.get("Cover"),
            "boost": hydro.get("Boost"),
            "low_alarm": hydro.get("Low"),
            "flow_alarm": hydro.get("FL1"),
            "redox_activated": hydro.get("Redox"),
        }


class NeoPoolHydrolysisRuntimeTotalSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "hydrolysis_runtime_total", "Cell Runtime Total",
                         icon="mdi:timer-outline")

    @property
    def native_value(self):
        return self._get_nested("Hydrolysis", "Runtime", "Total")


class NeoPoolHydrolysisRuntimePartSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "hydrolysis_runtime_part", "Cell Runtime Part",
                         icon="mdi:timer-outline",
                         enabled_default=False)

    @property
    def native_value(self):
        return self._get_nested("Hydrolysis", "Runtime", "Part")


class NeoPoolHydrolysisPol1Sensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "hydrolysis_pol1", "Cell Polarization 1 Runtime",
                         icon="mdi:timer-outline",
                         enabled_default=False)

    @property
    def native_value(self):
        return self._get_nested("Hydrolysis", "Runtime", "Pol1")


class NeoPoolHydrolysisPol2Sensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "hydrolysis_pol2", "Cell Polarization 2 Runtime",
                         icon="mdi:timer-outline",
                         enabled_default=False)

    @property
    def native_value(self):
        return self._get_nested("Hydrolysis", "Runtime", "Pol2")


class NeoPoolHydrolysisChangesSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "hydrolysis_changes", "Polarization Changes",
                         state_class=SensorStateClass.TOTAL_INCREASING,
                         icon="mdi:swap-horizontal")

    @property
    def native_value(self):
        return self._get_nested("Hydrolysis", "Runtime", "Changes")


# --- Filtration ---
class NeoPoolFiltrationStateSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "filtration_state_sensor", "Filtration State (sensor)",
                         icon="mdi:pump",
                         enabled_default=False)

    @property
    def native_value(self):
        state = self._get_nested("Filtration", "State")
        return "On" if state == 1 else "Off" if state == 0 else state


class NeoPoolFiltrationSpeedSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "filtration_speed_sensor", "Filtration Speed (sensor)",
                         icon="mdi:speedometer",
                         enabled_default=False)

    @property
    def native_value(self):
        from .const import FILTRATION_SPEEDS
        speed = self._get_nested("Filtration", "Speed")
        return FILTRATION_SPEEDS.get(speed, speed)


class NeoPoolFiltrationModeSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "filtration_mode_sensor", "Filtration Mode (sensor)",
                         icon="mdi:cog",
                         enabled_default=False)

    @property
    def native_value(self):
        mode = self._get_nested("Filtration", "Mode")
        return FILTRATION_MODES.get(mode, f"Unknown ({mode})") if mode is not None else None


# --- Relay States ---
def _make_relay_sensor(idx):
    class Sensor(NeoPoolSensor):
        def __init__(self, coordinator):
            super().__init__(coordinator, f"relay_{idx}", f"Relay {idx}",
                             icon="mdi:electric-switch")

        @property
        def native_value(self):
            states = self._get_nested("Relay", "State")
            if isinstance(states, list) and len(states) >= idx:
                return "On" if states[idx - 1] == 1 else "Off"
            return None
    return Sensor


NeoPoolRelay1Sensor = _make_relay_sensor(1)
NeoPoolRelay2Sensor = _make_relay_sensor(2)
NeoPoolRelay3Sensor = _make_relay_sensor(3)
NeoPoolRelay4Sensor = _make_relay_sensor(4)
NeoPoolRelay5Sensor = _make_relay_sensor(5)
NeoPoolRelay6Sensor = _make_relay_sensor(6)
NeoPoolRelay7Sensor = _make_relay_sensor(7)


class NeoPoolRelayAcidSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "relay_acid", "Acid Pump Relay",
                         icon="mdi:flask")

    @property
    def native_value(self):
        val = self._get_nested("Relay", "Acid")
        return "On" if val == 1 else "Off" if val == 0 else None


class NeoPoolRelayValveSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "relay_valve", "Valve Relay",
                         icon="mdi:valve")

    @property
    def native_value(self):
        val = self._get_nested("Relay", "Valve")
        return "On" if val == 1 else "Off" if val == 0 else None


# --- Device Info ---
class NeoPoolDeviceTypeSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "device_type", "Device Type",
                         icon="mdi:pool")

    @property
    def native_value(self):
        return self.coordinator.data.get("Type")


class NeoPoolFirmwareVersionSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "firmware_version", "Firmware Version",
                         icon="mdi:chip",
                         enabled_default=False)

    @property
    def native_value(self):
        return self._get_nested("Powerunit", "Version")


class NeoPoolVoltage5VSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "voltage_5v", "5V Supply",
                         device_class=SensorDeviceClass.VOLTAGE,
                         state_class=SensorStateClass.MEASUREMENT,
                         unit="V",
                         enabled_default=False)

    @property
    def native_value(self):
        return self._get_nested("Powerunit", "5V")


class NeoPoolVoltage12VSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "voltage_12v", "12V Supply",
                         device_class=SensorDeviceClass.VOLTAGE,
                         state_class=SensorStateClass.MEASUREMENT,
                         unit="V",
                         enabled_default=False)

    @property
    def native_value(self):
        return self._get_nested("Powerunit", "12V")


class NeoPoolVoltage24VSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "voltage_24v", "24-30V Supply",
                         device_class=SensorDeviceClass.VOLTAGE,
                         state_class=SensorStateClass.MEASUREMENT,
                         unit="V",
                         enabled_default=False)

    @property
    def native_value(self):
        return self._get_nested("Powerunit", "24-30V")


class NeoPoolCurrent420mASensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "current_420ma", "4-20mA Output",
                         device_class=SensorDeviceClass.CURRENT,
                         state_class=SensorStateClass.MEASUREMENT,
                         unit="mA",
                         enabled_default=False)

    @property
    def native_value(self):
        return self._get_nested("Powerunit", "4-20mA")


# --- Connection Stats ---
class NeoPoolMBRequestsSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "mb_requests", "Modbus Requests",
                         state_class=SensorStateClass.TOTAL_INCREASING,
                         icon="mdi:database-arrow-right",
                         enabled_default=False)

    @property
    def native_value(self):
        return self._get_nested("Connection", "MBRequests")


class NeoPoolMBNoErrorSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "mb_no_error", "Modbus Successful",
                         state_class=SensorStateClass.TOTAL_INCREASING,
                         icon="mdi:check-circle",
                         enabled_default=False)

    @property
    def native_value(self):
        return self._get_nested("Connection", "MBNoError")


class NeoPoolMBNoResponseSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "mb_no_response", "Modbus No Response",
                         state_class=SensorStateClass.TOTAL_INCREASING,
                         icon="mdi:alert",
                         enabled_default=False)

    @property
    def native_value(self):
        return self._get_nested("Connection", "MBNoResponse")


# --- Chlorine (conditional) ---
class NeoPoolChlorineDataSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "chlorine_data", "Chlorine",
                         state_class=SensorStateClass.MEASUREMENT,
                         unit="ppm",
                         icon="mdi:flask-round-bottom")

    @property
    def native_value(self):
        return self._get_nested("Chlorine", "Data")

    @property
    def available(self):
        return super().available and self._get_nested("Chlorine", "Data") is not None


class NeoPoolChlorineSetpointSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "chlorine_setpoint_sensor", "Chlorine Setpoint (sensor)",
                         unit="ppm",
                         icon="mdi:flask-round-bottom-outline",
                         enabled_default=False)

    @property
    def native_value(self):
        return self._get_nested("Chlorine", "Setpoint")

    @property
    def available(self):
        return super().available and self._get_nested("Chlorine") is not None


# --- Conductivity ---
class NeoPoolConductivitySensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "conductivity", "Conductivity",
                         state_class=SensorStateClass.MEASUREMENT,
                         unit=PERCENTAGE,
                         icon="mdi:flash-triangle")

    @property
    def native_value(self):
        return self.coordinator.data.get("Conductivity")

    @property
    def available(self):
        return super().available and self.coordinator.data.get("Conductivity") is not None


# --- Ionization ---
class NeoPoolIonizationDataSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "ionization_data", "Ionization",
                         state_class=SensorStateClass.MEASUREMENT,
                         icon="mdi:atom")

    @property
    def native_value(self):
        return self._get_nested("Ionization", "Data")

    @property
    def available(self):
        return super().available and self._get_nested("Ionization", "Data") is not None


class NeoPoolIonizationSetpointSensor(NeoPoolSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "ionization_setpoint_sensor", "Ionization Setpoint (sensor)",
                         icon="mdi:atom-variant",
                         enabled_default=False)

    @property
    def native_value(self):
        return self._get_nested("Ionization", "Setpoint")

    @property
    def available(self):
        return super().available and self._get_nested("Ionization") is not None
