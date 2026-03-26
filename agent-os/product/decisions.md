# Architecture Decision Records

> Key decisions for Smart Building Domotics - S4IT

---

## DEC-001: Git-managed HA Configuration

**Date**: 2026-02-10
**Status**: Decided

### Context
Home Assistant configuration needs version control for change tracking, rollback capability, and disaster recovery.

### Decision
Store HA configuration YAML files in a GitHub repository. Exclude secrets, database, runtime files, and custom_components via .gitignore.

### Rationale
- Full change history for all automations and config
- Easy rollback if a change breaks something
- Backup independent of NAS snapshots
- Enables code review before deploying changes

### Consequences
- Must remember to commit after HA UI changes
- secrets.yaml must never be committed
- Custom components managed separately (HACS)

---

## DEC-002: Zone-based Climate Control with Shelly Relays

**Date**: 2026-02-10
**Status**: Decided

### Context
The office has multiple climate zones (MT, Customer Service, Open Space, Meeting Room) that need independent temperature control.

### Decision
Use Shelly Pro 4PM relays to control HVAC per zone, with UP Sense temperature sensors for feedback and weather forecast for outdoor temp decisions.

### Rationale
- Shelly devices are reliable, local-control capable, and HA-native
- Per-zone control allows different schedules and thresholds
- Weather-based decisions prevent unnecessary heating/cooling

### Consequences
- Each zone needs its own automation (some duplication)
- Temperature thresholds may need seasonal tuning

---

## DEC-003: Versatile Thermostat with Blueprint-based Scheduling

**Date**: 2026-03
**Status**: Decided

### Context
Managing per-zone climate automations individually led to duplication and was hard to maintain. Fancoils require 0-10V control which HA doesn't natively support through climate entities.

### Decision
Use Versatile Thermostat (HACS) in valve mode, with template number entities that map valve percentage to Shelly Pro 0-10V PM brightness. Schedule presets via a reusable custom blueprint (`office_climate_schedule.yaml`).

### Rationale
- VT's valve mode outputs 0-100% which maps cleanly to Shelly 0-10V via light brightness
- Blueprint pattern: define schedule logic once, instantiate per zone with different parameters
- Workday sensor integration handles weekends + public holidays automatically
- Pre-heat option avoids cold-start mornings

### Consequences
- Fancoil entities appear as "light" devices in HA (brightness = fan speed)
- Template numbers add a layer of indirection between VT and Shelly
- Blueprint changes propagate to all zones (feature, not bug)

---

## DEC-004: Host Network Mode for HA and Matter

**Date**: 2026-02
**Status**: Decided

### Context
Home Assistant and Matter Server need access to local network for device discovery (mDNS, Thread, BLE).

### Decision
Run both containers with `network_mode: host` and `privileged: true`.

### Rationale
- mDNS/SSDP discovery requires host networking
- Matter protocol needs direct network access for commissioning
- D-Bus access required for Bluetooth/Thread

### Consequences
- Containers share host network stack (port conflicts possible)
- Privileged mode reduces container isolation
- Security trade-off accepted for device compatibility

---

## DEC-005: Dual Fancoil Control Architecture

**Date**: 2026-03
**Status**: Decided

### Context
The building has two generations of fancoil hardware:
- **New fancoils**: Stepless variable-speed motors controlled via 0-10V analog signal
- **Old fancoils**: 3-speed motors (Low/Medium/High) with manual speed selector switches and on/off valve

### Decision
Maintain two parallel control paths, both driven by Versatile Thermostat:
1. **New fancoils**: VT valve % → template number entity → Shelly Pro 0-10V PM (light brightness) → 0-10V analog signal
2. **Old fancoils**: VT on_percent → HA automation → ESP32 Athom 4CH relay board → 3-speed relay interlocking + valve relay

### Rationale
- Different hardware requires different control methods — no single approach fits both
- Old fancoils cannot accept analog 0-10V; they need discrete relay switching
- ESP32 Athom 4CH boards are cost-effective and provide WiFi control, OTA updates, and physical button fallback
- Break-before-make relay interlocking in ESPHome firmware protects motors from damage
- Cascaded 6-speed mapping (for dual-room zones) maximizes granularity from 3-speed hardware

### Consequences
- Two sets of entities and automations to maintain (template numbers for new, fan entities for old)
- ESPHome firmware managed in separate GitHub repo (`daggy72/esphome-fancoil`)
- ESP devices require NoT VLAN (10.0.30.0/24) network infrastructure

---

## DEC-006: ESPHome Remote Package Management

**Date**: 2026-03
**Status**: Decided

### Context
10 ESP32 fancoil devices share identical firmware logic but have device-specific names and IPs. Maintaining copies of the base config in each device file would be error-prone.

### Decision
Host the shared fancoil controller firmware (`fancoil-base.yaml`) in a dedicated GitHub repository (`daggy72/esphome-fancoil`). Each device YAML file uses ESPHome's `packages` feature to fetch the base config remotely with daily refresh.

### Rationale
- Single source of truth for controller logic (relay interlocking, fan template, sensors)
- Firmware updates propagate to all devices on next compile
- Device files stay minimal: just name, IP, zone, and package reference
- GitHub provides version history for firmware changes

### Consequences
- ESPHome needs internet access to fetch packages on first compile (cached after)
- Breaking changes in base package affect all 10 devices simultaneously
- Must test firmware changes before pushing to main branch
