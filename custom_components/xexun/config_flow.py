"""Config flow for Xexun Tracker."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from aiohttp import ClientError

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from . import parse_trackers
from .api import XexunApi, XexunAuthError, XexunError
from .const import CONF_THRESHOLD_HOURS, CONF_TRACKERS, DEFAULT_THRESHOLD_HOURS, DOMAIN

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        vol.Required(CONF_TRACKERS): TextSelector(TextSelectorConfig(multiline=True)),
    }
)


class XexunConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate(self, data: dict[str, Any]) -> str | None:
        try:
            parse_trackers(data[CONF_TRACKERS])
        except ValueError:
            return "invalid_trackers"
        api = XexunApi(async_get_clientsession(self.hass), data[CONF_USERNAME], data[CONF_PASSWORD])
        try:
            await api.login()
        except XexunAuthError:
            return "invalid_auth"
        except (XexunError, ClientError, TimeoutError):
            return "cannot_connect"
        return None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()
            if (error := await self._validate(user_input)) is None:
                return self.async_create_entry(title=user_input[CONF_USERNAME], data=user_input)
            errors["base"] = error
        return self.async_show_form(
            step_id="user", data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input), errors=errors
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reconfigure()

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry() if self.source == "reauth" else self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            if (error := await self._validate(user_input)) is None:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
            errors["base"] = error
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input or dict(entry.data)),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return XexunOptionsFlow()


class XexunOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_THRESHOLD_HOURS,
                    default=self.config_entry.options.get(CONF_THRESHOLD_HOURS, DEFAULT_THRESHOLD_HOURS),
                ): NumberSelector(NumberSelectorConfig(min=1, max=47, step=1, unit_of_measurement="h")),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
