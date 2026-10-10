<p align="center">
  <img src="custom_components/xexun/brand/icon.png" alt="Xexun Tracker" width="128">
</p>

# Xexun Tracker for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![GitHub Release](https://img.shields.io/github/v/release/stefunkk/xexunhass)](https://github.com/stefunkk/xexunhass/releases)
[![Validate](https://github.com/stefunkk/xexunhass/actions/workflows/validate.yml/badge.svg)](https://github.com/stefunkk/xexunhass/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Custom integration for GPS trackers managed at [tracker.xexun.com](https://tracker.xexun.com), such as Xexun pet and dog trackers.

It tells you **when a tracker goes silent** and **how much battery it has left**, so you can get a notification before the dog's collar dies in the woods.

## Features

- Set up from the UI (config flow), with no YAML
- Several trackers on one account
- A **Last seen** timestamp, a **Battery** level and a **No data** problem sensor for each tracker
- Configurable "no data" threshold (default **10 h**)
- Automatic re-login when the session token expires, and a re-authentication prompt if the password changes
- Light on the Xexun cloud: 2–3 small requests per tracker every 15 minutes

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=stefunkk&repository=xexunhass&category=integration)

Or manually in HACS:

1. Open **HACS** → **⋮** (top right) → **Custom repositories**.
2. Add `https://github.com/stefunkk/xexunhass` with type **Integration**.
3. Search for **Xexun Tracker** and click **Download**.
4. Restart Home Assistant.

### Manual

1. Download `xexun.zip` from the [latest release](https://github.com/stefunkk/xexunhass/releases/latest).
2. Unpack it into `<config>/custom_components/xexun/`. The folder must contain `manifest.json` directly.
3. Restart Home Assistant.

<details>
<summary>Resulting folder layout</summary>

```
config/
└── custom_components/
    └── xexun/
        ├── __init__.py
        ├── manifest.json
        └── ...
```
</details>

## Configuration

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=xexun)

Or go to **Settings** → **Devices & services** → **Add integration** → **Xexun Tracker** and fill in:

| Field | Description |
|---|---|
| Username | Your tracker.xexun.com login |
| Password | Your tracker.xexun.com password |
| Trackers | One tracker per line, as `Name: IMEI` |

```
Rex: 869469000000001
Luna: 869469000000002
```

The IMEI is shown in the device list at tracker.xexun.com and on the device label.
The name becomes the device name in Home Assistant.

**Options** (*Configure* on the integration): the alert threshold in hours (1–47, default 10).
**Reconfigure** (*⋮* → *Reconfigure*): change the login or the list of trackers.

## Entities

Each tracker gets its own device with these entities:

| Entity | Type | Description |
|---|---|---|
| Last seen | `sensor` (timestamp) | Time of the newest entry the tracker sent |
| Battery | `sensor` (%) | Battery level from the newest data report |
| No data | `binary_sensor` (problem) | `on` when there has been no entry for longer than the threshold |

The entity IDs depend on the device name, for example `sensor.rex_last_seen`, `sensor.rex_battery` and `binary_sensor.rex_no_data`.

## Notifications

Example automation that notifies you when a tracker has been silent for longer than the threshold, or when its battery drops to 20 % or less. A ready-to-use version is in [`examples/automation.yaml`](examples/automation.yaml).

```yaml
alias: Tracker alerts
triggers:
  - trigger: state
    id: no_data
    entity_id: binary_sensor.rex_no_data
    from: "off"
    to: "on"
  - trigger: numeric_state
    id: battery
    entity_id: sensor.rex_battery
    below: 21
actions:
  - action: notify.notify
    data:
      title: >-
        {{ 'Tracker is silent' if trigger.id == 'no_data' else 'Tracker battery low' }}
      message: >-
        {% set name = device_attr(device_id(trigger.entity_id), 'name') %}
        {% if trigger.id == 'no_data' %}
          {{ name }}: no data for more than {{ state_attr(trigger.entity_id, 'threshold_hours') | int }} h
        {% else %}
          {{ name }}: battery {{ trigger.to_state.state }} %
        {% endif %}
mode: queued
```

Replace `notify.notify` with your own notify service, for example `notify.mobile_app_your_phone`.

## How it works

The Xexun web API (`POST /web-manager/term4GTcp/getParsePage`) returns entries **oldest first** and ignores sort parameters.
With `pageSize: 1` the page number equals the entry number, so for each tracker the integration:

1. reads `total` (the number of entries in the last 48 h) from page 1,
2. fetches page `total`, the newest entry, which gives *Last seen*,
3. fetches page `total - 1` if needed, because the newest entry is usually a bare ACK and the data report with the battery level comes right before it.

## Troubleshooting

Turn on debug logging in `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.xexun: debug
```

Or use **Settings** → **Devices & services** → **Xexun Tracker** → **⋮** → **Enable debug logging**.

| Problem | Cause |
|---|---|
| Entities are `unavailable` | The Xexun cloud is unreachable. While this lasts, no "no data" alert is raised. |
| "Invalid username or password" | Check your login at tracker.xexun.com. |
| *Last seen* is `unknown` | No entries in the last 48 h. The sensor keeps the last known value while Home Assistant keeps running. |

## Disclaimer

This is an unofficial integration. It is not affiliated with or endorsed by Xexun.
It uses the same web API as the tracker.xexun.com website, which may change without notice.

## License

[MIT](LICENSE)
