"""NeoPool MQTT data coordinator."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    BOOST_MODES_REVERSE,
    DOMAIN,
    FILTRATION_MODES_REVERSE,
    FILTRATION_SPEEDS_REVERSE,
    LIGHT_MODES_REVERSE,
    LIGHT_TOGGLE,
    LWT_OFFLINE,
    LWT_ONLINE,
    MANUFACTURER,
    TOPIC_CMND,
    TOPIC_STAT_RESULT,
    TOPIC_TELE_LWT,
    TOPIC_TELE_SENSOR,
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
    ) -> None:
        self.hass = hass
        self.mqtt_topic = mqtt_topic
        self.device_name = device_name
        self.entry_id = entry_id
        self.data: dict[str, Any] = {}
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

    async def async_unload(self) -> None:
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
        self._available = True
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

    def _apply_result(self, key: str, value: Any) -> bool:
        """Update local state for a single command result. Returns True if changed."""
        if key == "NPFiltration":
            state = _on_off_to_int(value)
            if state is not None:
                self.data.setdefault("Filtration", {})["State"] = state
                return True
            return False

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
