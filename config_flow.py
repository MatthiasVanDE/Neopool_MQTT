"""Config flow for NeoPool MQTT Controller integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_BERRY_ENABLED,
    CONF_DEVICE_NAME,
    CONF_MQTT_TOPIC,
    DEFAULT_BERRY_ENABLED,
    DEFAULT_DEVICE_NAME,
    DEFAULT_MQTT_TOPIC,
    DOMAIN,
)


class NeoPoolMQTTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NeoPool MQTT Controller."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Check if already configured with same topic
            await self.async_set_unique_id(user_input[CONF_MQTT_TOPIC])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_DEVICE_NAME],
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_NAME, default=DEFAULT_DEVICE_NAME): str,
                    vol.Required(CONF_MQTT_TOPIC, default=DEFAULT_MQTT_TOPIC): str,
                    vol.Optional(
                        CONF_BERRY_ENABLED, default=DEFAULT_BERRY_ENABLED
                    ): bool,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return NeoPoolMQTTOptionsFlowHandler()


class NeoPoolMQTTOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for NeoPool MQTT Controller.

    Note: ``config_entry`` is provided by the base class as a property in recent
    Home Assistant; do NOT assign ``self.config_entry`` here (it is deprecated and
    breaks on newer cores).
    """

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        entry = self.config_entry
        current_berry = entry.options.get(
            CONF_BERRY_ENABLED,
            entry.data.get(CONF_BERRY_ENABLED, True),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_BERRY_ENABLED, default=current_berry
                    ): bool,
                }
            ),
        )
