# Smart Building Automation - Sales4Italy

> Monorepo for Home Assistant + ESPHome configuration for the S4IT warehouse/office facility

## Vision

Centralized, git-managed domotics system for the Sales4Italy warehouse and office in Cassano Magnago. Starting from climate control, rapidly expanding to cover sunscreens (tende), lighting, and additional smart devices. Enables reproducible automation, energy management, and workplace control with full change history and rollback capability. Manages both Home Assistant (automations, dashboards, integrations) and ESPHome (custom ESP device firmware) from a single repository.

## Problem Statement

- Climate control across multiple office zones requires complex seasonal scheduling with temperature-based overrides
- Two generations of fancoil hardware need different control strategies (0-10V analog vs 3-speed relay)
- Manual management of HVAC, sunscreens, lighting, kitchen appliances, and EV charging wastes time and energy
- Configuration changes are hard to track without version control
- No disaster recovery for HA config without git backup
- ESP devices need centralized firmware management alongside HA config
- System is expanding rapidly — new device types (sunscreens, lights) need a scalable architecture

## Target Users

- Dagmar (primary admin) — manages automations, integrations, and deployments
- Office staff — benefit from automated climate, lighting, and appliance control

## Key Systems

- **Climate Control (New Fancoils)**: Versatile Thermostat (valve mode) → template number → Shelly Pro 0-10V PM for stepless fan speed control
- **Climate Control (Old Fancoils)**: Versatile Thermostat → automation → ESP32 Athom 4CH relay boards for 3-speed (Low/Med/High) + valve control
- **Climate Presets**: Blueprint-based workday-aware Comfort/Eco/Frost scheduling per zone
- **Sunscreens (Tende)**: Motorized sunscreen control (in progress)
- **Lighting**: Smart lighting control (in progress)
- **EV Charging**: Wallbox auto-unlock on geofence arrival
- **Kitchen Appliances**: Scheduled on/off for workdays
- **ESP Devices**: Custom firmware for ESP-based sensors and controllers via ESPHome (10 fancoil units deployed)
- **Weather Integration**: Outdoor temperature-based HVAC decisions

## Infrastructure

- **Platform**: Home Assistant + ESPHome + Matter Server (Docker on Synology NAS)
- **Network**: UniFi UDM Pro managed network (10.0.10.x)
- **Proxy**: Synology Reverse Proxy → hacm1.sales4.it
- **Devices**: Shelly Pro 4PM, Shelly Pro 0-10V PM, UP Sense sensors, Wallbox, Tado, ESP32 Athom 4CH relay boards
- **Network (IoT)**: NoT VLAN 10.0.30.0/24 (no internet) for ESPHome devices, fixed IPs 10.0.30.41-50
- **Integrations**: Workday sensor, Weather forecast, Zone tracking, ESPHome

## Success Criteria

- [x] All office zones have automated climate control (heating + cooling via seasonal toggle)
- [x] Configuration is fully version-controlled with meaningful commits
- [x] ESPHome fancoil fleet deployed (10 devices, dual control architecture)
- [ ] Changes can be tested before deployment
- [x] Rollback is possible for any configuration change
- [ ] Energy usage is optimized through smart scheduling
- [ ] Sunscreen and lighting automation operational
- [ ] Full domotics coverage for the facility
