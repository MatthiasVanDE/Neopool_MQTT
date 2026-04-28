"""NeoPool MQTT data coordinator."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    TOPIC_TELE_SENSOR,
    TOPIC_STAT_RESULT,
    TOPIC_CMND,
)

_LOGGER = logging.getLogger(__name__)

SIGNAL_NEOPOOL_UPDATE = f"{DOMAIN}_update"


class NeoPoolCoordinator:
    """Coordinate NeoPool MQTT data."""

    def __init__(self, hass: HomeAssistant, mqtt_topic: str, device_name: str, entry_id: str) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.mqtt_topic = mqtt_topic
        self.device_name = device_name
        self.entry_id = entry_id
        self.data: dict[str, Any] = {}
        self._unsub_sensor = None
        self._unsub_result = None
        self._available = False

    @property
    def available(self) -> bool:
        """Return True if data is available."""
        return self._available

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        info = {
            "identifiers": {(DOMAIN, self.mqtt_topic)},
            "name": self.device_name,
            "manufacturer": "Sugar Valley",
            "model": self.data.get("Type", "NeoPool"),
        }
        fw = self.data.get("Powerunit", {}).get("Version")
        if fw:
            info["sw_version"] = fw
        node_id = self.data.get("Powerunit", {}).get("NodeID")
        if node_id:
            info["serial_number"] = node_id
        return info

    async def async_setup(self) -> None:
        """Set up MQTT subscriptions."""
        sensor_topic = TOPIC_TELE_SENSOR.format(self.mqtt_topic)
        result_topic = TOPIC_STAT_RESULT.format(self.mqtt_topic)

        @callback
        def _sensor_message_received(msg):
            """Handle sensor MQTT message."""
            try:
                payload = json.loads(msg.payload)
            except (json.JSONDecodeError, TypeError):
                _LOGGER.warning("Invalid JSON in SENSOR message: %s", msg.payload)
                return

            neopool_data = payload.get("NeoPool")
            if neopool_data is None:
                return

            self.data = neopool_data
            self._available = True
            async_dispatcher_send(self.hass, f"{SIGNAL_NEOPOOL_UPDATE}_{self.entry_id}")

        @callback
        def _result_message_received(msg):
            """Handle result MQTT message for command responses."""
            try:
                payload = json.loads(msg.payload)
            except (json.JSONDecodeError, TypeError):
                return

            # Update relevant data from command results
            updated = False

            if "NPFiltration" in payload:
                filt_val = payload["NPFiltration"]
                if isinstance(filt_val, dict):
                    if "State" in self.data.get("Filtration", {}):
                        self.data["Filtration"]["State"] = filt_val.get("State", self.data["Filtration"]["State"])
                    if "Speed" in filt_val and "Filtration" in self.data:
                        self.data["Filtration"]["Speed"] = filt_val["Speed"]
                elif isinstance(filt_val, str):
                    if "Filtration" not in self.data:
                        self.data["Filtration"] = {}
                    self.data["Filtration"]["State"] = 1 if filt_val == "ON" else 0
                updated = True

            if "NPFiltrationmode" in payload:
                mode_str = payload["NPFiltrationmode"]
                from .const import FILTRATION_MODES
                for k, v in FILTRATION_MODES.items():
                    if v == mode_str:
                        if "Filtration" not in self.data:
                            self.data["Filtration"] = {}
                        self.data["Filtration"]["Mode"] = k
                        break
                updated = True

            if "NPFiltrationspeed" in payload:
                speed_str = payload["NPFiltrationspeed"]
                from .const import FILTRATION_SPEEDS
                for k, v in FILTRATION_SPEEDS.items():
                    if v == speed_str:
                        if "Filtration" not in self.data:
                            self.data["Filtration"] = {}
                        self.data["Filtration"]["Speed"] = k
                        break
                updated = True

            if "NPLight" in payload:
                light_val = payload["NPLight"]
                if isinstance(light_val, str):
                    self.data["Light"] = 1 if light_val == "ON" else 0
                else:
                    self.data["Light"] = light_val
                updated = True

            if "NPBoost" in payload:
                boost_val = payload["NPBoost"]
                from .const import BOOST_MODES
                if isinstance(boost_val, str):
                    for k, v in BOOST_MODES.items():
                        if v == boost_val:
                            if "Hydrolysis" not in self.data:
                                self.data["Hydrolysis"] = {}
                            self.data["Hydrolysis"]["Boost"] = k
                            break
                updated = True

            if "NPpHMax" in payload:
                if "pH" not in self.data:
                    self.data["pH"] = {}
                self.data["pH"]["Max"] = payload["NPpHMax"]
                updated = True

            if "NPpHMin" in payload:
                if "pH" not in self.data:
                    self.data["pH"] = {}
                self.data["pH"]["Min"] = payload["NPpHMin"]
                updated = True

            if "NPRedox" in payload:
                if "Redox" not in self.data:
                    self.data["Redox"] = {}
                self.data["Redox"]["Setpoint"] = payload["NPRedox"]
                updated = True

            if "NPHydrolysis" in payload:
                if "Hydrolysis" not in self.data:
                    self.data["Hydrolysis"] = {}
                self.data["Hydrolysis"]["Setpoint"] = payload["NPHydrolysis"]
                updated = True

            if "NPIonization" in payload:
                if "Ionization" not in self.data:
                    self.data["Ionization"] = {}
                self.data["Ionization"]["Setpoint"] = payload["NPIonization"]
                updated = True

            if "NPChlorine" in payload:
                if "Chlorine" not in self.data:
                    self.data["Chlorine"] = {}
                self.data["Chlorine"]["Setpoint"] = payload["NPChlorine"]
                updated = True

            if updated:
                self._available = True
                async_dispatcher_send(self.hass, f"{SIGNAL_NEOPOOL_UPDATE}_{self.entry_id}")

        self._unsub_sensor = await mqtt.async_subscribe(
            self.hass, sensor_topic, _sensor_message_received, 0
        )
        self._unsub_result = await mqtt.async_subscribe(
            self.hass, result_topic, _result_message_received, 0
        )

        _LOGGER.info(
            "NeoPool MQTT subscribed to %s and %s", sensor_topic, result_topic
        )

    async def async_unload(self) -> None:
        """Unload MQTT subscriptions."""
        if self._unsub_sensor:
            self._unsub_sensor()
        if self._unsub_result:
            self._unsub_result()

    async def async_send_command(self, command: str, payload: str = "") -> None:
        """Send a command via MQTT."""
        topic = TOPIC_CMND.format(self.mqtt_topic, command)
        _LOGGER.debug("Sending MQTT command: %s = %s", topic, payload)
        await mqtt.async_publish(self.hass, topic, str(payload), 0, False)
