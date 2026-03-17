# Smart Building Automation - Sales4Italy

> Monorepo for Home Assistant + ESPHome configuration for the S4IT warehouse/office facility

## Vision

Centralized, git-managed smart building automation stack for the Sales4Italy warehouse and office in Cassano Magnago. Enables reproducible climate control, energy management, and workplace automation with full change history and rollback capability. Manages both Home Assistant (automations, dashboards, integrations) and ESPHome (custom ESP device firmware) from a single repository.

## Problem Statement

- Climate control across multiple office zones (Meeting Room, Customer Service, Open Space) requires complex seasonal scheduling with temperature-based overrides
- Manual management of HVAC, kitchen appliances, and EV charging wastes time and energy
- Configuration changes are hard to track without version control
- No disaster recovery for HA config without git backup
- ESP devices need centralized firmware management alongside HA config

## Target Users

- Dagmar (primary admin) — manages automations, integrations, and deployments
- Office staff — benefit from automated climate, lighting, and appliance control

## Key Systems

- **Climate Control**: Versatile Thermostat + Shelly 0-10V PM fancoils + UP Sense sensors for zone-based heating/cooling
- **Climate Presets**: Blueprint-based workday-aware Comfort/Eco/Frost scheduling per zone
- **EV Charging**: Wallbox auto-unlock on geofence arrival
- **Kitchen Appliances**: Scheduled on/off for workdays
- **ESP Devices**: Custom firmware for ESP-based sensors and controllers via ESPHome
- **Weather Integration**: Outdoor temperature-based HVAC decisions

## Infrastructure

- **Platform**: Home Assistant + ESPHome + Matter Server (Docker on Synology NAS)
- **Network**: UniFi UDM Pro managed network (10.0.10.x)
- **Proxy**: Synology Reverse Proxy → hacm1.sales4.it
- **Devices**: Shelly Pro 4PM, Shelly Pro 0-10V PM, UP Sense sensors, Wallbox, Tado, ESP devices
- **Integrations**: Workday sensor, Weather forecast, Zone tracking, ESPHome

## Success Criteria

- [x] All office zones have automated climate control (heating + cooling via seasonal toggle)
- [x] Configuration is fully version-controlled with meaningful commits
- [ ] Changes can be tested before deployment
- [x] Rollback is possible for any configuration change
- [ ] Energy usage is optimized through smart scheduling
