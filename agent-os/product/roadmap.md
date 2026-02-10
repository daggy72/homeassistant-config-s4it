# Development Roadmap

> Phased approach for Home Assistant Config - S4IT

## Phase 1: Foundation (Current)

**Goal**: Version-controlled baseline of existing configuration

**Deliverables**:
- [x] Initial config committed to GitHub
- [x] Climate automations for winter (MT, CS, OpenSpace zones)
- [x] Kitchen appliance scheduling
- [x] Wallbox auto-unlock on arrival
- [x] Climate workday preset modes
- [ ] AgentOS + CLAUDE.md setup
- [ ] README with documentation

**Status**: In progress

---

## Phase 2: Summer Climate

**Goal**: Add summer cooling automations

**Deliverables**:
- [ ] Summer climate automations per zone (chiller + fancoils)
- [ ] Seasonal switching logic (winter ↔ summer)
- [ ] Temperature threshold tuning per season

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
