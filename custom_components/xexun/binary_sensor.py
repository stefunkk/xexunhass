"""'No data' problem sensor: on when a tracker has been silent longer than the threshold."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import XexunConfigEntry
from .entity import XexunEntity


async def async_setup_entry(hass: HomeAssistant, entry: XexunConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities(NoDataSensor(coordinator, imei, coordinator.threshold) for imei in coordinator.trackers)


class NoDataSensor(XexunEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator, imei: str, threshold: timedelta) -> None:
        super().__init__(coordinator, imei, "no_data")
        self._threshold = threshold

    @property
    def is_on(self) -> bool | None:
        if self.status is None:
            return None
        last_seen = self.status.last_seen
        return last_seen is None or dt_util.utcnow() - last_seen > self._threshold

    @property
    def extra_state_attributes(self) -> dict:
        return {"threshold_hours": self._threshold.total_seconds() / 3600}
