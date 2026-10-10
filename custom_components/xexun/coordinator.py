"""Polling coordinator for Xexun trackers."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from aiohttp import ClientError

from .api import TrackerStatus, XexunApi, XexunAuthError, XexunError
from .const import DOMAIN, LOOKBACK, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class XexunCoordinator(DataUpdateCoordinator[dict[str, TrackerStatus]]):
    """Fetches the newest entry of every configured tracker."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: XexunApi, trackers: dict[str, str]) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.api = api
        self.trackers = trackers  # imei -> name

    async def _async_update_data(self) -> dict[str, TrackerStatus]:
        end = dt_util.utcnow()
        start = end - LOOKBACK
        result: dict[str, TrackerStatus] = {}
        try:
            for imei in self.trackers:
                status = await self.api.get_status(imei, start, end)
                previous = (self.data or {}).get(imei)
                # Nothing inside the lookback window: keep the last value we knew about.
                if status.last_seen is None and previous is not None:
                    status = previous
                result[imei] = status
        except XexunAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (XexunError, ClientError, TimeoutError) as err:
            raise UpdateFailed(str(err)) from err
        return result
