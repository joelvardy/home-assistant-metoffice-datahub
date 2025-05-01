"""Config flow for the Met Office (DataHub) integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE, DOMAIN
from .metoffice_datahub_api import MetOfficeDataHubAPI

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(
            CONF_LATITUDE,
            default=None,
        ): NumberSelector(
            NumberSelectorConfig(
                min=-90,
                max=90,
                step="any",
                mode=NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_LONGITUDE,
            default=None,
        ): NumberSelector(
            NumberSelectorConfig(
                min=-180,
                max=180,
                step="any",
                mode=NumberSelectorMode.BOX,
            )
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    api = MetOfficeDataHubAPI(
        data[CONF_API_KEY],
        data[CONF_LATITUDE],
        data[CONF_LONGITUDE],
    )

    try:
        # Test the API connection by fetching hourly forecast
        await api.async_get_forecast("hourly")
    except Exception as err:
        _LOGGER.exception("Error validating input: %s", err)
        raise CannotConnect from err
    finally:
        await api.async_close()

    return {"title": f"Met Office ({data[CONF_LATITUDE]}, {data[CONF_LONGITUDE]})"}


class MetOfficeDataHubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Met Office (DataHub)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
