# CLAUDE.md

> Project-specific instructions for Smart Building Automation - S4IT
> Created: 2026-02-10

## Project Overview

Version-controlled domotics system for the Sales4Italy warehouse/office in Cassano Magnago. Monorepo managing Home Assistant, ESPHome, and supporting services. Expanding from climate control to cover sunscreens (tende), lighting, and additional smart devices.

## Global Configuration

This project extends:
- `@~/.claude/CLAUDE.md` (global Claude Code config)
- `@~/DevProjects/CLAUDE.md` (workspace config)

## Project Structure

```
s4it-automation/
├── .claude/
│   └── CLAUDE.md                    # This file
├── agent-os/
│   ├── product/                     # Vision, tech stack, roadmap, decisions
│   └── standards/                   # Discovered patterns
├── homeassistant/
│   ├── config/                      # HA YAML configuration
│   │   ├── configuration.yaml       # Main config (includes, helpers, dashboards)
│   │   ├── automations.yaml         # All automations (standalone + blueprint)
│   │   ├── templates.yaml           # Fancoil template numbers (VT → Shelly 0-10V)
│   │   ├── blueprints/automation/custom/
│   │   │   └── office_climate_schedule.yaml
│   │   ├── dashboards/
│   │   │   └── climate.yaml
│   │   ├── scripts.yaml
│   │   ├── scenes.yaml
│   │   └── secrets.yaml             # NOT in git
│   ├── data/                        # HA runtime data (NOT in git)
│   └── matter-data/                 # Matter server data (NOT in git)
├── esphome/
│   ├── config/                      # ESPHome device configs
│   │   ├── common/                  # Shared includes (wifi, base)
│   │   │   └── base.yaml
│   │   ├── secrets.yaml             # NOT in git
│   │   └── *.yaml                   # One file per device
│   └── data/                        # ESPHome build cache (NOT in git)
├── docker-compose.yaml              # All services (HA, Matter, ESPHome)
├── .gitignore
└── README.md
```

## Services (Docker Compose)

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| Home Assistant | HA_homeassistant | 8123 | Core automation platform |
| Matter Server | HA_matter-server | 5580 | Matter/Thread device support |
| ESPHome | HA_esphome | 6052 | ESP device firmware management |

All services use `network_mode: host`. Paths are parameterized via `DOCKER_BASE` env var (defaults to `/volume1/docker/homeassistant`).

## Tech Stack

- **Platform**: Home Assistant + ESPHome + Matter Server (Docker on Synology NAS)
- **Config**: YAML
- **Custom Components**: Versatile Thermostat (valve mode), Nector200, HACS
- **Hardware**: Shelly Pro 4PM, Shelly Pro 0-10V PM, ESP32 Athom 4CH relay boards, UP Sense sensors, Wallbox, Tado
- **Network (LAN)**: UniFi UDM Pro (10.0.10.x), host networking for Docker
- **Network (IoT)**: NoT VLAN 10.0.30.0/24 (no internet) for ESPHome devices, fixed IPs 10.0.30.41-50
- **Proxy**: hacm1.sales4.it:443 → localhost:8123

## Home Assistant

### Climate Architecture

Two generations of fancoil hardware coexist, both driven by Versatile Thermostat:

**New fancoils (stepless)**: VT valve % → template number → Shelly Pro 0-10V PM (light brightness) → 0-10V analog signal. Template numbers in `homeassistant/config/templates.yaml` map valve position to Shelly brightness.

**Old fancoils (3-speed)**: VT on_percent → HA automation → ESP32 Athom 4CH relay board → 3-speed relay (Low/Med/High) + valve relay. The `Fancoil Speed Control` automation in `automations.yaml` handles cascaded 6-speed mapping for dual-room zones and 3-speed for single-room zones.

**Seasonal mode**: `input_select.climate_season` (winter/off/summer) switches all VTs between heat/cool/off and controls the chiller. Summer comfort temps are dynamic based on outdoor temperature (24-27°C offices, 25-28°C common).

#### New Fancoil Entities (templates.yaml — Shelly 0-10V)

| Template Number | Shelly 0-10V Entity | Shelly App Name | Notes |
|---|---|---|---|
| `number.fancoil_mensa_1` (display name "Fancoil Mensa") | `light.shellypro0110pm_8813bfe0fc18` | Fancoils-Mensa | Drives **both** Mensa ceiling fancoils wired in parallel |
| `number.fancoil_dagmar` | `light.shellypro0110pm_8813bfd9525c` | Fancoils-Dagmar | Drives **both** new fancoils in Dagmar's office wired in parallel (replaced old binary smart plug) |
| `number.fancoil_projects_1` | `light.shellypro0110pm_8813bfd95330` | — | One fancoil in the MT/Projects room |
| `number.fancoil_projects_2` | `light.shellypro0110pm_8813bfe0e42c` | — | Other fancoil in the MT/Projects room |

#### Old Fancoil Entities (ESPHome — ESP32 Athom 4CH relay)

| Fan Entity | Zone | Room Type |
|------------|------|-----------|
| `fan.fancoil_01_fancoil`, `fan.fancoil_02_fancoil` | OpenSpace | Dual (6-speed cascade) |
| `fan.fancoil_03_fancoil` | Entrance | Single (3-speed) |
| `fan.fancoil_04_fancoil` | Reception | Single (3-speed) |
| `fan.fancoil_05_fancoil`, `fan.fancoil_06_fancoil` | MeetingRoom | Dual (6-speed cascade) |
| `fan.fancoil_07_fancoil`, `fan.fancoil_08_fancoil` | CustomerService | Dual (6-speed cascade) |
| `fan.fancoil_09_fancoil`, `fan.fancoil_10_fancoil` | Tania | Dual (6-speed cascade) |

#### Climate Zones (Versatile Thermostat entities)

| Zone | Climate Entity | Blueprint Automation |
|------|---------------|---------------------|
| Office (MT + Projects) | `climate.projects_1`, `climate.projects_2` | Office Climate Schedule |
| Customer Service | `climate.fancoil_cs` | CS Climate Schedule |
| Meeting Room | `climate.fancoil_meeting` | Meeting Room Climate Schedule |
| Open Space | `climate.fancoil_openspace` | Open Space Climate Schedule |
| Mensa | `climate.climate_mensa` | Mensa Climate Schedule |
| Tania | `climate.fancoil_tania` | — |
| Reception | `climate.fancoil_reception` | — |
| Entrance | `climate.fancoil_entrance` | — |

### Automations

#### Standalone Automations (automations.yaml)

| Automation | Trigger | Description |
|------------|---------|-------------|
| Kitchen Appliances | Time: 8:00 on / 19:00 off (Mon-Sat) | Smart plugs for kitchen devices |
| Auto Unlock Wallbox | Zone: enter home (geofence) | Unlock EV charger when Dagmar arrives |
| Seasonal Climate Mode Switch | State: `input_select.climate_season` | Switches all VTs heat/cool/off + chiller control |
| Summer Dynamic Temp Adjust | Time: every 30min (summer only) | Adjusts cooling targets based on outdoor temp |
| Fancoil Speed Control | State: VT `on_percent` attribute | Maps VT demand to ESP32 fan speed (old fancoils) |

#### Blueprint-based Automations (office_climate_schedule.yaml)

All use `blueprints/automation/custom/office_climate_schedule.yaml`. Workday-aware with comfort/eco/frost presets.

| Zone | Comfort | Eco | Frost | Pre-heat |
|------|---------|-----|-------|----------|
| Office | 08:00 | 17:00 | 19:00 | Yes (07:30) |
| CS | 08:00 | 16:00 | 18:00 | Yes (07:30) |
| Meeting Room | 12:00 | 08:00 | 16:00 | No |
| Open Space | 08:00 | 16:00 | 18:00 | Yes (07:30) |
| Mensa | 09:00 | 15:00 | 18:00 | No |

## ESPHome

### Device Fleet

10 ESP32 Athom 4CH relay boards controlling old 3-speed fancoils:

| Devices | IPs | Zone |
|---------|-----|------|
| fancoil-01, -02 | 10.0.30.41-42 | OpenSpace |
| fancoil-03 | 10.0.30.43 | Entrance |
| fancoil-04 | 10.0.30.44 | Reception |
| fancoil-05, -06 | 10.0.30.45-46 | MeetingRoom |
| fancoil-07, -08 | 10.0.30.47-48 | CustomerService |
| fancoil-09, -10 | 10.0.30.49-50 | Tania |

All devices on NoT VLAN (10.0.30.0/24, no internet). Firmware sourced from GitHub package `daggy72/esphome-fancoil` (daily refresh).

### Working with ESPHome YAML

- One YAML file per device in `esphome/config/`
- Shared firmware via remote GitHub package (`packages` key) — device files are minimal (name, IP, zone)
- Local shared config in `esphome/config/common/` (wifi, base settings)
- Use `!include` and `!secret` for shared config and credentials
- ESPHome dashboard at port 6052 for compiling and flashing
- Secrets in `esphome/config/secrets.yaml` (NOT in git)

## Important Notes

- **secrets.yaml** files are NEVER committed (both HA and ESPHome)
- **custom_components/** managed via HACS, excluded from git
- **Testing**: Always run HA config check before deploying changes
- **Deployment**: User manually pulls changes on Synology NAS — Claude Code has NO SSH access

## Working with HA YAML

- Automations are defined in `homeassistant/config/automations.yaml` (HA UI also writes to this file)
- After manual YAML edits, HA needs reload: Settings → Automations → Reload
- Use `!include` directives to split large configs into separate files
- Device IDs are hardware-specific — never change them, only reference them
- Entity IDs follow HA naming: `domain.friendly_name_slug`

## DevProjects Portal Integration

```bash
# Report bugs or request features
curl -X POST https://devprojects.sales4.it/api/board/homeassistant/bugs \
  -H "Content-Type: application/json" \
  -d '{"title": "Bug title", "description": "Details", "reporter_name": "Name"}'
```
