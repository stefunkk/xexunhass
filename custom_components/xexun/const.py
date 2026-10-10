"""Constants for the Xexun Tracker integration."""

from datetime import timedelta

DOMAIN = "xexun"

API_BASE = "https://tracker.xexun.com/web-manager"
LOGIN_URL = f"{API_BASE}/auth/login"
DATA_URL = f"{API_BASE}/term4GTcp/getParsePage"

CONF_TRACKERS = "trackers"
CONF_THRESHOLD_HOURS = "threshold_hours"

DEFAULT_THRESHOLD_HOURS = 10
SCAN_INTERVAL = timedelta(hours=4)
# How far back to look for the newest entry. Must exceed the alert threshold.
LOOKBACK = timedelta(hours=48)
