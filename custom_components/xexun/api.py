"""Minimal client for the Xexun tracker web API."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import aiohttp

from .const import DATA_URL, LOGIN_URL


class XexunError(Exception):
    """Generic API error."""


class XexunAuthError(XexunError):
    """Login rejected or token expired."""


@dataclass
class TrackerStatus:
    """Newest known state of a tracker."""

    last_seen: datetime | None
    battery: int | None


class XexunApi:
    """Logs in once and re-logs in when the token expires."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._token: str | None = None

    async def login(self) -> None:
        payload = {
            "userName": self._username,
            "password": base64.b64encode(self._password.encode()).decode(),
            "mode": "none",
        }
        async with self._session.post(LOGIN_URL, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            body = await resp.json(content_type=None)
        if not body.get("success") or not (body.get("data") or {}).get("token"):
            raise XexunAuthError(body.get("message") or "login failed")
        self._token = body["data"]["token"]

    async def _page(self, imei: str, start: datetime, end: datetime, page: int) -> dict[str, Any]:
        """Fetch one single-record page. Records are sorted oldest first and the API ignores sort params."""
        payload = {
            "startTime": int(start.timestamp() * 1000),
            "endTime": int(end.timestamp() * 1000),
            "imei": [imei],
            "pageNum": page,
            "pageSize": 1,
            "dataType": "",
        }
        for attempt in range(2):
            if self._token is None:
                await self.login()
            async with self._session.post(
                DATA_URL,
                json=payload,
                headers={"Authorization": self._token},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                status = resp.status
                body = await resp.json(content_type=None)
            if status == 401 or body.get("code") == 401:
                self._token = None
                if attempt == 0:
                    continue
                raise XexunAuthError(body.get("message") or "unauthorized")
            if body.get("code") != 200 or body.get("data") is None:
                raise XexunError(f"unexpected response: {body.get('code')} {body.get('message')}")
            return body["data"]
        raise XexunAuthError("unauthorized")

    async def get_status(self, imei: str, start: datetime, end: datetime) -> TrackerStatus:
        """Return the newest entry in [start, end] using at most three tiny requests."""
        total = (await self._page(imei, start, end, 1))["total"]
        if not total:
            return TrackerStatus(last_seen=None, battery=None)

        # Page N (pageSize 1) is the N-th record, so page `total` is the newest one.
        # It is usually a bare ACK; the data report with battery sits right before it.
        last_seen: datetime | None = None
        battery: int | None = None
        for page in (total, total - 1):
            if page < 1:
                break
            records = (await self._page(imei, start, end, page))["records"]
            if not records:
                break
            record = records[0]
            if last_seen is None:
                last_seen = datetime.fromtimestamp(record["uploadTime"] / 1000, tz=timezone.utc)
            battery = _field(record, "DEVICE.BATTERY")
            if battery is not None:
                break
        return TrackerStatus(last_seen=last_seen, battery=battery)


def _field(record: dict[str, Any], suffix: str) -> int | None:
    for block in record.get("bodyVoList") or []:
        for field in block.get("data") or []:
            if str(field.get("fieldName", "")).endswith(suffix):
                try:
                    return int(field.get("fieldDescribe"))
                except (TypeError, ValueError):
                    return None
    return None
