"""The Met Office (DataHub) integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .metoffice_datahub_api import MetOfficeDataHubAPI

PLATFORMS: list[Platform] = [Platform.WEATHER]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Met Office (DataHub) from a config entry.

    Args:
        hass: The Home Assistant instance
        entry: The config entry containing the integration configuration

    Returns:
        bool: True if setup was successful, False otherwise
    """
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = MetOfficeDataHubAPI(
        entry.data["api_key"],
        entry.data["latitude"],
        entry.data["longitude"],
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: The Home Assistant instance
        entry: The config entry to unload

    Returns:
        bool: True if unload was successful, False otherwise
    """
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        api = hass.data[DOMAIN].pop(entry.entry_id)
        await api.async_close()

    return unload_ok
