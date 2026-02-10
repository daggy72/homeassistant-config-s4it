# Home Assistant Config - Sales4Italy

> Version-controlled Home Assistant configuration for the S4IT warehouse/office facility

## Vision

Centralized, git-managed smart building configuration for the Sales4Italy warehouse and office in Cassano Magnago. Enables reproducible climate control, energy management, and workplace automation with full change history and rollback capability.

## Problem Statement

- Climate control across multiple office zones (Meeting Room, Customer Service, Open Space) requires complex seasonal scheduling with temperature-based overrides
- Manual management of HVAC, kitchen appliances, and EV charging wastes time and energy
- Configuration changes are hard to track without version control
- No disaster recovery for HA config without git backup

## Target Users

- Dagmar (primary admin) — manages automations, integrations, and deployments
- Office staff — benefit from automated climate, lighting, and appliance control

## Key Systems

- **Climate Control**: Shelly Pro 4PM relays + temperature sensors (UP Sense) for zone-based heating/cooling
- **Climate Presets**: Tado/climate entities with Home/Sleep/Away/Comfort preset modes
- **EV Charging**: Wallbox auto-unlock on geofence arrival
- **Kitchen Appliances**: Scheduled on/off for workdays
- **Weather Integration**: Outdoor temperature-based HVAC decisions

## Infrastructure

- **Platform**: Home Assistant (Docker container on Synology NAS)
- **Network**: UniFi UDM Pro managed network (10.0.10.x)
- **Proxy**: Synology Reverse Proxy → hacm1.sales4.it
- **Devices**: Shelly Pro 4PM, UP Sense sensors, Wallbox, Tado thermostats
- **Integrations**: Workday sensor, Weather forecast, Zone tracking

## Success Criteria

- [ ] All office zones have automated climate control (winter + summer)
- [ ] Configuration is fully version-controlled with meaningful commits
- [ ] Changes can be tested before deployment
- [ ] Rollback is possible for any configuration change
- [ ] Energy usage is optimized through smart scheduling
