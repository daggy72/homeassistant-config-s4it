# Development Roadmap

> Phased approach for Smart Building Domotics - S4IT

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
- [x] Template number entities mapping VT valve % → Shelly 0-10V brightness (new stepless fancoils)
- [x] Custom blueprint: `office_climate_schedule.yaml` (workday-aware presets)
- [x] 5 zone-specific automations using blueprint (Office, CS, Meeting Room, Open Space, Mensa)
- [x] Seasonal mode toggle (`input_boolean.heating_season` → heat/cool switch)
- [x] Climate Control YAML dashboard with presets + fancoil status
- [x] Pre-heat option in blueprint for early morning warm-up

**Status**: Complete

---

## Phase 3: ESPHome Fancoil Fleet (Complete)

**Goal**: Replace manual controls on old 3-speed fancoils with ESP32-based automation

**Deliverables**:
- [x] 10 × ESP32 Athom 4CH relay boards configured (fancoil-01 through fancoil-10)
- [x] Centralized firmware via GitHub package (`daggy72/esphome-fancoil`)
- [x] Break-before-make relay interlocking (motor protection)
- [x] 3-speed (Low/Med/High) + valve relay control per unit
- [x] Cascaded 6-speed mapping for dual-room zones, 3-speed for single-room zones
- [x] VT on_percent → fan speed automation (`fancoil_speed_control`)
- [x] NoT VLAN (10.0.30.0/24) with fixed IPs, no internet
- [x] OTA update capability via ESPHome dashboard
- [x] Physical button controls (speed select + on/off + factory reset)

**Status**: Complete (2 online v1.1.0, 4 online needing reflash, 4 offline/unpowered)

---

## Ongoing: Domotics Expansion

**Goal**: Grow the system organically as new needs and devices arise

**Planned areas** (no fixed order — driven by opportunity and need):

### Energy Monitoring
- [ ] Shelly energy monitoring dashboards
- [ ] Weekly/monthly energy reports
- [ ] Peak usage alerts
- [ ] Wallbox charging session tracking

### Sunscreens (Tende)
- [ ] Motorized sunscreen integration
- [ ] Weather-based automation (wind, sun, rain)
- [ ] Schedule-based open/close

### Lighting
- [ ] Smart lighting control per zone
- [ ] Presence-based lighting automation
- [ ] Scene/mood presets

### Presence & Occupancy
- [ ] Room-level occupancy detection
- [ ] Auto-adjust climate based on occupancy
- [ ] Last-person-out shutdown automation
- [ ] Holiday/vacation mode

### Additional Smart Devices
- [ ] New device types as they are introduced to the facility
