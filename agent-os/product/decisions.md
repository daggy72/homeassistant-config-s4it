# Architecture Decision Records

> Key decisions for Home Assistant Config - S4IT

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
