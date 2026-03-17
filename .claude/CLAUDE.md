# CLAUDE.md

> Project-specific instructions for Smart Building Automation - S4IT
> Created: 2026-02-10

## Project Overview

Version-controlled smart building automation stack for the Sales4Italy warehouse/office in Cassano Magnago. Monorepo managing Home Assistant, ESPHome, and supporting services.

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
- **Hardware**: Shelly Pro 4PM, Shelly Pro 0-10V PM, UP Sense sensors, Wallbox, Tado, ESP devices
- **Network**: UniFi UDM Pro (10.0.10.x), host networking for Docker
- **Proxy**: hacm1.sales4.it:443 → localhost:8123

## Home Assistant

### Climate Architecture

**Approach**: Versatile Thermostat (valve mode) → template number entity → Shelly Pro 0-10V PM (light brightness)

The VT outputs a 0-100% valve position. Template numbers in `homeassistant/config/templates.yaml` map this to Shelly 0-10V brightness, which drives the fancoil speed.

**Seasonal toggle**: `input_boolean.heating_season` switches VT between heat/cool HVAC modes.

#### Fancoil Entities (templates.yaml)

| Template Number | Shelly 0-10V Entity |
|-----------------|---------------------|
| Fancoil Mensa 1 | `light.shellypro0110pm_8813bfe0fc18` |
| Fancoil Mensa 2 | `light.shellypro0110pm_8813bfd9525c` |
| Fancoil Projects 1 | `light.shellypro0110pm_8813bfe0e42c` |
| Fancoil Projects 2 | `light.shellypro0110pm_8813bfd95330` |

#### Climate Zones (Versatile Thermostat entities)

| Zone | Climate Entity | Blueprint Automation |
|------|---------------|---------------------|
| Office (MT + Projects) | `climate.mt_climate`, `climate.projects_1` | Office Climate Schedule |
| Customer Service | `climate.cs_climate` | CS Climate Schedule |
| Meeting Room | `climate.meeting_room_climate` | Meeting Room Climate Schedule |
| Open Space | `climate.open_space_climate` | Open Space Climate Schedule |
| Mensa | `climate.mensa_climate` | Mensa Climate Schedule |

### Automations

#### Standalone Automations (automations.yaml)

| Automation | Trigger | Description |
|------------|---------|-------------|
| Kitchen Appliances | Time: 8:00 on / 19:00 off (Mon-Sat) | Smart plugs for kitchen devices |
| Auto Unlock Wallbox | Zone: enter home (geofence) | Unlock EV charger when Dagmar arrives |
| Fancoil Seasonal Mode Toggle | State: `input_boolean.heating_season` | Switches VT between heat/cool mode |

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

### Working with ESPHome YAML

- One YAML file per device in `esphome/config/`
- Shared configuration in `esphome/config/common/` (wifi, base settings)
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
