# Smart Building Automation - S4IT

Version-controlled smart building automation stack for the Sales4Italy warehouse/office facility in Cassano Magnago.

## Services

| Service | Purpose | Config Path |
|---------|---------|-------------|
| Home Assistant | Core automation platform | `homeassistant/config/` |
| ESPHome | ESP device firmware management | `esphome/config/` |
| Matter Server | Matter/Thread device support | (no user config) |
| InfluxDB | Long-term climate telemetry storage | `influxdb/` |
| Grafana | Internal and WH1 customer telemetry dashboards | `grafana/` |

## What's Managed

- **Climate Control**: Zone-based heating/cooling via Versatile Thermostat + fancoils
- **Kitchen Appliances**: Scheduled on/off via smart plugs
- **EV Charging**: Wallbox auto-unlock on geofence arrival
- **Climate Presets**: Workday-aware Comfort/Eco/Frost modes per zone
- **Telemetry**: InfluxDB/Grafana logging for WH1, fancoils, chiller, and weather context
- **ESP Devices**: Custom firmware for ESP-based sensors and controllers

## Hardware

| Device | Purpose |
|--------|---------|
| Shelly Pro 4PM | Relay control for HVAC zones |
| Shelly Pro 0-10V PM | Fancoil speed control (0-10V) |
| UP Sense | Temperature sensors per zone |
| Wallbox | EV charger with lock/unlock |
| Tado | Climate preset mode control |
| ESP devices | Custom sensors and controllers via ESPHome |

## Setup

This stack runs on Docker (Synology NAS).

```bash
# Clone
git clone git@github.com:daggy72/homeassistant-config-s4it.git

# On production (Synology NAS):
# Set DOCKER_BASE if not using default /volume1/docker/homeassistant
docker compose up -d
```

### What's NOT in this repo

- `*/secrets.yaml` — API keys, passwords (create manually)
- `homeassistant/config/custom_components/` — managed via HACS
- `homeassistant/config/.storage/` — HA runtime state
- `homeassistant/data/`, `homeassistant/matter-data/`, `esphome/data/` — runtime data

## Monitoring

**No ad-hoc LLM polling loops.** Anomaly detection for this facility (chiller,
VT wedges, fan/valve faults, preset drift) runs as native HA template binary
sensors + state-change automations (`homeassistant/config/templates.yaml` /
`automations.yaml`, ids prefixed `watchdog_*`), not as a Claude/Codex cron
polling Home Assistant on an interval. See the DEV-DOMOTICA CLAUDE.md ground
truth: "Monitoring belongs in HA automations/template sensors, NOT in LLM
polling loops" — a prior 5-min LLM watchdog burned ~4.9M output tokens across
~4,400 MCP polls (usage-audit-2026-07, finding F1) and silently missed
coverage twice when the MCP server disconnected. State-change detection is
free, always-on, and has no external dependency to fail. One short daily LLM
review session (a "night-watch" pattern) is fine — a recurring interval poll
is not.

## Documentation

- [Mission & Vision](agent-os/product/mission.md)
- [Tech Stack](agent-os/product/tech-stack.md)
- [Roadmap](agent-os/product/roadmap.md)
- [Architecture Decisions](agent-os/product/decisions.md)
- [Climate Telemetry Stack](docs/climate/telemetry.md)
