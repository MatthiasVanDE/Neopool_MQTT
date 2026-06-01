# Bestaande entiteiten — READ-ONLY CONTRACT (REGEL 0)

Dit is de volledige inventaris van entity-keys zoals aanwezig in de repo bij de start
van het werkplan (commit `ebefd15`). De `unique_id` van elke entity is
`f"{coordinator.mqtt_topic}_{key}"` (zie [entity.py](../entity.py)). De `key` is dus
het contract met de gebruiker: zijn automatiseringen hangen via `entity_id` →
`unique_id` → `key` hieraan vast.

**Geen enkele key in deze lijst mag wijzigen of verdwijnen.** Nieuwe functionaliteit
komt er als NIEUWE entity met een NIEUWE key naast. Verifieer vóór elke commit dat
geen bestaande `key=`-waarde is gewijzigd of verwijderd t.o.v. deze lijst.

`unique_id`-suffix hieronder = `_<key>` (voorafgegaan door de mqtt_topic).

## sensor ([sensor.py](../sensor.py))

| key | unique_id-suffix | naam |
|-----|------------------|------|
| `temperature` | `_temperature` | Water Temperature |
| `ph_data` | `_ph_data` | pH |
| `ph_state` | `_ph_state` | pH State |
| `ph_pump` | `_ph_pump` | pH Pump |
| `ph_tank` | `_ph_tank` | pH Tank |
| `redox_data` | `_redox_data` | Redox (ORP) |
| `redox_setpoint` | `_redox_setpoint` | Redox Setpoint |
| `hydrolysis_data` | `_hydrolysis_data` | Hydrolysis Level |
| `hydrolysis_setpoint_sensor` | `_hydrolysis_setpoint_sensor` | Hydrolysis Setpoint (sensor) |
| `hydrolysis_state` | `_hydrolysis_state` | Hydrolysis State |
| `hydrolysis_runtime_total` | `_hydrolysis_runtime_total` | Cell Runtime Total |
| `hydrolysis_runtime_part` | `_hydrolysis_runtime_part` | Cell Runtime Part |
| `hydrolysis_pol1` | `_hydrolysis_pol1` | Cell Polarization 1 Runtime |
| `hydrolysis_pol2` | `_hydrolysis_pol2` | Cell Polarization 2 Runtime |
| `hydrolysis_changes` | `_hydrolysis_changes` | Polarization Changes |
| `filtration_state_sensor` | `_filtration_state_sensor` | Filtration State (sensor) |
| `filtration_speed_sensor` | `_filtration_speed_sensor` | Filtration Speed (sensor) |
| `filtration_mode_sensor` | `_filtration_mode_sensor` | Filtration Mode (sensor) |
| `relay_1` … `relay_7` | `_relay_1` … `_relay_7` | Relay 1 … Relay 7 |
| `relay_acid` | `_relay_acid` | Acid Pump Relay |
| `relay_valve` | `_relay_valve` | Valve Relay |
| `device_type` | `_device_type` | Device Type |
| `firmware_version` | `_firmware_version` | Firmware Version |
| `voltage_5v` | `_voltage_5v` | 5V Supply |
| `voltage_12v` | `_voltage_12v` | 12V Supply |
| `voltage_24v` | `_voltage_24v` | 24-30V Supply |
| `current_420ma` | `_current_420ma` | 4-20mA Output |
| `mb_requests` | `_mb_requests` | Modbus Requests |
| `mb_no_error` | `_mb_no_error` | Modbus Successful |
| `mb_no_response` | `_mb_no_response` | Modbus No Response |
| `chlorine_data` | `_chlorine_data` | Chlorine |
| `chlorine_setpoint_sensor` | `_chlorine_setpoint_sensor` | Chlorine Setpoint (sensor) |
| `conductivity` | `_conductivity` | Conductivity |
| `ionization_data` | `_ionization_data` | Ionization |
| `ionization_setpoint_sensor` | `_ionization_setpoint_sensor` | Ionization Setpoint (sensor) |

## binary_sensor ([binary_sensor.py](../binary_sensor.py))

| key | unique_id-suffix | naam |
|-----|------------------|------|
| `ph_alarm` | `_ph_alarm` | pH Alarm |
| `ph_tank_empty` | `_ph_tank_empty` | pH Tank Empty |
| `ph_flow` | `_ph_flow` | pH Flow Detection |
| `hydrolysis_flow_alarm` | `_hydrolysis_flow_alarm` | Hydrolysis Flow Alarm |
| `hydrolysis_low_alarm` | `_hydrolysis_low_alarm` | Hydrolysis Low Alarm |
| `cover_active` | `_cover_active` | Cover Active |
| `filtration_running` | `_filtration_running` | Filtration Running |

## switch ([switch.py](../switch.py))

| key | unique_id-suffix | naam |
|-----|------------------|------|
| `filtration` | `_filtration` | Filtration |
| `light` | `_light` | Light |
| `aux1` … `aux4` | `_aux1` … `_aux4` | Aux 1 … Aux 4 |

## select ([select.py](../select.py))

| key | unique_id-suffix | naam |
|-----|------------------|------|
| `filtration_mode` | `_filtration_mode` | Filtration Mode |
| `filtration_speed` | `_filtration_speed` | Filtration Speed |
| `boost_mode` | `_boost_mode` | Boost Mode |

## number ([number.py](../number.py))

| key | unique_id-suffix | naam |
|-----|------------------|------|
| `ph_min` | `_ph_min` | pH Min Setpoint |
| `ph_max` | `_ph_max` | pH Max Setpoint |
| `redox_setpoint_number` | `_redox_setpoint_number` | Redox Setpoint |
| `hydrolysis_setpoint` | `_hydrolysis_setpoint` | Hydrolysis Setpoint |
| `ionization_setpoint` | `_ionization_setpoint` | Ionization Setpoint |
| `chlorine_setpoint` | `_chlorine_setpoint` | Chlorine Setpoint |

## button ([button.py](../button.py))

| key | unique_id-suffix | naam |
|-----|------------------|------|
| `clear_errors` | `_clear_errors` | Clear Errors |
| `save_eeprom` | `_save_eeprom` | Save to EEPROM |
| `exec` | `_exec` | Execute Changes |

## Nieuwe keys toegevoegd door dit werkplan (NIET in originele contract)

Deze keys zijn NA de inventaris toegevoegd; ze breken niets omdat ze nieuw zijn.

| platform | key | fase |
|----------|-----|------|
| select | `light_mode` | 1.3 |
| button | `light_next_program` | 1.3 |
| sensor | `relay_base`, `relay_redox`, `relay_chlorine`, `relay_conductivity`, `relay_heating`, `relay_uv` | 2.1 |
| binary_sensor | `module_ph`, `module_redox`, `module_hydrolysis`, `module_chlorine`, `module_conductivity`, `module_ionization` | 2.2 |
| sensor | `mb_error_rate` | 2.3 |
| number | `heating_setpoint` | 2.4 |
| sensor | `berry_version` | 4 |
