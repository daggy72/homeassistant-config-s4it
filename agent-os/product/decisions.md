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
