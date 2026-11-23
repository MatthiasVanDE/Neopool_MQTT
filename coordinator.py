"""NeoPool MQTT data coordinator."""
from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    BOOST_MODES_REVERSE,
    FILTRATION_MODE_MANUAL,
    CMD_NPEXEC,
    CMD_NPREAD,
    CMD_NPVERSION,
    CMD_NPWRITE,
    DOMAIN,
    FILTRATION_MODES_REVERSE,
    FILTRATION_SPEEDS_REVERSE,
    HYDROLYSIS_UNIT_CONFIRM,
    LIGHT_MODES_REVERSE,
    LIGHT_TOGGLE,
    LWT_OFFLINE,
    LWT_ONLINE,
    MANUFACTURER,
    configured_interval_speed,
    cover_closed_from_input,
    filtration_speed_from_relays,
    filtration_speed_relay_bits,
    MASK_FILTRATION_CONF_INT1_SPEED,
    REG_AUX_NAME_LENGTH,
    REG_INPUT_STATUS,
    REG_PAR_FILTRATION_CONF,
    REG_PAR_UICFG_MACH_NAME_AUX,
    REG_RELAY_STATE,
    SHIFT_FILTRATION_CONF_INT1_SPEED,
    REGISTER_BLOCKS,
    REGISTER_BLOCKS_FAST,
    REGISTER_BLOCKS_STATIC,
    REGISTER_POLL_FAST_SECONDS,
    REGISTER_POLL_INTERVAL_MINUTES,
    TOPIC_CMND,
    TOPIC_STAT_RESULT,
    TOPIC_TELE_LWT,
    TOPIC_TELE_SENSOR,
    UNIT_PERCENT,
)

_LOGGER = logging.getLogger(__name__)

SIGNAL_NEOPOOL_UPDATE = f"{DOMAIN}_update"


def _on_off_to_int(value: Any) -> int | None:
    """Convert Tasmota ON/OFF (case-insensitive) or 0/1 to int."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        upper = value.strip().upper()
        if upper in ("ON", "1", "TRUE"):
            return 1
        if upper in ("OFF", "0", "FALSE"):
            return 0
    return None


def _label_to_int(value: Any, label_to_key: dict[str, int]) -> int | None:
    """Look up an int key by case-insensitive label, or accept an int directly."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, str):
        upper = value.strip().upper()
        for label, key in label_to_key.items():
            if label.upper() == upper:
                return key
    return None


class NeoPoolCoordinator:
    """Coordinate NeoPool MQTT data."""

    def __init__(
        self,
        hass: HomeAssistant,
        mqtt_topic: str,
        device_name: str,
        entry_id: str,
        berry_enabled: bool = False,
        flow_required_aux: frozenset[int] | None = None,
        speed_controller: str = "",
    ) -> None:
        self.hass = hass
        self.mqtt_topic = mqtt_topic
        self.device_name = device_name
        self.entry_id = entry_id
        self.berry_enabled = berry_enabled
        # Aux outputs that may not run without filtration, and the automation that
        # owns the interval speed. Both are installation facts the panel cannot tell
        # us, so they come from the options flow; empty means no interlock.
        self.flow_required_aux = flow_required_aux or frozenset()
        self.speed_controller = speed_controller
        # Berry driver version (from NPVersion RESULT); not present in SENSOR JSON.
        self.berry_version: str | None = None
        self.data: dict[str, Any] = {}
        # Raw Modbus registers read with NPRead, keyed by address. Everything the
        # SENSOR JSON does not carry (backwash valve, smart/intelligent mode, ...)
        # lives here; see const.REGISTER_BLOCKS.
        self.registers: dict[int, int] = {}
        # Hydrolysis unit as last confirmed; see _track_hydrolysis_unit.
        self._hydrolysis_unit: str | None = None
        self._hydrolysis_unit_candidate: str | None = None
        self._hydrolysis_unit_count = 0
        # Guards the one-shot re-request in _on_sensor_message.
        self._registers_requested = False
        self._unsub_poll = None
        self._unsub_poll_fast = None
        self._unsub_sensor = None
        self._unsub_result = None
        self._unsub_lwt = None
        # Data-driven availability: True once we've seen a SENSOR/RESULT message.
        self._available = False
        # LWT availability: None = unknown, True = Online, False = Offline.
        # An explicit Offline LWT overrides the data-driven flag.
        self._lwt_online: bool | None = None

    @property
    def available(self) -> bool:
        if self._lwt_online is False:
            return False
        return self._available

    @property
    def signal(self) -> str:
        return f"{SIGNAL_NEOPOOL_UPDATE}_{self.entry_id}"

    @property
    def device_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {
            "identifiers": {(DOMAIN, self.mqtt_topic)},
            "name": self.device_name,
            "manufacturer": MANUFACTURER,
            "model": self.data.get("Type", "NeoPool"),
        }
        powerunit = self.data.get("Powerunit") or {}
        if powerunit.get("Version"):
            info["sw_version"] = powerunit["Version"]
        # NodeID is intentionally NOT exposed (sensitive identifier). The stable
        # device identifier is the mqtt_topic, already set in "identifiers".
        return info

    async def async_setup(self) -> None:
        sensor_topic = TOPIC_TELE_SENSOR.format(self.mqtt_topic)
        result_topic = TOPIC_STAT_RESULT.format(self.mqtt_topic)
        lwt_topic = TOPIC_TELE_LWT.format(self.mqtt_topic)

        self._unsub_sensor = await mqtt.async_subscribe(
            self.hass, sensor_topic, self._on_sensor_message, 0
        )
        self._unsub_result = await mqtt.async_subscribe(
            self.hass, result_topic, self._on_result_message, 0
        )
        self._unsub_lwt = await mqtt.async_subscribe(
            self.hass, lwt_topic, self._on_lwt_message, 0
        )

        _LOGGER.info(
            "NeoPool MQTT subscribed to %s, %s and %s",
            sensor_topic,
            result_topic,
            lwt_topic,
        )

        # Berry-only: request the driver version once so the diagnostic sensor can
        # populate. Harmless no-op on devices without neopoolcmd.be (no RESULT).
        if self.berry_enabled:
            await self.async_send_command(CMD_NPVERSION)

        # NPRead is part of the stock Tasmota NeoPool driver, so this needs no Berry
        # script. Arm the polls *before* the first read: at startup this integration
        # can be set up before the MQTT client finishes connecting, and a first read
        # that goes nowhere must not cost us the periodic refresh as well.
        self._unsub_poll = async_track_time_interval(
            self.hass,
            self._async_poll_registers,
            timedelta(minutes=REGISTER_POLL_INTERVAL_MINUTES),
        )
        # The speed lines are live state, not configuration: polling them every five
        # minutes would make the speed sensor useless.
        self._unsub_poll_fast = async_track_time_interval(
            self.hass,
            self._async_poll_registers_fast,
            timedelta(seconds=REGISTER_POLL_FAST_SECONDS),
        )
        try:
            await self.async_refresh_all_registers()
        except Exception:  # noqa: BLE001 - never fail setup over a first read
            _LOGGER.debug(
                "NeoPool: initial register read failed, retrying on the next poll",
                exc_info=True,
            )

    async def async_unload(self) -> None:
        if self._unsub_poll:
            self._unsub_poll()
        if self._unsub_poll_fast:
            self._unsub_poll_fast()
        if self._unsub_sensor:
            self._unsub_sensor()
        if self._unsub_result:
            self._unsub_result()
        if self._unsub_lwt:
            self._unsub_lwt()

    async def async_send_command(self, command: str, payload: str = "") -> None:
        topic = TOPIC_CMND.format(self.mqtt_topic, command)
        _LOGGER.debug("NeoPool MQTT publish: %s = %s", topic, payload)
        await mqtt.async_publish(self.hass, topic, str(payload), 0, False)

    async def _async_poll_registers(self, _now: Any = None) -> None:
        """Interval callback: refresh the configuration registers."""
        await self.async_refresh_registers()

    async def _async_poll_registers_fast(self, _now: Any = None) -> None:
        """Interval callback: refresh the live state registers."""
        await self.async_refresh_registers(REGISTER_BLOCKS_FAST)

    async def async_refresh_all_registers(self) -> None:
        """Every block there is: slow, fast and read-once.

        Used at setup and by the self-heal in _on_sensor_message. Asking only for the
        slow blocks there would leave the live registers - and with them the pool
        cover - unavailable until the next fast poll.
        """
        await self.async_refresh_registers(include_static=True)
        await self.async_refresh_registers(REGISTER_BLOCKS_FAST)

    async def async_refresh_registers(
        self,
        blocks: tuple[tuple[int, int], ...] | None = None,
        include_static: bool = False,
    ) -> None:
        """Request register blocks with NPRead; answers arrive on stat/.../RESULT."""
        todo = list(REGISTER_BLOCKS if blocks is None else blocks)
        if include_static:
            todo += list(REGISTER_BLOCKS_STATIC)
        for address, count in todo:
            await self.async_send_command(CMD_NPREAD, f"0x{address:04X} {count}")

    async def async_write_register(self, address: int, value: int) -> None:
        """Write one register and read it back.

        NPWrite lands in RAM and NPExec activates it; nothing is written to EEPROM
        (that is what the "Save to EEPROM" button is for), so a panel power cycle
        reverts the change. The read-back means entities show what the panel really
        stored instead of what we hoped it would store.
        """
        await self.async_send_command(CMD_NPWRITE, f"0x{address:04X} {value}")
        await self.async_send_command(CMD_NPEXEC)
        await self.async_send_command(CMD_NPREAD, f"0x{address:04X} 1")

    @property
    def speed_controller_on(self) -> bool:
        """True while the configured automation owns the filtration interval speed."""
        if not self.speed_controller or self.hass is None:
            return False
        state = self.hass.states.get(self.speed_controller)
        return state is not None and state.state == "on"

    @property
    def speed_controller_name(self) -> str:
        """The controller's friendly name, falling back to its entity id."""
        if self.hass is not None and self.speed_controller:
            state = self.hass.states.get(self.speed_controller)
            if state is not None:
                return state.attributes.get("friendly_name") or self.speed_controller
        return self.speed_controller

    @property
    def filtration_mode(self) -> int | None:
        """Filtration mode (0 = Manual), or None while no SENSOR message has landed."""
        mode = (self.data.get("Filtration") or {}).get("Mode")
        return mode if isinstance(mode, int) and not isinstance(mode, bool) else None

    @property
    def timer_interval_driving(self) -> bool:
        """True when a filtration timer interval is what is driving the pump.

        Outside Manual mode the panel starts filtration from its own timer, and while
        such an interval runs the speed comes from MBF_PAR_FILTRATION_CONF bits 7-9;
        the default speed field is ignored until the interval ends. An unknown mode
        counts as "not driving": a control is only greyed out on something we read,
        never on a guess.
        """
        mode = self.filtration_mode
        if mode is None or mode == FILTRATION_MODE_MANUAL:
            return False
        return (self.data.get("Filtration") or {}).get("State") == 1

    @property
    def filtration_running(self) -> bool | None:
        """Whether the filtration pump is on, or None if the panel has not said."""
        state = (self.data.get("Filtration") or {}).get("State")
        return None if state is None else state == 1

    def aux_on(self, aux_num: int) -> bool | None:
        """Whether Aux<n> (1..4) is energised, or None if the panel has not said."""
        aux = (self.data.get("Relay") or {}).get("Aux")
        if not isinstance(aux, list) or len(aux) < aux_num:
            return None
        return aux[aux_num - 1] == 1

    def aux_label(self, aux_num: int) -> str:
        """"Aux 4", plus the name the panel has for it when that has been read."""
        label = f"Aux {aux_num}"
        if 1 <= aux_num <= len(REG_PAR_UICFG_MACH_NAME_AUX):
            name = self.register_string(
                REG_PAR_UICFG_MACH_NAME_AUX[aux_num - 1], REG_AUX_NAME_LENGTH
            )
            if name:
                return f"{label} ({name})"
        return label

    @property
    def hydrolysis_unit(self) -> str:
        """Unit of the hydrolysis level and setpoint ("%" or "g/h"), debounced."""
        return self._hydrolysis_unit or UNIT_PERCENT

    def _track_hydrolysis_unit(self, data: dict[str, Any]) -> None:
        """Follow Hydrolysis.Unit, but ignore a unit that shows up only briefly.

        Tasmota decides the unit on every cycle from MBF_PAR_UICFG_MACHINE and
        MBF_PAR_UICFG_MACH_VISUAL_STYLE. A single misread of either flips the label
        for one message while the value (raw / 10) stays the same; seen on an
        OxiLife set to %, which reported "g/h" once. Home Assistant reacts to any
        unit change by suppressing long-term statistics, so a new unit only counts
        once it has been reported HYDROLYSIS_UNIT_CONFIRM times in a row.
        """
        unit = (data.get("Hydrolysis") or {}).get("Unit")
        if not unit:
            return
        if self._hydrolysis_unit is None or unit == self._hydrolysis_unit:
            self._hydrolysis_unit = unit
            self._hydrolysis_unit_candidate = None
            self._hydrolysis_unit_count = 0
            return
        if unit == self._hydrolysis_unit_candidate:
            self._hydrolysis_unit_count += 1
        else:
            self._hydrolysis_unit_candidate = unit
            self._hydrolysis_unit_count = 1
        if self._hydrolysis_unit_count >= HYDROLYSIS_UNIT_CONFIRM:
            _LOGGER.info(
                "Hydrolysis unit changed from %s to %s", self._hydrolysis_unit, unit
            )
            self._hydrolysis_unit = unit
            self._hydrolysis_unit_candidate = None
            self._hydrolysis_unit_count = 0

    @property
    def filtration_speed(self) -> int | None:
        """Speed (1..3) the panel is really driving, from the relay lines."""
        return filtration_speed_from_relays(self.registers.get(REG_RELAY_STATE))

    @property
    def filtration_speed_bits(self) -> int | None:
        """The raw speed lines (0..7), for diagnosing an unfamiliar pump wiring."""
        return filtration_speed_relay_bits(self.registers.get(REG_RELAY_STATE))

    @property
    def cover_closed(self) -> bool | None:
        """Pool cover, read from the undocumented input mirror at 0x0062."""
        return cover_closed_from_input(self.registers.get(REG_INPUT_STATUS))

    @property
    def configured_speed(self) -> int | None:
        """Speed (1..3) configured for filtration timer interval 1."""
        return configured_interval_speed(self.registers.get(REG_PAR_FILTRATION_CONF))

    async def async_set_interval_speed(self, speed: int) -> None:
        """Set the speed for filtration timer interval 1 (1..3).

        This is the field that actually governs the pump while a filtration timer
        is running; NPFiltrationspeed only writes the default speed, which applies
        outside the intervals. Only the speed bits are touched, so the pump type and
        the default speed are left exactly as the panel has them.
        """
        current = self.registers.get(REG_PAR_FILTRATION_CONF)
        if current is None:
            _LOGGER.warning(
                "NeoPool: filtration config register not read yet, cannot set speed"
            )
            return
        value = (current & ~MASK_FILTRATION_CONF_INT1_SPEED) | (
            (speed - 1) << SHIFT_FILTRATION_CONF_INT1_SPEED
        )
        await self.async_write_register(REG_PAR_FILTRATION_CONF, value)

    def register(self, address: int) -> int | None:
        """One 16-bit register, or None if it has not been read yet."""
        return self.registers.get(address)

    def register_long(self, address: int) -> int | None:
        """A 32-bit value stored as low word first, as the panel does."""
        low = self.registers.get(address)
        high = self.registers.get(address + 1)
        if low is None or high is None:
            return None
        return low | (high << 16)

    def register_string(self, address: int, count: int) -> str | None:
        """An ASCIIZ string packed two characters per register, high byte first."""
        raw = bytearray()
        for offset in range(count):
            value = self.registers.get(address + offset)
            if value is None:
                return None
            raw += bytes(((value >> 8) & 0xFF, value & 0xFF))
        text = raw.split(b"\x00")[0]
        try:
            return text.decode("ascii").strip() or None
        except UnicodeDecodeError:
            return None

    @callback
    def _on_sensor_message(self, msg) -> None:
        try:
            payload = json.loads(msg.payload)
        except (json.JSONDecodeError, TypeError):
            _LOGGER.warning("Invalid JSON in SENSOR message: %s", msg.payload)
            return

        neopool = payload.get("NeoPool")
        if neopool is None:
            return

        self.data = neopool
        self._track_hydrolysis_unit(neopool)
        self._available = True

        # Self-heal: telemetry is flowing but no register answer ever arrived - most
        # likely the reads at setup were published before MQTT was connected. Ask
        # again now rather than leaving the register entities unavailable until the
        # next slow poll (or forever, if the static block was the one that was lost).
        if self.hass is not None and not self.registers and not self._registers_requested:
            self._registers_requested = True
            self.hass.async_create_task(self.async_refresh_all_registers())

        async_dispatcher_send(self.hass, self.signal)

    @callback
    def _on_lwt_message(self, msg) -> None:
        """Track availability from the Tasmota Last Will (LWT) topic."""
        payload = msg.payload
        if isinstance(payload, bytes):
            payload = payload.decode(errors="ignore")
        payload = (payload or "").strip()

        if payload == LWT_ONLINE:
            online = True
        elif payload == LWT_OFFLINE:
            online = False
        else:
            _LOGGER.debug("Unrecognised LWT payload: %s", payload)
            return

        if online == self._lwt_online:
            return
        self._lwt_online = online
        async_dispatcher_send(self.hass, self.signal)

    @callback
    def _on_result_message(self, msg) -> None:
        """Apply optimistic updates from command responses."""
        try:
            payload = json.loads(msg.payload)
        except (json.JSONDecodeError, TypeError):
            return

        updated = False
        for key, value in payload.items():
            if self._apply_result(key, value):
                updated = True

        if updated:
            self._available = True
            async_dispatcher_send(self.hass, self.signal)

    def _apply_register_read(self, value: Any) -> bool:
        """Cache an {"Address": a, "Data": [...]} answer from NPRead."""
        if not isinstance(value, dict):
            return False
        address = value.get("Address")
        data = value.get("Data")
        if not isinstance(address, int) or isinstance(address, bool):
            return False
        if isinstance(data, int) and not isinstance(data, bool):
            data = [data]
        if not isinstance(data, list):
            return False

        changed = False
        for offset, item in enumerate(data):
            if not isinstance(item, int) or isinstance(item, bool):
                continue
            if self.registers.get(address + offset) != item:
                self.registers[address + offset] = item
                changed = True
        return changed

    def _apply_result(self, key: str, value: Any) -> bool:
        """Update local state for a single command result. Returns True if changed."""
        if key == "NPRead":
            return self._apply_register_read(value)

        if key == "NPVersion":
            self.berry_version = str(value)
            return True

        if key == "NPFiltration":
            # Accept both the scalar form ("1") and the combined state+speed form
            # ("1 2", space-separated) sent by the speed select when running.
            state_tok: Any = value
            speed_tok: Any = None
            if isinstance(value, str) and len(value.split()) > 1:
                parts = value.split()
                state_tok, speed_tok = parts[0], parts[1]
            changed = False
            state = _on_off_to_int(state_tok)
            if state is not None:
                self.data.setdefault("Filtration", {})["State"] = state
                changed = True
            if speed_tok is not None:
                try:
                    speed: int | None = int(speed_tok)
                except (TypeError, ValueError):
                    speed = _label_to_int(speed_tok, FILTRATION_SPEEDS_REVERSE)
                if speed is not None:
                    self.data.setdefault("Filtration", {})["Speed"] = speed
                    changed = True
            return changed

        if key == "NPFiltrationmode":
            mode = _label_to_int(value, FILTRATION_MODES_REVERSE)
            if mode is not None:
                self.data.setdefault("Filtration", {})["Mode"] = mode
                return True
            return False

        if key == "NPFiltrationspeed":
            speed = _label_to_int(value, FILTRATION_SPEEDS_REVERSE)
            if speed is not None:
                self.data.setdefault("Filtration", {})["Speed"] = speed
                return True
            return False

        if key == "NPLight":
            # Accept ON/OFF, numeric modes (0/1/3), labels (Off/On/Auto), toggle (2).
            light = _label_to_int(value, LIGHT_MODES_REVERSE)
            if light is None:
                light = _on_off_to_int(value)
            if light == LIGHT_TOGGLE:
                current = self.data.get("Light")
                light = 0 if current == 1 else 1
            if light is not None:
                self.data["Light"] = light
                return True
            return False

        if key == "NPBoost":
            boost = _label_to_int(value, BOOST_MODES_REVERSE)
            if boost is not None:
                self.data.setdefault("Hydrolysis", {})["Boost"] = boost
                return True
            return False

        if key == "NPpHMin":
            self.data.setdefault("pH", {})["Min"] = value
            return True
        if key == "NPpHMax":
            self.data.setdefault("pH", {})["Max"] = value
            return True
        if key == "NPRedox":
            self.data.setdefault("Redox", {})["Setpoint"] = value
            return True
        if key == "NPHydrolysis":
            self.data.setdefault("Hydrolysis", {})["Setpoint"] = value
            return True
        if key == "NPIonization":
            self.data.setdefault("Ionization", {})["Setpoint"] = value
            return True
        if key == "NPChlorine":
            self.data.setdefault("Chlorine", {})["Setpoint"] = value
            return True

        if key.startswith("NPAux") and len(key) == 6 and key[5].isdigit():
            idx = int(key[5])
            if 1 <= idx <= 4:
                state = _on_off_to_int(value)
                if state is not None:
                    relay = self.data.setdefault("Relay", {})
                    aux = relay.setdefault("Aux", [0, 0, 0, 0])
                    while len(aux) < idx:
                        aux.append(0)
                    aux[idx - 1] = state
                    return True
            return False

        return False
