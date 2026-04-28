# NeoPool MQTT Controller

Home Assistant custom integration for **Sugar Valley NeoPool** pool controllers
(Hidrolife, Aquascenic, Oxilife, Bionet, Hidroniser, UVScenic, Station, Brilix,
Bayrol, Hay, …) connected through a **Tasmota-flashed Modbus bridge** over MQTT.

## How it works

```
NeoPool controller  <-- RS-485 / Modbus -->  ESP with Tasmota NeoPool driver  <-- MQTT -->  Home Assistant
```

The integration subscribes to the topics published by Tasmota and never talks
Modbus directly:

| Direction | Topic | Purpose |
|---|---|---|
| In  | `tele/<topic>/SENSOR` | Full pool state, every `TelePeriod` seconds |
| In  | `stat/<topic>/RESULT` | Response to commands (used for instant UI updates) |
| Out | `cmnd/<topic>/NP…`    | Filtration / light / aux / setpoints / mode / speed / boost / errors / save / exec |

## Requirements

- Home Assistant with the **MQTT integration** configured and pointed at the same
  broker your Tasmota bridge uses.
- A Tasmota build that includes the **NeoPool driver** (`xsns_83_neopool`),
  flashed on the ESP that wires to your NeoPool's RS-485 port.
- `TelePeriod` enabled on Tasmota (the default 300 s is fine).

## Installation

1. Copy this folder to `<config>/custom_components/neopool_mqtt/`.
2. Restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → "NeoPool MQTT Controller"**.
4. Enter:
   - **Device name** — anything, becomes the HA device label (default `NeoPool`).
   - **MQTT topic** — must match the Tasmota device's `Topic` setting (default `SmartPool`).

## Entities

All entities live under a single device per config entry. Diagnostic ones are
disabled by default — enable them via the entity registry if you need them.

| Platform | Count | Highlights |
|---|---|---|
| Sensor | 41 | Water Temperature, pH, Redox (ORP), Hydrolysis Level, Cell Runtime, Polarization Changes, Relay 1–7, Acid/Valve relays, Powerunit voltages, Modbus stats, Chlorine, Conductivity, Ionization |
| Binary sensor | 7 | pH Alarm, pH Tank Empty, pH Flow, Hydrolysis Flow/Low Alarm, Cover Active, Filtration Running |
| Switch | 6 | Filtration, Light, Aux 1–4 |
| Select | 3 | Filtration Mode, Filtration Speed, Boost Mode |
| Number | 6 | pH Min/Max, Redox / Hydrolysis / Ionization / Chlorine setpoints |
| Button | 3 | Clear Errors, Save to EEPROM, Execute Changes |

Chlorine, Conductivity and Ionization entities mark themselves *Unavailable*
when the controller doesn't report the corresponding module — they exist for
everyone, but only "light up" if hardware is present.

## Behaviour worth knowing

### Filtration speed only applies in Manual mode

The NeoPool controller honours `NPFiltrationspeed` **only when the filtration
mode is Manual (0)**. In Auto / Smart / Intelligent / Heating the speed is
fixed by the timer-block configuration on the device.

To make the **Filtration Speed** select actually do something, the integration
switches the device to Manual mode *automatically* before sending the speed,
when needed. You'll see it in the log:

```
INFO ... Switching filtration to Manual mode so speed change takes effect (was mode=1)
```

If you want speed control while staying in Auto, you must configure the speeds
per timer-block on the controller's front panel. The integration does not do
raw Modbus writes.

### The clock is **not** managed by this integration

This integration never sends `NPTime`. Clock sync is the Tasmota bridge's job,
typically via a Tasmota rule:

```
Rule1 ON Time#Set DO NPTime 0 ENDON
Rule1 1
```

For that to give the *correct* time, Tasmota itself must have a working
timezone with DST. For Belgium / most of the EU:

```
Backlog Timezone 99; TimeDST 0,0,3,1,2,120; TimeSTD 0,0,10,1,3,60
```

A fixed `Timezone +01:00` will be **one hour off during summer time** — and
the rule will then dutifully push that wrong time to the NeoPool on every NTP
resync.

### Optimistic UI updates

When you flip a switch or move a setpoint, HA receives the Tasmota response
on `stat/<topic>/RESULT` within ~100 ms and updates the UI immediately,
without waiting for the next `tele/.../SENSOR` cycle.

## File layout

```
custom_components/neopool_mqtt/
  __init__.py       # config-entry setup / unload, platform forwarding
  const.py          # MQTT topics, NP-commands, mode/speed/boost dicts
  config_flow.py    # UI: MQTT topic + device name
  coordinator.py    # MQTT subscribe/publish, state cache, dispatcher
  entity.py         # base entity with dispatcher binding
  sensor.py         # 41 sensors via NeoPoolSensorDescription
  binary_sensor.py  # 7 binary sensors via NeoPoolBinarySensorDescription
  switch.py         # filtration / light / aux1-4
  select.py         # filtration mode / speed / boost
  number.py         # 6 setpoints via NeoPoolNumberDescription
  button.py         # clear-errors / save / exec
```

## Troubleshooting

**No data appears after setup**
- Confirm HA's MQTT integration is connected to the same broker as your bridge.
- In the Tasmota console run `weblog 4` and look for `tele/<topic>/SENSOR`
  traffic. If you don't see it, check `Topic` and `TelePeriod`.

**Switch toggles "snap back" to old state**
- The broker is dropping retained messages or QoS isn't satisfied. Check HA
  logs filtered on `mqtt`.

**Filtration Speed doesn't change anything**
- See "Filtration speed only applies in Manual mode" above. Either let the
  integration auto-switch to Manual or change mode yourself first.

**The NeoPool clock keeps resetting / is one hour off**
- The fix is in Tasmota, not here. See "The clock is not managed by this
  integration" above.

**An entity is Unavailable**
- Chlorine, Conductivity, and Ionization depend on optional hardware. If your
  pool doesn't have that module, the entity stays Unavailable — that's normal.

## Commands actually sent by this integration

`NPFiltration`, `NPFiltrationmode`, `NPFiltrationspeed`, `NPLight`,
`NPAux1`..`NPAux4`, `NPpHMin`, `NPpHMax`, `NPRedox`, `NPHydrolysis`,
`NPIonization`, `NPChlorine`, `NPBoost`, `NPEscape`, `NPSave`, `NPExec`.

It deliberately does **not** send `NPTime`, `NPTelePeriod`, `NPRead`,
`NPWrite`, or any direct Modbus register writes.
