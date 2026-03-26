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
| Shelly Pro 0-10V PM | HTTP/MQTT | New fancoil speed control (0-10V stepless output mapped as light brightness) |
| ESP32 Athom 4CH Relay Board | ESPHome (WiFi) | Old fancoil control: 3-speed relay (Low/Med/High) + valve, 10 units deployed |
| UP Sense | — | Temperature sensors per zone |
| Wallbox | HA Integration | EV charger lock/unlock |
| Tado | HA Integration | Climate preset modes |
| UniFi | HA Integration | Network/presence detection |

## ESPHome Device Fleet

| Device | IP | Zone | Board | Firmware Source |
|--------|----|------|-------|----------------|
| fancoil-01 to -02 | 10.0.30.41-42 | OpenSpace | ESP32 Athom 4CH | GitHub: daggy72/esphome-fancoil |
| fancoil-03 | 10.0.30.43 | Entrance | ESP32 Athom 4CH | GitHub: daggy72/esphome-fancoil |
| fancoil-04 | 10.0.30.44 | Reception | ESP32 Athom 4CH | GitHub: daggy72/esphome-fancoil |
| fancoil-05 to -06 | 10.0.30.45-46 | MeetingRoom | ESP32 Athom 4CH | GitHub: daggy72/esphome-fancoil |
| fancoil-07 to -08 | 10.0.30.47-48 | CustomerService | ESP32 Athom 4CH | GitHub: daggy72/esphome-fancoil |
| fancoil-09 to -10 | 10.0.30.49-50 | Tania | ESP32 Athom 4CH | GitHub: daggy72/esphome-fancoil |

## Infrastructure

- **Deployment**: Synology NAS (Docker Compose, `network_mode: host`)
- **Reverse Proxy**: hacm1.sales4.it:443 → localhost:8123
- **SSL**: Synology system certificates mounted read-only
- **Network (LAN)**: UniFi UDM Pro (10.0.10.x subnet)
- **Network (IoT)**: NoT VLAN (10.0.30.0/24) — no internet, ESPHome devices only
- **DNS**: UDM Pro local DNS for internal access
- **Backup**: `/volume1/backup/homeassistant` mounted in container

## Development Tools

- **Editor**: VS Code / Cursor with YAML extension
- **Validation**: HA config check (`ha core check`)
- **Version Control**: Git + GitHub (daggy72/homeassistant-config-s4it)
