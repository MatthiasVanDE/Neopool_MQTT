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
| Sensor | 49 | Water Temperature, pH, Redox (ORP), Hydrolysis Level, Cell Runtime, Polarization Changes, Relay 1–7, named relays (Acid/Valve/Base/Redox/Chlorine/Conductivity/Heating/UV), Powerunit voltages, Modbus stats + error rate, Chlorine, Conductivity, Ionization, Berry version |
| Binary sensor | 13 | pH Alarm, pH Tank Empty, pH Flow, Hydrolysis Flow/Low Alarm, Cover Active, Filtration Running, Module present (pH/Redox/Hydrolysis/Chlorine/Conductivity/Ionization) |
| Switch | 6 | Filtration, Light, Aux 1–4 *(Aux only when the Berry option is enabled)* |
| Select | 4 | Filtration Mode, Filtration Speed, Boost Mode, Light Mode |
| Number | 7 | pH Min/Max, Redox / Hydrolysis / Ionization / Chlorine setpoints, Heating setpoint *(experimental)* |
| Button | 4 | Clear Errors, Save to EEPROM, Execute Changes, Light Next Program |

Module-dependent entities (Chlorine, Conductivity, Ionization, the named relays,
the heating setpoint, …) mark themselves *Unavailable* when the controller
doesn't report the corresponding subkey — they exist for everyone, but only
"light up" if the hardware/function is present. The integration does **not**
remove entities based on detected modules (that would break automations bound to
them); it keeps them and uses availability instead.

## Behaviour worth knowing

### Availability follows the Tasmota LWT

The integration subscribes to `tele/<topic>/LWT`. When Tasmota's Last Will
publishes `Offline`, **all entities become Unavailable** — and that explicitly
wins over the data-driven availability (a stale `Online` won't keep them alive).
`Online` restores availability. This makes a disconnected bridge visible in HA
instead of showing the last cached values forever.

### Filtration Speed

`NPFiltrationspeed` only meaningfully applies with configured speed control /
Manual mode on the device. The **Filtration Speed** select therefore behaves
explicitly (it no longer silently forces Manual mode):

- **While filtration is running** it sends the documented two-parameter form
  `NPFiltration 1 <speed>` (e.g. `NPFiltration 1 2`), setting state + speed in
  one command.
- **While filtration is off** it sends `NPFiltrationspeed <speed>`, setting the
  desired speed for when it next runs.

The integration does not do raw Modbus writes for filtration.

### Light

The original `Light` switch (on/off) is kept. Two extra controls were added:

- **Light Mode** select — Off / On / Auto (`NPLight 0 / 1 / 3`).
- **Light Next Program** button — advances to the next RGB program (`NPLight 4`).

### Berry commands (Aux switches)

`NPAux1..NPAux4` only exist when the Berry script `neopoolcmd.be` is loaded on
the ESP32. Enable **"Berry NeoPool commands installed"** during setup (or later
via the integration's Options) to create the Aux switches. Toggling the option
reloads the integration. For backward compatibility, config entries created
before this option existed default to *enabled*, so their existing Aux switches
are preserved.

### Heating setpoint (experimental)

If the controller reports a `Heating` relay function, an **experimental**,
default-disabled `Heating Setpoint` number appears. Setting it writes the
Modbus register `0x0416` (`MBF_PAR_HEATING_TEMP`) via `NPWrite` + `NPExec`
(RAM only — **never** `NPSave`). Verify the register address and value scaling
for your model before relying on it.

### EEPROM safety

`NPSave` persists settings to EEPROM, which has a limited number of write cycles
(guaranteed 100,000). The integration **never** calls `NPSave` automatically —
the high-level `NP…` setpoints are managed by the driver, and the experimental
heating write uses `NPExec` (RAM). Use the **Save to EEPROM** button only when
you deliberately want to persist a change.

### Privacy

The device's `NodeID` is **not** exposed (not as a serial number, attribute, or
in logs). The stable device identifier is the MQTT topic.

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
  __init__.py       # config-entry setup / unload, platform forwarding, options reload
  const.py          # MQTT topics, NP-commands, mode/speed/boost/light dicts, berry helper
  config_flow.py    # UI: MQTT topic + device name + Berry option; OptionsFlow
  coordinator.py    # MQTT subscribe/publish (SENSOR/RESULT/LWT), state cache, dispatcher
  entity.py         # base entity with dispatcher binding
  sensor.py         # 49 sensors (description-driven + Berry version)
  binary_sensor.py  # 13 binary sensors (incl. module diagnostics)
  switch.py         # filtration / light / aux1-4 (Aux conditional)
  select.py         # filtration mode / speed / boost / light mode
  number.py         # 6 setpoints + experimental heating setpoint
  button.py         # clear-errors / save / exec / light-next-program
```

Entity **display names are English** (set via `_attr_name`, which in Home
Assistant takes precedence over `translation_key`). The config and options
flows are translated (en/nl). Translating entity names to Dutch would require
switching every entity from `_attr_name` to `translation_key`; that was
deliberately not done to avoid touching working entities (see `CLAUDE.md`
REGEL 0). You can always rename entities locally in the HA UI.

## Troubleshooting

**No data appears after setup**
- Confirm HA's MQTT integration is connected to the same broker as your bridge.
- In the Tasmota console run `weblog 4` and look for `tele/<topic>/SENSOR`
  traffic. If you don't see it, check `Topic` and `TelePeriod`.

**Switch toggles "snap back" to old state**
- The broker is dropping retained messages or QoS isn't satisfied. Check HA
  logs filtered on `mqtt`.

**Filtration Speed doesn't change anything**
- See "Filtration Speed" above. Speed control requires a variable-speed pump
  configured on the controller; on a single-speed pump the command is a no-op.

**The Aux switches are missing**
- They are only created when the **Berry** option is enabled (the `neopoolcmd.be`
  script must be loaded on the ESP32). Enable it in the integration's Options.

**The NeoPool clock keeps resetting / is one hour off**
- The fix is in Tasmota, not here. See "The clock is not managed by this
  integration" above.

**An entity is Unavailable**
- Module-dependent entities (Chlorine, Conductivity, Ionization, named relays,
  heating setpoint, …) depend on optional hardware/function assignment. If your
  pool doesn't report it, the entity stays Unavailable — that's normal.
- If **everything** is Unavailable, the Tasmota bridge is probably offline (LWT
  `Offline`). Check the bridge / broker connection.

## Commands actually sent by this integration

`NPFiltration` (incl. the `1 <speed>` form), `NPFiltrationmode`,
`NPFiltrationspeed`, `NPLight` (modes 0/1/3/4), `NPAux1`..`NPAux4` *(Berry only)*,
`NPpHMin`, `NPpHMax`, `NPRedox`, `NPHydrolysis`, `NPIonization`, `NPChlorine`,
`NPBoost`, `NPEscape`, `NPSave` (button only), `NPExec`, `NPVersion` *(Berry,
once at setup)*, and `NPWrite 0x0416` *(only via the experimental heating
setpoint)*.

It deliberately does **not** send `NPTime`, `NPTelePeriod`, `NPRead`, or any
other direct Modbus register writes beyond the documented heating register.
