# Smart Building Automation - S4IT

Version-controlled smart building automation stack for the Sales4Italy warehouse/office facility in Cassano Magnago.

## Services

| Service | Purpose | Config Path |
|---------|---------|-------------|
| Home Assistant | Core automation platform | `homeassistant/config/` |
| ESPHome | ESP device firmware management | `esphome/config/` |
| Matter Server | Matter/Thread device support | (no user config) |

## What's Managed

- **Climate Control**: Zone-based heating/cooling via Versatile Thermostat + fancoils
- **Kitchen Appliances**: Scheduled on/off via smart plugs
- **EV Charging**: Wallbox auto-unlock on geofence arrival
- **Climate Presets**: Workday-aware Comfort/Eco/Frost modes per zone
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

## Documentation

- [Mission & Vision](agent-os/product/mission.md)
- [Tech Stack](agent-os/product/tech-stack.md)
- [Roadmap](agent-os/product/roadmap.md)
- [Architecture Decisions](agent-os/product/decisions.md)
