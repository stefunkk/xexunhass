"""Last-seen and battery sensors."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import XexunConfigEntry
from .entity import XexunEntity


async def async_setup_entry(hass: HomeAssistant, entry: XexunConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []
    for imei in coordinator.trackers:
        entities += [LastSeenSensor(coordinator, imei, "last_seen"), BatterySensor(coordinator, imei, "battery")]
    async_add_entities(entities)


class LastSeenSensor(XexunEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        return self.status.last_seen if self.status else None


class BatterySensor(XexunEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> int | None:
        return self.status.battery if self.status else None
