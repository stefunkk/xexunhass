"""Polling coordinator for Xexun trackers."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from aiohttp import ClientError

from .api import TrackerStatus, XexunApi, XexunAuthError, XexunError
from .const import CONF_THRESHOLD_HOURS, DEFAULT_THRESHOLD_HOURS, DOMAIN, LOOKBACK, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class XexunCoordinator(DataUpdateCoordinator[dict[str, TrackerStatus]]):
    """Fetches the newest entry of every configured tracker."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: XexunApi, trackers: dict[str, str]) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.api = api
        self.trackers = trackers  # imei -> name
        self.threshold = timedelta(hours=entry.options.get(CONF_THRESHOLD_HOURS, DEFAULT_THRESHOLD_HOURS))
        self._unsub_deadline: CALLBACK_TYPE | None = None

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
        self._schedule_deadline_check(result, end)
        return result

    def _schedule_deadline_check(self, data: dict[str, TrackerStatus], now: datetime) -> None:
        """Refresh right when a tracker would cross the threshold, so a long poll interval does not delay the alert."""
        if self._unsub_deadline:
            self._unsub_deadline()
            self._unsub_deadline = None
        deadlines = [
            status.last_seen + self.threshold + timedelta(minutes=1)
            for status in data.values()
            if status.last_seen is not None and now - status.last_seen <= self.threshold
        ]
        if deadlines and (deadline := min(deadlines)) < now + SCAN_INTERVAL:
            self._unsub_deadline = async_track_point_in_utc_time(self.hass, self._deadline_reached, deadline)

    @callback
    def _deadline_reached(self, _now: datetime) -> None:
        self._unsub_deadline = None
        self.hass.async_create_task(self.async_request_refresh())

    async def async_shutdown(self) -> None:
        if self._unsub_deadline:
            self._unsub_deadline()
            self._unsub_deadline = None
        await super().async_shutdown()
