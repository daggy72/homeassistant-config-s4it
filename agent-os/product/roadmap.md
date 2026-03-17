# Development Roadmap

> Phased approach for Home Assistant Config - S4IT

## Phase 1: Foundation (Complete)

**Goal**: Version-controlled baseline of existing configuration

**Deliverables**:
- [x] Initial config committed to GitHub
- [x] Climate automations for winter (MT, CS, OpenSpace zones)
- [x] Kitchen appliance scheduling (Mon-Sat 8:00-19:00)
- [x] Wallbox auto-unlock on arrival (geofence)
- [x] Climate workday preset modes
- [x] AgentOS + CLAUDE.md setup
- [x] README with documentation

**Status**: Complete

---

## Phase 2: Fancoil Climate System (Complete)

**Goal**: Unified climate control via Versatile Thermostat + fancoils

**Deliverables**:
- [x] Versatile Thermostat integration (valve mode)
- [x] Template number entities mapping VT valve % → Shelly 0-10V brightness
- [x] Custom blueprint: `office_climate_schedule.yaml` (workday-aware presets)
- [x] 5 zone-specific automations using blueprint (Office, CS, Meeting Room, Open Space, Mensa)
- [x] Seasonal mode toggle (`input_boolean.heating_season` → heat/cool switch)
- [x] Climate Control YAML dashboard with presets + fancoil status
- [x] Pre-heat option in blueprint for early morning warm-up

**Status**: Complete

---

## Phase 3: Energy Monitoring

**Goal**: Track and optimize energy consumption

**Deliverables**:
- [ ] Shelly energy monitoring dashboards
- [ ] Weekly/monthly energy reports
- [ ] Peak usage alerts
- [ ] Wallbox charging session tracking

---

## Phase 4: Presence & Occupancy

**Goal**: Smarter automation based on actual occupancy

**Deliverables**:
- [ ] Room-level occupancy detection
- [ ] Auto-adjust climate based on occupancy
- [ ] Last-person-out shutdown automation
- [ ] Holiday/vacation mode
