"""Base entity for Xexun trackers."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import TrackerStatus
from .const import DOMAIN
from .coordinator import XexunCoordinator


class XexunEntity(CoordinatorEntity[XexunCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: XexunCoordinator, imei: str, key: str) -> None:
        super().__init__(coordinator)
        self.imei = imei
        self._attr_translation_key = key
        self._attr_unique_id = f"{imei}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, imei)},
            name=coordinator.trackers[imei],
            manufacturer="Xexun",
            serial_number=imei,
        )

    @property
    def status(self) -> TrackerStatus | None:
        return (self.coordinator.data or {}).get(self.imei)
