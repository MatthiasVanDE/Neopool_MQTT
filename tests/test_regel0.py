"""REGEL 0 regression guard: existing entity keys must never change or disappear.

The unique_id is f"{mqtt_topic}_{key}", so every key in the original contract
(docs/EXISTING_ENTITIES.md) must keep existing. New keys are allowed; missing ones
are a breaking change for users' automations.
"""
from conftest import load_module

sensor = load_module("sensor")
binary = load_module("binary_sensor")
number = load_module("number")
button = load_module("button")

# The read-only contract from docs/EXISTING_ENTITIES.md (commit ebefd15).
CONTRACT = {
    # sensor
    "temperature", "ph_data", "ph_state", "ph_pump", "ph_tank", "redox_data",
    "redox_setpoint", "hydrolysis_data", "hydrolysis_setpoint_sensor",
    "hydrolysis_state", "hydrolysis_runtime_total", "hydrolysis_runtime_part",
    "hydrolysis_pol1", "hydrolysis_pol2", "hydrolysis_changes",
    "filtration_state_sensor", "filtration_speed_sensor", "filtration_mode_sensor",
    "relay_1", "relay_2", "relay_3", "relay_4", "relay_5", "relay_6", "relay_7",
    "relay_acid", "relay_valve", "device_type", "firmware_version", "voltage_5v",
    "voltage_12v", "voltage_24v", "current_420ma", "mb_requests", "mb_no_error",
    "mb_no_response", "chlorine_data", "chlorine_setpoint_sensor", "conductivity",
    "ionization_data", "ionization_setpoint_sensor",
    # binary_sensor
    "ph_alarm", "ph_tank_empty", "ph_flow", "hydrolysis_flow_alarm",
    "hydrolysis_low_alarm", "cover_active", "filtration_running",
    # switch
    "filtration", "light", "aux1", "aux2", "aux3", "aux4",
    # select
    "filtration_mode", "filtration_speed", "boost_mode",
    # number
    "ph_min", "ph_max", "redox_setpoint_number", "hydrolysis_setpoint",
    "ionization_setpoint", "chlorine_setpoint",
    # button
    "clear_errors", "save_eeprom", "exec",
}


def _current_keys() -> set[str]:
    keys = {d.key for d in sensor.SENSORS}
    keys.add("berry_version")
    keys |= {d.key for d in binary.BINARY_SENSORS}
    keys |= {d.key for d in number.NUMBERS}
    keys.add("heating_setpoint")
    keys |= {d.key for d in button.BUTTONS}
    # class-based switch + select keys (constructed in __init__)
    keys |= {"filtration", "light", "aux1", "aux2", "aux3", "aux4"}
    keys |= {"filtration_mode", "filtration_speed", "boost_mode", "light_mode"}
    return keys


def test_no_existing_key_removed():
    missing = CONTRACT - _current_keys()
    assert not missing, f"REGEL 0 violation: keys removed/renamed: {sorted(missing)}"


def test_no_duplicate_keys_within_platform():
    for descs in (sensor.SENSORS, binary.BINARY_SENSORS, number.NUMBERS, button.BUTTONS):
        keys = [d.key for d in descs]
        assert len(keys) == len(set(keys)), f"duplicate keys: {keys}"
