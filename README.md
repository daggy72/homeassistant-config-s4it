# Home Assistant Config - S4IT

Version-controlled Home Assistant configuration for the Sales4Italy warehouse/office facility in Cassano Magnago.

## What's Managed

- **Climate Control**: Zone-based heating/cooling for MT, Customer Service, Open Space, and Meeting Room
- **Kitchen Appliances**: Scheduled on/off via smart plugs
- **EV Charging**: Wallbox auto-unlock on geofence arrival
- **Climate Presets**: Workday-aware Home/Sleep/Away/Comfort modes

## Hardware

| Device | Purpose |
|--------|---------|
| Shelly Pro 4PM | Relay control for HVAC zones |
| UP Sense | Temperature sensors per zone |
| Wallbox | EV charger with lock/unlock |
| Tado | Climate preset mode control |

## Setup

This configuration runs on Home Assistant (Docker) on a Synology NAS.

```bash
# Clone
git clone git@github.com:daggy72/homeassistant-config-s4it.git

# Copy to HA config directory (on NAS)
# /volume1/docker/homeassistant/config/
```

### What's NOT in this repo

- `secrets.yaml` — API keys, passwords (create manually from secrets.yaml.example)
- `custom_components/` — managed via HACS
- `.storage/` — HA runtime state
- `home-assistant_v2.db` — HA database

## Documentation

- [Mission & Vision](agent-os/product/mission.md)
- [Tech Stack](agent-os/product/tech-stack.md)
- [Roadmap](agent-os/product/roadmap.md)
- [Architecture Decisions](agent-os/product/decisions.md)
