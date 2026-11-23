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
| `ph_flow` | `_ph_flow` | pH Flow Alarm (heette tot 18-09-2026 "pH Flow Detection"; FL1 is een alarmbit) |
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

## Register-gebaseerde keys (18-09-2026)

Deze entiteiten lezen niet uit de SENSOR-JSON maar uit de registercache die
`NeoPoolCoordinator` vult met `NPRead`. Zie [REGISTERS.md](REGISTERS.md) voor de
registers en de gemeten waarden. Allemaal nieuwe keys; er is niets hernoemd.

| platform | key | register | standaard aan |
|----------|-----|----------|---------------|
| sensor | `backwash_remaining` | `0x04EF` | ja |
| sensor | `backwash_last_start` | `0x04EB/EC` | ja |
| sensor | `backwash_next_start` | afgeleid: `0x04EB/EC` + `0x04ED` | ja |
| sensor | `backwash_relay` | `0x04EA` | nee |
| sensor | `cell_pwm` | `0x010F` | nee |
| sensor | `cell_voltage` | `0x0111` | nee |
| sensor | `panel_time` | `0x0408/09` | nee |
| sensor | `panel_clock_drift` | afgeleid: `0x0408/09` vs HA | nee |
| sensor | `smart_interval_reduction` | `0x041B` | nee |
| sensor | `intelligent_bonus_time` | `0x041E` | nee |
| sensor | `intelligent_next_interval` | `0x041F` | nee |
| sensor | `intelligent_intervals` | `0x0420` | nee |
| sensor | `cell_pol_positive_time` | `0x0405` | nee |
| sensor | `cell_pol_negative_time` | `0x0406` | nee |
| sensor | `cell_pol_dead_time` | `0x0407` | nee |
| sensor | `cover_reduction_percent` | `0x042D` LSB | nee |
| sensor | `cover_shutdown_temp` | `0x042D` MSB | nee |
| sensor | `dosing_pump_time_on` | `0x042F` | nee |
| sensor | `dosing_pump_time_off` | `0x042E` | nee |
| sensor | `aux1_name` … `aux4_name` | `0x0610`, `0x0615`, `0x061A`, `0x061F` | nee |
| sensor | `filtration_speed_bits` | `0x010E` bits 8-10, ruw | nee |
| sensor | `input_status_raw` | `0x0062`, ruw hex | nee |
| select | `filtration_interval_speed` | `0x050F` bits 7-9 | ja |
| binary_sensor | `cover_closed` | `0x0062` bit 8 | ja |
| binary_sensor | `backwash_active` | `0x04EF` > 0 | ja |
| binary_sensor | `backwash_enabled` | `0x04E8` | nee |
| binary_sensor | `cover_reduction_enabled` | `0x042C` bit 0 | nee |
| binary_sensor | `temperature_shutdown_enabled` | `0x042C` bit 1 | nee |
| binary_sensor | `smart_antifreeze` | `0x041A` | nee |
| binary_sensor | `fl1_interlock` | `0x0403` bit 0 | nee |
| binary_sensor | `heating_active` | `0x0414` | nee |
| number | `smart_temp_high` | `0x0418` | nee |
| number | `smart_temp_low` | `0x0419` | nee |
| number | `intelligent_temp` | `0x041C` | nee |
| number | `intelligent_filt_min_time` | `0x041D` | nee |
| number | `backwash_period` | `0x04ED` | nee |
| number | `backwash_duration` | `0x04EE` | nee |
| number | `dosing_pump_max_time` | `0x0431` | nee |

De `number`-entiteiten schrijven met `NPWrite` + `NPExec` en staan daarom standaard
uit, met `EntityCategory.CONFIG`. Ze tonen wat het paneel werkelijk opgeslagen heeft:
na het schrijven volgt een `NPRead` van hetzelfde register.

## Gewijzigd gedrag van bestaande entiteiten (18-09-2026)

Geen enkele key is gewijzigd; twee entiteiten geven wel een andere **waarde** dan
voorheen, omdat de oude waarde aantoonbaar fout was.

| key | was | is |
|-----|-----|-----|
| `filtration_speed_sensor` | `Filtration.Speed` uit de SENSOR-JSON | gedecodeerd uit de relaislijnen `0x010E` bits 8-10 |
| `filtration_speed` (select) | idem | idem, met terugval op de JSON zolang `0x010E` nog niet gelezen is |

De select `filtration_speed` schrijft nog altijd `NPFiltrationspeed`, en dat zet enkel
het **standaard**snelheidsveld (`0x050F` bits 4-6). Het paneel past dat alleen toe
buiten een filtratie-interval. De nieuwe select `filtration_interval_speed` schrijft
bits 7-9, het veld dat de pomp stuurt terwijl een timerinterval loopt — dat is de
knop die tijdens de filtratie iets doet.

Tasmota's `NeoPoolGetFiltrationSpeed()` herkent alleen one-hot relaislijnen (1, 2, 4)
en valt voor elke andere combinatie terug op de **ingestelde standaardsnelheid**. Op
een pomp waarvan de snelheidslijnen optellend bedraad zijn — zoals hier: `0b001` = Low,
`0b011` = Mid — rapporteerde het daardoor `High` terwijl de pomp meetbaar op Mid liep.
Beide entiteiten melden nu niets (`unknown`) in plaats van een gok wanneer er geen
enkele snelheidslijn bekrachtigd is; `binary_sensor.neopool_filtration_running` zegt
in dat geval al dat de pomp stilstaat.
