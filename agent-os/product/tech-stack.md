# Tech Stack

> Technology choices for Smart Building Automation - S4IT

## Core Platform

| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| Platform | Home Assistant | Latest stable | Open-source home automation |
| Config Format | YAML | — | HA native configuration language |
| Runtime | Docker | — | Containers on Synology NAS |
| Version Control | Git | — | Change tracking and rollback |

## Services (Docker Compose)

| Service | Container | Image | Purpose |
|---------|-----------|-------|---------|
| Home Assistant | HA_homeassistant | ghcr.io/home-assistant/home-assistant:stable | Core automation platform |
| Matter Server | HA_matter-server | ghcr.io/home-assistant-libs/python-matter-server:stable | Matter/Thread device support |
| ESPHome | HA_esphome | ghcr.io/esphome/esphome:stable | ESP device firmware management |

## Custom Components (HACS)

| Component | Purpose |
|-----------|---------|
| Versatile Thermostat | Advanced thermostat with valve mode — drives fancoil 0-10V via template numbers |
| Nector200 | Custom integration (debug logging enabled) |

## Hardware Integrations

| Device | Protocol | Purpose |
|--------|----------|---------|
| Shelly Pro 4PM | HTTP/MQTT | Relay control for HVAC zones, appliances |
| Shelly Pro 0-10V PM | HTTP/MQTT | Fancoil speed control (0-10V output mapped as light brightness) |
| UP Sense | — | Temperature sensors per zone |
| Wallbox | HA Integration | EV charger lock/unlock |
| Tado | HA Integration | Climate preset modes |
| UniFi | HA Integration | Network/presence detection |
| ESP devices | ESPHome (WiFi) | Custom sensors and controllers |

## Infrastructure

- **Deployment**: Synology NAS (Docker Compose, `network_mode: host`)
- **Reverse Proxy**: hacm1.sales4.it:443 → localhost:8123
- **SSL**: Synology system certificates mounted read-only
- **Network**: UniFi UDM Pro (10.0.10.x subnet)
- **DNS**: UDM Pro local DNS for internal access
- **Backup**: `/volume1/backup/homeassistant` mounted in container

## Development Tools

- **Editor**: VS Code / Cursor with YAML extension
- **Validation**: HA config check (`ha core check`)
- **Version Control**: Git + GitHub (daggy72/homeassistant-config-s4it)
