# Tech Stack

> Technology choices for Home Assistant Config - S4IT

## Core Platform

| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| Platform | Home Assistant | Latest stable | Open-source home automation |
| Config Format | YAML | — | HA native configuration language |
| Runtime | Docker | — | Container on Synology NAS |
| Version Control | Git | — | Change tracking and rollback |

## Hardware Integrations

| Device | Protocol | Purpose |
|--------|----------|---------|
| Shelly Pro 4PM | HTTP/MQTT | Relay control for HVAC, appliances |
| UP Sense | — | Temperature sensors per zone |
| Wallbox | HA Integration | EV charger lock/unlock |
| Tado | HA Integration | Climate preset modes |
| UniFi | HA Integration | Network/presence detection |

## Infrastructure

- **Deployment**: Synology NAS (Docker container)
- **Reverse Proxy**: hacm1.sales4.it:443 → localhost:8123
- **Network**: UniFi UDM Pro (10.0.10.x subnet)
- **DNS**: UDM Pro local DNS for internal access

## Development Tools

- **Editor**: VS Code / Cursor with YAML extension
- **Validation**: HA config check (`ha core check`)
- **Version Control**: Git + GitHub (daggy72/homeassistant-config-s4it)
