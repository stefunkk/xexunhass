"""Xexun Tracker integration: reports when trackers stop sending data."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import XexunApi
from .const import CONF_TRACKERS
from .coordinator import XexunCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

type XexunConfigEntry = ConfigEntry[XexunCoordinator]


def parse_trackers(text: str) -> dict[str, str]:
    """Parse lines like 'Rex: 869469000000001' into {imei: name}."""
    trackers: dict[str, str] = {}
    for line in text.replace(",", "\n").splitlines():
        if not line.strip():
            continue
        name, sep, imei = line.rpartition(":")
        imei = imei.strip()
        if not sep:
            name = imei
        if not imei.isdigit():
            raise ValueError(line)
        trackers[imei] = name.strip() or imei
    if not trackers:
        raise ValueError("empty")
    return trackers


async def async_setup_entry(hass: HomeAssistant, entry: XexunConfigEntry) -> bool:
    api = XexunApi(async_get_clientsession(hass), entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    coordinator = XexunCoordinator(hass, entry, api, parse_trackers(entry.data[CONF_TRACKERS]))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: XexunConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: XexunConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
