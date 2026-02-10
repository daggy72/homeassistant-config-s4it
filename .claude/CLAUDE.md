# CLAUDE.md

> Project-specific instructions for Home Assistant Config - S4IT
> Created: 2026-02-10

## Project Overview

Version-controlled Home Assistant configuration for the Sales4Italy warehouse/office in Cassano Magnago. Manages climate control, appliance scheduling, EV charging, and workplace automation.

## Global Configuration

This project extends:
- `@~/.claude/CLAUDE.md` (global Claude Code config)
- `@~/DevProjects/CLAUDE.md` (workspace config)

## Archon Integration

**Project ID**: `35b3bbdc-7f75-4fd3-b58c-a310c544ab08`

### Before Starting Work
```bash
# 1. Get project context
find_projects(project_id="35b3bbdc-7f75-4fd3-b58c-a310c544ab08")

# 2. Search knowledge base for HA patterns
rag_search_knowledge_base(query="home assistant automation", match_count=5)
```

## Project Structure

```
homeassistant-config-s4it/
├── agent-os/
│   ├── product/
│   │   ├── mission.md         # Project vision and goals
│   │   ├── tech-stack.md      # Technologies and hardware
│   │   ├── roadmap.md         # Development phases
│   │   └── decisions.md       # Architecture decisions
│   └── specs/
├── .claude/
│   └── CLAUDE.md              # This file
├── blueprints/                # HA blueprint templates
├── configuration.yaml         # Main HA config
├── automations.yaml           # All automations
├── scripts.yaml               # HA scripts
├── scenes.yaml                # HA scenes
└── .gitignore
```

## Tech Stack

- **Platform**: Home Assistant (Docker on Synology NAS)
- **Config**: YAML
- **Hardware**: Shelly Pro 4PM, UP Sense sensors, Wallbox, Tado
- **Network**: UniFi UDM Pro (10.0.10.x)
- **Proxy**: hacm1.sales4.it:443 → localhost:8123

## Office Zones

| Zone | Climate Entity | Shelly Device | Temp Sensor |
|------|---------------|---------------|-------------|
| MT (Meeting Room) | `climate.mt` | `shellypro4pm_ece334ea3fc4` | `sensor.up_sense_temperature_2` |
| Customer Service | `climate.customer_service` | `shellypro4pm_ece334eaf568` | `sensor.cc_up_sense_temperature` |
| Open Space | `climate.openspace_meetingroom` | `shellypro4pm_ece334ea3fc4` | `sensor.up_sense_temperature_3` |
| Meeting (lunch) | `climate.meeting` | — | — |

## Current Automations

| Automation | Schedule | Description |
|------------|----------|-------------|
| Kitchen Appliances | 8:00 on / 19:00 off (Mon-Sat) | Smart plugs for kitchen devices |
| Chiller & Fancoils | 8:00 on / 19:00 off (Mon-Fri) | Summer cooling when outdoor temp > 22°C |
| Auto Unlock Wallbox | On arrival (geofence) | Unlock EV charger when Dagmar arrives |
| Climate MT Winter | 7-8:00 on / 19:00 off | Heating with 22.5-24.5°C band |
| Climate CS Winter | 7-8:00 on / 18:00 off | Same pattern for Customer Service |
| Climate OpenSpace Winter | 7-8:00 on / 18:00 off | Same pattern for Open Space |
| Climate Workday Presets | Multiple times | Home/Sleep/Away/Comfort modes per zone |

## Important Notes

- **secrets.yaml** is NEVER committed (contains API keys, passwords)
- **custom_components/** managed via HACS, excluded from git
- **.storage/** contains runtime state, excluded from git
- **Testing**: Always run HA config check before deploying changes
- **Deployment**: User manually pulls changes on Synology NAS — Claude Code has NO SSH access

## Working with HA YAML

- Automations are defined in `automations.yaml` (HA UI also writes to this file)
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
