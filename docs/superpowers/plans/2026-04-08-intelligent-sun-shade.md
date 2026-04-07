# Intelligent Sun Shade Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an adaptive sun-shade automation for the Meeting Room and Mensa using a shared HA blueprint with hybrid predictive + reactive decision logic, plus a nightly LLM-driven evaluator (two remote-scheduled Claude Code agents) that proposes threshold tweaks via Telegram with interactive approval.

**Architecture:** A single blueprint (`intelligent_sun_shade.yaml`) instantiated twice (Meeting Room ESE + Mensa SSW) drives two shelly covers. All thresholds are externalized as `input_number.*` helpers. A forecast populator automation calls `weather.get_forecasts` hourly and writes today's max into a dedicated helper (avoids the deprecated `forecast` attribute). A nightly `RemoteTrigger` at 21:00 UTC pulls HA history via REST API, writes a Markdown report, and proposes changes via Telegram Bot API with a Crockford base32 token. A morning `RemoteTrigger` at 05:00 UTC polls Telegram `getUpdates` for `apply`/`ignore` replies and applies approved changes to YAML + live HA state.

**Tech Stack:** Home Assistant YAML (blueprint, input_number, input_datetime, timer, counter, sensor/derivative, template), HA REST API, Telegram Bot API (curl), Claude Code `RemoteTrigger` (schedule skill), git.

**Spec:** `docs/superpowers/specs/2026-04-07-intelligent-sun-shade-design.md`

**Execution environment notes:**
- The repo at `/Volumes/docker/homeassistant` is a Synology volume mount. Edits are live to HA instantly; no NAS sync or `git pull` needed between edit and reload.
- HA runs at `https://hacm1.sales4.it` via Cloudflare Tunnel. The HA REST API is reachable from the Mac.
- The engineer executing this plan cannot SSH to the NAS. Any step that says "Run `docker exec ...`" is for the user to copy-paste into the NAS terminal themselves. All other steps run on the Mac or via HA UI.
- Steps marked 🧑 require the user to click around in HA UI; steps marked 🤖 are for the agent.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `homeassistant/config/input_numbers.yaml` | **Create** | 10 global `shade_*` threshold helpers + 2 per-room forecast snapshots |
| `homeassistant/config/input_datetimes.yaml` | **Create** | 4 close-timestamp datetimes |
| `homeassistant/config/timers.yaml` | **Create** | 2 manual-override grace timers |
| `homeassistant/config/counters.yaml` | **Create** | 2 manual-override counters |
| `homeassistant/config/sensors.yaml` | **Create** | 2 derivative sensors (rate of rise) — legacy `platform:` syntax only |
| `homeassistant/config/templates.yaml` | **Modify** | Append 2 template sensors (`sensor.meeting_room_temp`, `sensor.mensa_temp`) to the existing `- sensor:` list at line 546 |
| `homeassistant/config/configuration.yaml` | **Modify** | Add 5 new includes (`input_number`, `input_datetime`, `timer`, `counter`, `sensor`) |
| `homeassistant/config/blueprints/automation/custom/intelligent_sun_shade.yaml` | **Create** | The shared blueprint with 7 action branches |
| `homeassistant/config/automations.yaml` | **Modify** | Delete `mensa_sun_shade` (lines 403–483); add `sun_shade_forecast_populator`, `sun_shade_midnight_reset`, and the two blueprint instantiations |
| `homeassistant/config/dashboards/climate.yaml` | **Modify** | Add `Sun Shade — Thresholds & Activity` entities card under Window Shades |
| `homeassistant/eval-state.json` | **Create** | Initial state `{"version":1,"last_telegram_update_id":0,"pending_changes":[]}` |
| `docs/sun-shade-eval/.gitkeep` | **Create** | Reserve directory for nightly reports |
| Remote Trigger: `sun-shade-evaluator-nightly` | **Create** via `RemoteTrigger.create` | Daily analysis + propose (21:00 UTC) |
| Remote Trigger: `sun-shade-evaluator-morning` | **Create** via `RemoteTrigger.create` | Daily apply-approvals (05:00 UTC) |

**Untouched:** `cs_sun_shade` (out of scope per spec), all climate automations, all ESPHome files.

---

## Chunk 1: HA helper entities

Creates and registers all helper entities the blueprint will reference. After this chunk, the helpers exist in HA but nothing uses them yet. Validating this first means later chunks can reference the helpers without fear of "entity not found" errors.

### Task 1.1: Create `input_numbers.yaml`

**Files:**
- Create: `homeassistant/config/input_numbers.yaml`

- [ ] 🤖 **Step 1: Write the file**

```yaml
# Global sun-shade threshold helpers — tunable by the evaluator within bounds.
# See docs/superpowers/specs/2026-04-07-intelligent-sun-shade-design.md §Component 2.

shade_forecast_max_threshold:
  name: "Shade — Forecast Max Threshold"
  icon: mdi:thermometer-alert
  initial: 22.0
  min: 18
  max: 26
  step: 0.5
  unit_of_measurement: "°C"
  mode: box

shade_clouds_close_threshold:
  name: "Shade — Clouds (close)"
  icon: mdi:cloud-outline
  initial: 50
  min: 20
  max: 80
  step: 5
  unit_of_measurement: "%"
  mode: box

shade_clouds_open_threshold:
  name: "Shade — Clouds (open)"
  icon: mdi:cloud
  initial: 70
  min: 40
  max: 90
  step: 5
  unit_of_measurement: "%"
  mode: box

shade_room_cap:
  name: "Shade — Room Cap"
  icon: mdi:thermometer-high
  initial: 25.0
  min: 23
  max: 28
  step: 0.5
  unit_of_measurement: "°C"
  mode: box

shade_rate_threshold:
  name: "Shade — Rate Threshold"
  icon: mdi:chart-line-variant
  initial: 0.6
  min: 0.3
  max: 1.2
  step: 0.1
  unit_of_measurement: "°C/h"
  mode: box

shade_room_reopen:
  name: "Shade — Room Re-open"
  icon: mdi:thermometer-low
  initial: 23.0
  min: 21
  max: 25
  step: 0.5
  unit_of_measurement: "°C"
  mode: box

shade_closed_position:
  name: "Shade — Closed Position"
  icon: mdi:window-shutter
  initial: 30
  min: 0
  max: 50
  step: 5
  unit_of_measurement: "%"
  mode: box

shade_open_position:
  name: "Shade — Open Position"
  icon: mdi:window-shutter-open
  initial: 100
  min: 50
  max: 100
  step: 5
  unit_of_measurement: "%"
  mode: box

shade_grace_minutes:
  name: "Shade — Manual Grace (minutes)"
  icon: mdi:timer-outline
  initial: 30
  min: 10
  max: 59
  step: 1
  unit_of_measurement: "min"
  mode: box

# Populator-owned — NOT user-tunable, overwritten hourly by sun_shade_forecast_populator.
shade_today_outdoor_max_forecast:
  name: "Shade — Today's Forecast Max"
  icon: mdi:weather-sunny-alert
  initial: 0
  min: -20
  max: 50
  step: 0.1
  unit_of_measurement: "°C"
  mode: box

# Per-room snapshots — written by the blueprint at the moment of predictive close,
# read by the evaluator for predicted-vs-actual comparison.
meeting_room_forecast_max_at_window_start:
  name: "Meeting Room — Forecast at window start"
  icon: mdi:weather-sunny
  initial: 0
  min: -20
  max: 50
  step: 0.1
  unit_of_measurement: "°C"
  mode: box

mensa_forecast_max_at_window_start:
  name: "Mensa — Forecast at window start"
  icon: mdi:weather-sunny
  initial: 0
  min: -20
  max: 50
  step: 0.1
  unit_of_measurement: "°C"
  mode: box
```

- [ ] 🤖 **Step 2: Commit**

```bash
git add homeassistant/config/input_numbers.yaml
git commit -m "feat(ha): add sun shade input_number helpers

Adds 9 tunable global thresholds (forecast/clouds/room/rate/position/grace),
1 populator-owned today-forecast helper, and 2 per-room window-start snapshot
helpers. Bounds are the evaluator's guardrails."
```

### Task 1.2: Create `input_datetimes.yaml`

**Files:**
- Create: `homeassistant/config/input_datetimes.yaml`

- [ ] 🤖 **Step 1: Write the file**

```yaml
meeting_room_predictive_close_at:
  name: "Meeting Room — Last predictive close"
  icon: mdi:clock-outline
  has_date: true
  has_time: true

meeting_room_reactive_close_at:
  name: "Meeting Room — Last reactive close"
  icon: mdi:clock-alert-outline
  has_date: true
  has_time: true

mensa_predictive_close_at:
  name: "Mensa — Last predictive close"
  icon: mdi:clock-outline
  has_date: true
  has_time: true

mensa_reactive_close_at:
  name: "Mensa — Last reactive close"
  icon: mdi:clock-alert-outline
  has_date: true
  has_time: true
```

- [ ] 🤖 **Step 2: Commit**

```bash
git add homeassistant/config/input_datetimes.yaml
git commit -m "feat(ha): add sun shade close-timestamp helpers"
```

### Task 1.3: Create `timers.yaml`

**Files:**
- Create: `homeassistant/config/timers.yaml`

- [ ] 🤖 **Step 1: Write the file**

```yaml
shade_meeting_manual_grace:
  name: "Shade Meeting — Manual grace"
  icon: mdi:timer-sand
  duration: "00:30:00"
  restore: true

shade_mensa_manual_grace:
  name: "Shade Mensa — Manual grace"
  icon: mdi:timer-sand
  duration: "00:30:00"
  restore: true
```

Note: the default `duration` here is the fallback used if `timer.start` is called without an explicit duration. The blueprint always passes an explicit duration derived from `input_number.shade_grace_minutes`, so this default only matters if the timer is started manually from the UI.

- [ ] 🤖 **Step 2: Commit**

```bash
git add homeassistant/config/timers.yaml
git commit -m "feat(ha): add sun shade manual-override grace timers"
```

### Task 1.4: Create `counters.yaml`

**Files:**
- Create: `homeassistant/config/counters.yaml`

- [ ] 🤖 **Step 1: Write the file**

```yaml
meeting_room_manual_override_count:
  name: "Meeting Room — Manual override count"
  icon: mdi:hand-back-right
  initial: 0
  step: 1
  restore: true

mensa_manual_override_count:
  name: "Mensa — Manual override count"
  icon: mdi:hand-back-right
  initial: 0
  step: 1
  restore: true
```

- [ ] 🤖 **Step 2: Commit**

```bash
git add homeassistant/config/counters.yaml
git commit -m "feat(ha): add sun shade manual-override counters"
```

### Task 1.5: Create `sensors.yaml` with derivative sensors

**Files:**
- Create: `homeassistant/config/sensors.yaml`

The derivative platform must live under `sensor:` (legacy platform syntax) and cannot coexist in the modern `template:` block used by `templates.yaml`. That is why this is a separate file.

- [ ] 🤖 **Step 1: Write the file**

```yaml
# Derivative sensors for room-temperature rate of rise.
# Sources are the template sensors defined in templates.yaml (meeting_room_temp, mensa_temp)
# which expose climate.*.current_temperature as plain numeric sensors.
# See docs/superpowers/specs/2026-04-07-intelligent-sun-shade-design.md §Component 2.

- platform: derivative
  source: sensor.meeting_room_temp
  name: "Meeting Room Temp Rate"
  unique_id: meeting_room_temp_rate
  time_window: "00:30:00"
  unit_time: h
  round: 2

- platform: derivative
  source: sensor.mensa_temp
  name: "Mensa Temp Rate"
  unique_id: mensa_temp_rate
  time_window: "00:30:00"
  unit_time: h
  round: 2
```

- [ ] 🤖 **Step 2: Commit**

```bash
git add homeassistant/config/sensors.yaml
git commit -m "feat(ha): add derivative sensors for room temp rate of rise"
```

### Task 1.6: Append template sensors to `templates.yaml`

**Files:**
- Modify: `homeassistant/config/templates.yaml` — append to the existing `- sensor:` list at line 546 (the one that already holds Summer Comfort/Eco sensors)

- [ ] 🤖 **Step 1: Read the tail of templates.yaml**

Run the Read tool on `homeassistant/config/templates.yaml` with `offset: 560` to see the last sensor in the existing list and confirm the indentation pattern.

- [ ] 🤖 **Step 2: Append the two new template sensors**

Use the Edit tool to insert these entries **after** the last existing sensor in the `- sensor:` list (the "Summer Eco Common" entry ending around line 587). Match the 4-space indentation used by the existing sensors:

```yaml

    - name: "Meeting Room Temp"
      unique_id: meeting_room_temp
      state: "{{ state_attr('climate.meeting_room_climate', 'current_temperature') }}"
      unit_of_measurement: "°C"
      device_class: temperature
      state_class: measurement
      availability: >
        {{ state_attr('climate.meeting_room_climate', 'current_temperature') is not none }}

    - name: "Mensa Temp"
      unique_id: mensa_temp
      state: "{{ state_attr('climate.mensa_climate', 'current_temperature') }}"
      unit_of_measurement: "°C"
      device_class: temperature
      state_class: measurement
      availability: >
        {{ state_attr('climate.mensa_climate', 'current_temperature') is not none }}
```

Rationale: these materialize the `current_temperature` attribute of each climate entity as a plain numeric sensor state, so the `derivative` platform (which reads entity state, not attributes) can compute the rate of rise.

- [ ] 🤖 **Step 3: Verify the insertion is inside the `- sensor:` list, not outside it**

Use the Read tool to re-read the file around the modified region. The two new entries must be at the same indentation as "Summer Eco Common" (4 spaces, starting with `- name:`). If they landed at the top level with a `- sensor:` prefix, fix them — there can only be one `- sensor:` block.

- [ ] 🤖 **Step 4: Commit**

```bash
git add homeassistant/config/templates.yaml
git commit -m "feat(ha): add template sensors for Meeting Room and Mensa temps

Materializes climate.*.current_temperature as numeric sensor states
so the derivative platform can compute rate of rise over a 30-min window."
```

### Task 1.7: Wire includes into `configuration.yaml`

**Files:**
- Modify: `homeassistant/config/configuration.yaml` — add 5 new top-level includes

- [ ] 🤖 **Step 1: Add the 5 includes**

Use Edit to append these lines after the existing `template: !include templates.yaml` line (around line 36), so they land near the other includes:

```yaml

# --- Sun shade helpers (see docs/superpowers/specs/2026-04-07-intelligent-sun-shade-design.md) ---
input_number: !include input_numbers.yaml
input_datetime: !include input_datetimes.yaml
timer: !include timers.yaml
counter: !include counters.yaml
sensor: !include sensors.yaml
```

- [ ] 🤖 **Step 2: Commit**

```bash
git add homeassistant/config/configuration.yaml
git commit -m "feat(ha): wire sun shade helper includes"
```

### Task 1.8: Config check + restart + verification

**Files:** none — this is validation of Chunk 1 as a whole.

- [ ] 🧑 **Step 1: Run HA config check on the NAS**

Ask the user to run this in their NAS terminal:

```bash
docker exec HA_homeassistant python -m homeassistant --script check_config --config /config
```

Expected: `Testing configuration at /config` followed by `Configuration will be loaded successfully.` and no errors. If it reports errors, fix them before proceeding — **do not** restart HA with a broken config.

- [ ] 🧑 **Step 2: Restart HA**

User restarts HA via Settings → System → Restart (or `docker restart HA_homeassistant` on the NAS). A restart is required (not a reload) because new include files and new `input_number` / `timer` / `counter` domains can't be registered by a yaml-reload alone.

- [ ] 🤖 **Step 3: Verify HA REST API is reachable**

Before looping through 24 entities, confirm the API is responding at all. This is **the** long-lived access token that will also be reused later by Task 4.2 (don't delete it after this step — the evaluator needs it too).

```bash
export HA_TOKEN=<user-supplies>
export HA_BASE=https://hacm1.sales4.it
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_BASE/api/" | python3 -m json.tool
```

Expected: `{"message": "API running."}`. If 401, the token is wrong. If connection refused / timeout, HA or the Cloudflare Tunnel is down.

- [ ] 🤖 **Step 4: Verify all helper entities exist via REST API**

Using the `$HA_TOKEN` and `$HA_BASE` exported in Step 3:

```bash

for entity in \
  input_number.shade_forecast_max_threshold \
  input_number.shade_clouds_close_threshold \
  input_number.shade_clouds_open_threshold \
  input_number.shade_room_cap \
  input_number.shade_rate_threshold \
  input_number.shade_room_reopen \
  input_number.shade_closed_position \
  input_number.shade_open_position \
  input_number.shade_grace_minutes \
  input_number.shade_today_outdoor_max_forecast \
  input_number.meeting_room_forecast_max_at_window_start \
  input_number.mensa_forecast_max_at_window_start \
  input_datetime.meeting_room_predictive_close_at \
  input_datetime.meeting_room_reactive_close_at \
  input_datetime.mensa_predictive_close_at \
  input_datetime.mensa_reactive_close_at \
  timer.shade_meeting_manual_grace \
  timer.shade_mensa_manual_grace \
  counter.meeting_room_manual_override_count \
  counter.mensa_manual_override_count \
  sensor.meeting_room_temp \
  sensor.mensa_temp \
  sensor.meeting_room_temp_rate \
  sensor.mensa_temp_rate; do
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $HA_TOKEN" \
    "$HA_BASE/api/states/$entity")
  echo "$code  $entity"
done
```

Expected: every line shows `200` followed by the entity ID. Any `404` means that entity failed to register — investigate before proceeding.

Note: `sensor.meeting_room_temp_rate` and `sensor.mensa_temp_rate` will have state `unknown` until ~30 minutes of history has accumulated; that's expected and not a failure.

- [ ] 🧑 **Step 5: Spot-check defaults in HA UI**

User navigates to Settings → Devices & Services → Helpers and confirms the 9 `shade_*` threshold helpers appear with the correct default values and min/max bounds.

- [ ] 🤖 **Step 6: Tag the chunk completion (no commit needed, but noted)**

Chunk 1 is done. All helpers exist. Nothing uses them yet — that's Chunk 2.

---

## Chunk 2: Blueprint, forecast populator, midnight reset

Adds the shared blueprint and the two supporting automations (forecast populator + midnight counter reset). After this chunk the blueprint is available for instantiation but no room is wired up yet.

### Task 2.1: Create the blueprint file

**Files:**
- Create: `homeassistant/config/blueprints/automation/custom/intelligent_sun_shade.yaml`

- [ ] 🤖 **Step 1: Write the blueprint**

```yaml
blueprint:
  name: Intelligent Sun Shade
  description: >
    Hybrid sun-shade automation with predictive + reactive logic.
    Predictive close at sun-window start if today's forecast max is high
    and skies are clear. Reactive override closes if room temperature
    rises above the cap or faster than the rate threshold. Manual
    overrides start a grace timer during which the automation backs off.
    Startup re-evaluation handles HA cold-start mid-window.

    See docs/superpowers/specs/2026-04-07-intelligent-sun-shade-design.md
    for the full decision matrix and rationale.
  domain: automation
  author: Dagmar @ Salesupply Italy
  input:
    cover_entity:
      name: Cover
      description: The window shade to control
      selector:
        entity:
          domain: cover

    room_climate_entity:
      name: Room Climate Entity
      description: Climate entity whose current_temperature represents the room
      selector:
        entity:
          domain: climate

    rate_sensor_entity:
      name: Room Temperature Rate Sensor
      description: Derivative sensor exposing room temperature rate in °C/h
      selector:
        entity:
          domain: sensor

    manual_grace_timer:
      name: Manual Grace Timer
      description: Timer that disables the automation after a manual cover move
      selector:
        entity:
          domain: timer

    manual_override_counter:
      name: Manual Override Counter
      description: Counter incremented on every manual cover move
      selector:
        entity:
          domain: counter

    predictive_close_dt:
      name: Predictive Close Datetime
      description: input_datetime to record the last predictive close timestamp
      selector:
        entity:
          domain: input_datetime

    reactive_close_dt:
      name: Reactive Close Datetime
      description: input_datetime to record the last reactive close timestamp
      selector:
        entity:
          domain: input_datetime

    forecast_snapshot:
      name: Forecast Snapshot Helper
      description: input_number to snapshot today's forecast max at window start
      selector:
        entity:
          domain: input_number

    sun_azimuth_min:
      name: Sun Window Start Azimuth
      description: Sun azimuth at which the window begins (°)
      default: 90
      selector:
        number:
          min: 0
          max: 360
          step: 1
          unit_of_measurement: "°"

    sun_azimuth_max:
      name: Sun Window End Azimuth
      description: Sun azimuth at which the window ends (°)
      default: 150
      selector:
        number:
          min: 0
          max: 360
          step: 1
          unit_of_measurement: "°"

    sun_elevation_min:
      name: Minimum Sun Elevation
      description: Below this elevation the automation does not act (°)
      default: 15
      selector:
        number:
          min: 0
          max: 90
          step: 1
          unit_of_measurement: "°"

    room_label:
      name: Room Label
      description: Human-readable room name for Logbook messages
      selector:
        text:

mode: single
max_exceeded: silent

# Expose inputs as Jinja variables so templates inside actions can reference them.
variables:
  cover_entity: !input cover_entity
  room_climate_entity: !input room_climate_entity
  rate_sensor_entity: !input rate_sensor_entity
  manual_grace_timer: !input manual_grace_timer
  manual_override_counter: !input manual_override_counter
  predictive_close_dt: !input predictive_close_dt
  reactive_close_dt: !input reactive_close_dt
  forecast_snapshot: !input forecast_snapshot
  sun_azimuth_min: !input sun_azimuth_min
  sun_azimuth_max: !input sun_azimuth_max
  sun_elevation_min: !input sun_elevation_min
  room_label: !input room_label

triggers:
  - trigger: numeric_state
    entity_id: sun.sun
    attribute: azimuth
    above: !input sun_azimuth_min
    id: window_start

  - trigger: numeric_state
    entity_id: sun.sun
    attribute: azimuth
    above: !input sun_azimuth_max
    id: window_end

  - trigger: numeric_state
    entity_id: sun.sun
    attribute: elevation
    below: !input sun_elevation_min
    id: elevation_drop

  - trigger: numeric_state
    entity_id: weather.forecast_home
    attribute: cloud_coverage
    below: input_number.shade_clouds_close_threshold
    id: clear_sky

  - trigger: numeric_state
    entity_id: weather.forecast_home
    attribute: cloud_coverage
    above: input_number.shade_clouds_open_threshold
    id: cloudy

  - trigger: numeric_state
    entity_id: !input room_climate_entity
    attribute: current_temperature
    above: input_number.shade_room_cap
    for: "00:05:00"
    id: room_hot

  - trigger: numeric_state
    entity_id: !input rate_sensor_entity
    above: input_number.shade_rate_threshold
    for: "00:05:00"
    id: rate_high

  - trigger: numeric_state
    entity_id: !input room_climate_entity
    attribute: current_temperature
    below: input_number.shade_room_reopen
    id: room_cool

  - trigger: state
    entity_id: !input cover_entity
    id: manual_override

  - trigger: event
    event_type: timer.finished
    event_data:
      entity_id: !input manual_grace_timer
    id: grace_expired

  - trigger: state
    entity_id: input_select.climate_season
    id: season_change

  - trigger: homeassistant
    event: start
    id: startup

conditions:
  - condition: not
    conditions:
      - condition: state
        entity_id: input_select.climate_season
        state: winter

actions:
  - choose:

      # --- Branch 1: Manual override detected ---
      - conditions:
          - condition: trigger
            id: manual_override
          - condition: template
            value_template: >
              {{ trigger.to_state is not none
                 and trigger.to_state.context.user_id is not none }}
        sequence:
          - action: counter.increment
            target:
              entity_id: !input manual_override_counter
          - action: timer.start
            target:
              entity_id: !input manual_grace_timer
            data:
              duration: >-
                00:{{ '%02d' | format(states('input_number.shade_grace_minutes') | int) }}:00
          - action: logbook.log
            data:
              name: "Intelligent Sun Shade"
              message: "{{ room_label }}: manual override detected, grace timer started"

      # --- Branch 2: Predictive close at window start ---
      - conditions:
          - condition: trigger
            id: window_start
          - condition: state
            entity_id: !input manual_grace_timer
            state: idle
          - condition: numeric_state
            entity_id: sun.sun
            attribute: elevation
            above: !input sun_elevation_min
          - condition: numeric_state
            entity_id: input_number.shade_today_outdoor_max_forecast
            above: input_number.shade_forecast_max_threshold
          - condition: numeric_state
            entity_id: weather.forecast_home
            attribute: cloud_coverage
            below: input_number.shade_clouds_close_threshold
          - condition: numeric_state
            entity_id: !input cover_entity
            attribute: current_position
            above: 50
        sequence:
          - action: input_number.set_value
            target:
              entity_id: !input forecast_snapshot
            data:
              value: "{{ states('input_number.shade_today_outdoor_max_forecast') | float }}"
          - action: cover.set_cover_position
            target:
              entity_id: !input cover_entity
            data:
              position: "{{ states('input_number.shade_closed_position') | int }}"
          - action: input_datetime.set_datetime
            target:
              entity_id: !input predictive_close_dt
            data:
              datetime: "{{ now().isoformat() }}"
          - action: logbook.log
            data:
              name: "Intelligent Sun Shade"
              message: >-
                {{ room_label }}: predictive close
                (forecast max {{ states('input_number.shade_today_outdoor_max_forecast') }}°C,
                clouds {{ state_attr('weather.forecast_home', 'cloud_coverage') }}%)

      # --- Branch 3: Reactive override (room hot or rising fast) ---
      - conditions:
          - condition: or
            conditions:
              - condition: trigger
                id: room_hot
              - condition: trigger
                id: rate_high
          - condition: state
            entity_id: !input manual_grace_timer
            state: idle
          - condition: numeric_state
            entity_id: sun.sun
            attribute: azimuth
            above: !input sun_azimuth_min
          - condition: numeric_state
            entity_id: sun.sun
            attribute: azimuth
            below: !input sun_azimuth_max
          - condition: numeric_state
            entity_id: sun.sun
            attribute: elevation
            above: !input sun_elevation_min
          - condition: numeric_state
            entity_id: !input cover_entity
            attribute: current_position
            above: 50
        sequence:
          - action: cover.set_cover_position
            target:
              entity_id: !input cover_entity
            data:
              position: "{{ states('input_number.shade_closed_position') | int }}"
          - action: input_datetime.set_datetime
            target:
              entity_id: !input reactive_close_dt
            data:
              datetime: "{{ now().isoformat() }}"
          - action: logbook.log
            data:
              name: "Intelligent Sun Shade"
              message: >-
                {{ room_label }}: reactive close
                (room {{ state_attr(room_climate_entity, 'current_temperature') }}°C,
                rate {{ states(rate_sensor_entity) }}°C/h)

      # --- Branch 4: Re-open (cool + cloudy, or very cloudy) ---
      - conditions:
          - condition: or
            conditions:
              - condition: trigger
                id: room_cool
              - condition: trigger
                id: cloudy
          - condition: numeric_state
            entity_id: !input cover_entity
            attribute: current_position
            below: 50
          - condition: or
            conditions:
              - condition: and
                conditions:
                  - condition: numeric_state
                    entity_id: !input room_climate_entity
                    attribute: current_temperature
                    below: input_number.shade_room_reopen
                  - condition: numeric_state
                    entity_id: weather.forecast_home
                    attribute: cloud_coverage
                    above: input_number.shade_clouds_close_threshold
              - condition: numeric_state
                entity_id: weather.forecast_home
                attribute: cloud_coverage
                above: input_number.shade_clouds_open_threshold
        sequence:
          - action: cover.set_cover_position
            target:
              entity_id: !input cover_entity
            data:
              position: "{{ states('input_number.shade_open_position') | int }}"
          - action: logbook.log
            data:
              name: "Intelligent Sun Shade"
              message: "{{ room_label }}: re-opened (cool + cloudy)"

      # --- Branch 5: Window end (sun out of azimuth / elevation drop) ---
      - conditions:
          - condition: or
            conditions:
              - condition: trigger
                id: window_end
              - condition: trigger
                id: elevation_drop
          - condition: numeric_state
            entity_id: !input cover_entity
            attribute: current_position
            below: 50
        sequence:
          - action: cover.set_cover_position
            target:
              entity_id: !input cover_entity
            data:
              position: "{{ states('input_number.shade_open_position') | int }}"
          - action: logbook.log
            data:
              name: "Intelligent Sun Shade"
              message: "{{ room_label }}: re-opened (sun out of window)"

      # --- Branch 6: Grace timer expired, re-evaluate ---
      - conditions:
          - condition: trigger
            id: grace_expired
          - condition: numeric_state
            entity_id: sun.sun
            attribute: azimuth
            above: !input sun_azimuth_min
          - condition: numeric_state
            entity_id: sun.sun
            attribute: azimuth
            below: !input sun_azimuth_max
          - condition: numeric_state
            entity_id: !input cover_entity
            attribute: current_position
            above: 50
          - condition: or
            conditions:
              - condition: numeric_state
                entity_id: !input room_climate_entity
                attribute: current_temperature
                above: input_number.shade_room_cap
              - condition: and
                conditions:
                  - condition: numeric_state
                    entity_id: input_number.shade_today_outdoor_max_forecast
                    above: input_number.shade_forecast_max_threshold
                  - condition: numeric_state
                    entity_id: weather.forecast_home
                    attribute: cloud_coverage
                    below: input_number.shade_clouds_close_threshold
        sequence:
          - action: cover.set_cover_position
            target:
              entity_id: !input cover_entity
            data:
              position: "{{ states('input_number.shade_closed_position') | int }}"
          - action: logbook.log
            data:
              name: "Intelligent Sun Shade"
              message: "{{ room_label }}: grace expired, re-asserted close"

      # --- Branch 7: Startup re-evaluation (HA cold start mid-window) ---
      - conditions:
          - condition: trigger
            id: startup
        sequence:
          # Delay so weather/derivative entities finish loading before we check them.
          - delay: "00:00:30"
          - condition: state
            entity_id: !input manual_grace_timer
            state: idle
          - condition: numeric_state
            entity_id: sun.sun
            attribute: azimuth
            above: !input sun_azimuth_min
          - condition: numeric_state
            entity_id: sun.sun
            attribute: azimuth
            below: !input sun_azimuth_max
          - condition: numeric_state
            entity_id: sun.sun
            attribute: elevation
            above: !input sun_elevation_min
          - condition: numeric_state
            entity_id: input_number.shade_today_outdoor_max_forecast
            above: input_number.shade_forecast_max_threshold
          - condition: numeric_state
            entity_id: weather.forecast_home
            attribute: cloud_coverage
            below: input_number.shade_clouds_close_threshold
          - condition: numeric_state
            entity_id: !input cover_entity
            attribute: current_position
            above: 50
          - action: input_number.set_value
            target:
              entity_id: !input forecast_snapshot
            data:
              value: "{{ states('input_number.shade_today_outdoor_max_forecast') | float }}"
          - action: cover.set_cover_position
            target:
              entity_id: !input cover_entity
            data:
              position: "{{ states('input_number.shade_closed_position') | int }}"
          - action: input_datetime.set_datetime
            target:
              entity_id: !input predictive_close_dt
            data:
              datetime: "{{ now().isoformat() }}"
          - action: logbook.log
            data:
              name: "Intelligent Sun Shade"
              message: "{{ room_label }}: startup re-evaluation — closing (conditions met)"
```

**A note on `numeric_state` entity-id thresholds:** triggers like `above: input_number.shade_forecast_max_threshold` use HA's native "compare against another entity's state" form, which is cleaner than templated strings and avoids the "pick one form" issue the spec called out. The spec's templated form would also work but this is the idiomatic HA pattern.

- [ ] 🤖 **Step 2: Commit**

```bash
git add homeassistant/config/blueprints/automation/custom/intelligent_sun_shade.yaml
git commit -m "feat(ha): add intelligent_sun_shade blueprint

Single blueprint with 7 action branches:
  1. Manual override detection + grace timer start
  2. Predictive close at sun-window start
  3. Reactive override on room_hot or rate_high
  4. Re-open when room cool + clouds or very cloudy
  5. Window-end re-open on azimuth exit or elevation drop
  6. Grace-expired re-evaluation
  7. Startup re-evaluation for HA cold-start mid-window

Reads today's forecast max from input_number.shade_today_outdoor_max_forecast
(populator-owned, avoids the deprecated weather.forecast_home.forecast
attribute). Thresholds reference input_number.shade_* via entity-id form."
```

- [ ] 🧑 **Step 3: Reload blueprints in HA UI**

User navigates to Settings → Automations & Scenes → Blueprints → ⋮ → Reload blueprints. The new blueprint should appear in the list as "Intelligent Sun Shade" under the `custom` folder.

- [ ] 🧑 **Step 4: Spot-check blueprint validation**

If HA logs any blueprint validation errors, they appear in `home-assistant.log` and in Settings → System → Logs. Skim the log for `blueprint` errors. If none, the blueprint is syntactically sound. (Semantic validation happens when an instance is created in Chunk 3.)

### Task 2.2: Add the forecast populator automation

**Files:**
- Modify: `homeassistant/config/automations.yaml` — append a new automation

- [ ] 🤖 **Step 1: Read the last few lines of `automations.yaml` to match existing style**

Use the Read tool at the end of the file to see how existing automations end and confirm list-item indentation.

- [ ] 🤖 **Step 2: Append the forecast populator**

Append this automation to the end of `automations.yaml` (at the top-level list):

```yaml
- id: sun_shade_forecast_populator
  alias: Sun Shade — Populate today's outdoor max forecast
  description: >
    Calls weather.get_forecasts (the modern replacement for the deprecated
    forecast attribute) and writes today's max temperature into
    input_number.shade_today_outdoor_max_forecast so the blueprint can
    read it from a simple numeric_state condition.
  mode: single
  triggers:
    - trigger: homeassistant
      event: start
    - trigger: time
      at: "06:00:00"
    - trigger: time_pattern
      minutes: 5
  actions:
    - action: weather.get_forecasts
      target:
        entity_id: weather.forecast_home
      data:
        type: daily
      response_variable: forecast_response
    - variables:
        today_max: >
          {% set fc = forecast_response['weather.forecast_home'].forecast %}
          {% if fc and fc | length > 0 %}
            {{ fc[0].temperature | float(0) }}
          {% else %}
            0
          {% endif %}
    - action: input_number.set_value
      target:
        entity_id: input_number.shade_today_outdoor_max_forecast
      data:
        value: "{{ today_max }}"
```

The `time_pattern` with just `minutes: 5` fires at every HH:05 of every hour (so once an hour at :05). Combined with the 06:00 fixed trigger and the HA startup trigger, the helper is refreshed hourly and always at the start of the day.

- [ ] 🤖 **Step 3: Commit**

```bash
git add homeassistant/config/automations.yaml
git commit -m "feat(ha): add sun_shade_forecast_populator automation

Calls weather.get_forecasts hourly and writes today's forecast max into
input_number.shade_today_outdoor_max_forecast. Replaces the deprecated
state_attr('weather.forecast_home', 'forecast')[0] pattern."
```

### Task 2.3: Add the midnight counter reset automation

**Files:**
- Modify: `homeassistant/config/automations.yaml`

- [ ] 🤖 **Step 1: Append the reset automation**

```yaml
- id: sun_shade_midnight_reset
  alias: Sun Shade — Midnight counter reset
  description: >
    Resets per-room manual-override counters at 00:00:01 so the nightly
    evaluator (which runs at 21:00 UTC, before local midnight) sees the
    full day's counts, and the next day starts fresh.
  mode: single
  triggers:
    - trigger: time
      at: "00:00:01"
  actions:
    - action: counter.reset
      target:
        entity_id:
          - counter.meeting_room_manual_override_count
          - counter.mensa_manual_override_count
```

- [ ] 🤖 **Step 2: Commit**

```bash
git add homeassistant/config/automations.yaml
git commit -m "feat(ha): add sun_shade_midnight_reset automation

Resets manual-override counters daily at 00:00:01 local. The nightly
evaluator runs at 21:00 UTC which is always before local midnight, so
it sees the day's full counter value."
```

### Task 2.4: Reload automations, trigger populator once, verify

- [ ] 🧑 **Step 1: Reload automations**

User: Settings → Automations & Scenes → ⋮ → Reload automations. Both new automations (`sun_shade_forecast_populator`, `sun_shade_midnight_reset`) should appear with `on` state.

- [ ] 🧑 **Step 2: Manually trigger the populator**

User: Settings → Automations & Scenes → Sun Shade — Populate today's outdoor max forecast → Run. Watch for any errors in the trace.

- [ ] 🤖 **Step 3: Verify `shade_today_outdoor_max_forecast` is non-zero**

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_BASE/api/states/input_number.shade_today_outdoor_max_forecast" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['state'])"
```

Expected: a positive float like `21.4` (or whatever today's forecast is). If it's `0`, the `weather.get_forecasts` call failed — check the automation's last trace in HA UI.

---

## Chunk 3: Blueprint instantiations, mensa_sun_shade removal, dashboard, and live tests

Wires the blueprint to both rooms, removes the legacy standalone `mensa_sun_shade`, adds the dashboard panel, and runs the live reactive-override test. After this chunk, the HA side is fully operational and ready for the 1-week soak.

### Task 3.1: Add Meeting Room blueprint instance

**Files:**
- Modify: `homeassistant/config/automations.yaml`

- [ ] 🤖 **Step 1: Append the Meeting Room instantiation**

```yaml
- id: sun_shade_meeting_room
  alias: Sun Shade — Meeting Room
  description: Intelligent sun shade for the Meeting Room (ESE, azimuth 90–150°)
  use_blueprint:
    path: custom/intelligent_sun_shade.yaml
    input:
      cover_entity: cover.shellypro2cover_34987a47c9b0_cover_0
      room_climate_entity: climate.meeting_room_climate
      rate_sensor_entity: sensor.meeting_room_temp_rate
      manual_grace_timer: timer.shade_meeting_manual_grace
      manual_override_counter: counter.meeting_room_manual_override_count
      predictive_close_dt: input_datetime.meeting_room_predictive_close_at
      reactive_close_dt: input_datetime.meeting_room_reactive_close_at
      forecast_snapshot: input_number.meeting_room_forecast_max_at_window_start
      sun_azimuth_min: 90
      sun_azimuth_max: 150
      sun_elevation_min: 15
      room_label: "Meeting Room"
```

- [ ] 🤖 **Step 2: Commit**

```bash
git add homeassistant/config/automations.yaml
git commit -m "feat(ha): instantiate intelligent_sun_shade for Meeting Room (ESE)"
```

### Task 3.2: Add Mensa blueprint instance

**Files:**
- Modify: `homeassistant/config/automations.yaml`

- [ ] 🤖 **Step 1: Append the Mensa instantiation**

```yaml
- id: sun_shade_mensa
  alias: Sun Shade — Mensa
  description: Intelligent sun shade for Mensa (SSW, azimuth 170–240°)
  use_blueprint:
    path: custom/intelligent_sun_shade.yaml
    input:
      cover_entity: cover.shellypro2cover_2cbcbbb1ff9c_cover_0
      room_climate_entity: climate.mensa_climate
      rate_sensor_entity: sensor.mensa_temp_rate
      manual_grace_timer: timer.shade_mensa_manual_grace
      manual_override_counter: counter.mensa_manual_override_count
      predictive_close_dt: input_datetime.mensa_predictive_close_at
      reactive_close_dt: input_datetime.mensa_reactive_close_at
      forecast_snapshot: input_number.mensa_forecast_max_at_window_start
      sun_azimuth_min: 170
      sun_azimuth_max: 240
      sun_elevation_min: 15
      room_label: "Mensa"
```

- [ ] 🤖 **Step 2: Commit**

```bash
git add homeassistant/config/automations.yaml
git commit -m "feat(ha): instantiate intelligent_sun_shade for Mensa (SSW)"
```

### Task 3.3: Delete the legacy `mensa_sun_shade` automation

The new `sun_shade_mensa` blueprint instance covers the same cover entity. Both must not exist at the same time or they will race.

**Files:**
- Modify: `homeassistant/config/automations.yaml` — delete lines 403–483 (the `mensa_sun_shade` automation)

- [ ] 🤖 **Step 1: Verify the line range by reading**

Use Read on `homeassistant/config/automations.yaml` with `offset: 400, limit: 90` to confirm the `- id: mensa_sun_shade` automation spans the expected range. Line numbers may have shifted if earlier chunks modified the file.

- [ ] 🤖 **Step 2: Delete the automation block**

Use Edit to remove the entire `- id: mensa_sun_shade` entry, including its `alias`, `description`, `triggers`, `conditions`, and `actions`. Leave the surrounding automations untouched.

- [ ] 🤖 **Step 3: Commit**

```bash
git add homeassistant/config/automations.yaml
git commit -m "refactor(ha): remove legacy mensa_sun_shade

Replaced by the intelligent_sun_shade blueprint instance sun_shade_mensa,
which is a strict superset (same azimuth-based sun window + forecast gate
+ reactive override + manual grace). Both cannot coexist on the same
cover.shellypro2cover_2cbcbbb1ff9c_cover_0 entity."
```

### Task 3.4: Reload and verify automations

- [ ] 🧑 **Step 1: Reload automations**

User: Settings → Automations & Scenes → ⋮ → Reload automations.

- [ ] 🧑 **Step 2: Verify the three new automations appear**

Expected in the list:
- `Sun Shade — Meeting Room` (from blueprint)
- `Sun Shade — Mensa` (from blueprint)
- `Sun Shade — Populate today's outdoor max forecast` (already added in Chunk 2)
- `Sun Shade — Midnight counter reset` (already added in Chunk 2)

And `Mensa Sun Shade (Afternoon)` (the legacy one) should be **gone**.

- [ ] 🧑 **Step 3: Check home-assistant.log for blueprint errors**

Settings → System → Logs. If the blueprint fails to validate for either instance (e.g., an input references a non-existent entity), the error will be here. Fix any typos in the instantiation YAML and re-reload.

### Task 3.5: Add the dashboard panel

**Files:**
- Modify: `homeassistant/config/dashboards/climate.yaml` — add a new entities card under Window Shades

- [ ] 🤖 **Step 1: Find the Window Shades card location**

Use Read on `homeassistant/config/dashboards/climate.yaml` with `offset: 120, limit: 30` to find the existing "Window Shades" entities card (around line 125-133 based on the spec's references) and confirm the indentation.

- [ ] 🤖 **Step 2: Append the new card immediately after the Window Shades card**

Use Edit to insert this YAML at the same indentation as the Window Shades card (likely 6 spaces for `- type:` within the `cards:` list of the containing view):

```yaml
      - type: entities
        title: Sun Shade — Thresholds & Activity
        state_color: true
        entities:
          - type: section
            label: Global thresholds
          - entity: input_number.shade_forecast_max_threshold
            name: Forecast trigger
          - entity: input_number.shade_clouds_close_threshold
            name: Clouds (close)
          - entity: input_number.shade_clouds_open_threshold
            name: Clouds (open)
          - entity: input_number.shade_room_cap
            name: Room cap
          - entity: input_number.shade_rate_threshold
            name: Rate of rise
          - entity: input_number.shade_room_reopen
            name: Room re-open
          - entity: input_number.shade_closed_position
            name: Closed position
          - entity: input_number.shade_open_position
            name: Open position
          - entity: input_number.shade_grace_minutes
            name: Grace (minutes)
          - type: section
            label: Today
          - entity: input_number.shade_today_outdoor_max_forecast
            name: Forecast max today
          - entity: input_number.meeting_room_forecast_max_at_window_start
            name: Meeting — forecast at window start
          - entity: input_number.mensa_forecast_max_at_window_start
            name: Mensa — forecast at window start
          - type: section
            label: Manual overrides (today)
          - entity: counter.meeting_room_manual_override_count
            name: Meeting
          - entity: counter.mensa_manual_override_count
            name: Mensa
          - type: section
            label: Last close events
          - entity: input_datetime.meeting_room_predictive_close_at
            name: Meeting — predictive
          - entity: input_datetime.meeting_room_reactive_close_at
            name: Meeting — reactive
          - entity: input_datetime.mensa_predictive_close_at
            name: Mensa — predictive
          - entity: input_datetime.mensa_reactive_close_at
            name: Mensa — reactive
          - type: section
            label: Grace timers
          - entity: timer.shade_meeting_manual_grace
            name: Meeting
          - entity: timer.shade_mensa_manual_grace
            name: Mensa
```

Indentation in the actual file may need adjustment — match whatever the surrounding cards use.

- [ ] 🤖 **Step 3: Commit**

```bash
git add homeassistant/config/dashboards/climate.yaml
git commit -m "feat(dashboard): add Sun Shade thresholds + activity panel"
```

- [ ] 🧑 **Step 4: Reload the dashboard in HA UI**

User: Overview → ⋮ → Edit Dashboard → Raw Configuration Editor → reload (or refresh the browser tab). The new panel should appear under the existing Window Shades card with all 22 entities visible.

### Task 3.6: Live test — reactive override

This verifies the blueprint's Branch 3 (reactive close on room_hot) works end-to-end on the Meeting Room instance.

- [ ] 🧑 **Step 1: Record the current Meeting Room temperature**

Check `climate.meeting_room_climate` current_temperature in the HA UI.

- [ ] 🧑 **Step 2: Lower `input_number.shade_room_cap` to 1°C below current temp**

E.g., if the room is 22.5°C, set `shade_room_cap` to 21.0. Edit via the dashboard panel added in Task 3.5.

- [ ] 🧑 **Step 3: Wait ~5 minutes for the `for: "00:05:00"` debounce**

The `room_hot` trigger requires the temperature to stay above the cap for 5 continuous minutes before firing.

- [ ] 🧑 **Step 4: Confirm reactive close fired**

Check:
- `cover.shellypro2cover_34987a47c9b0_cover_0` is now at position 30 (closed)
- `input_datetime.meeting_room_reactive_close_at` has updated to the current time
- Logbook shows "Intelligent Sun Shade: Meeting Room: reactive close ..."

- [ ] 🧑 **Step 5: Restore `shade_room_cap` to 25.0**

Reset the threshold to its default so the automation returns to normal behavior.

- [ ] 🧑 **Step 6: Manually open the Meeting Room cover via dashboard**

Set its position back to 100 via the cover card.

- [ ] 🧑 **Step 7: Verify manual-override detection**

Check:
- `counter.meeting_room_manual_override_count` incremented from 0 to 1
- `timer.shade_meeting_manual_grace` is in `active` state with a non-zero `remaining` attribute
- Logbook shows "Intelligent Sun Shade: Meeting Room: manual override detected, grace timer started"

- [ ] 🧑 **Step 8: Wait for or force the grace timer to expire**

Either wait ~30 minutes, or force it via Developer Tools → Services → `timer.finish` with entity_id `timer.shade_meeting_manual_grace`. The grace-expired branch should re-evaluate and (if conditions are met) re-close. If the room is not currently hot/sunny, it stays open — that's correct.

### Task 3.7: Begin the 1-week soak period

- [ ] 🧑 **Step 1: Record today's date**

Note the start date. The evaluator side (Chunk 4) should not be enabled until at least 7 days have passed and the HA side has been observed to behave correctly across at least 2 sunny days.

- [ ] 🧑 **Step 2: Daily monitoring during the soak**

Each day, check:
- Did predictive close fire on sunny days? (Logbook + `meeting_room_predictive_close_at` + cover position history)
- Did reactive close fire if room temp spiked? (Logbook)
- Any manual overrides? (Dashboard counter)
- Any errors in home-assistant.log?

If the thresholds feel wrong, adjust via the dashboard directly — you're the tuning loop for now. Record observations; they feed into the evaluator prompt in Chunk 4.

**Chunk 3 complete when**: 1 week elapsed + automations behaving sensibly + no blocking errors.

---

## Chunk 4: Evaluator (state file + remote triggers + smoke tests)

Creates the evaluator infrastructure and enables the nightly analysis loop. Do not start this chunk until the 1-week soak in Chunk 3 is complete.

### Task 4.1: Initialize `eval-state.json`

**Files:**
- Create: `homeassistant/eval-state.json`
- Create: `docs/sun-shade-eval/.gitkeep`

- [ ] 🤖 **Step 1: Write the initial state file**

```json
{
  "version": 1,
  "last_telegram_update_id": 0,
  "pending_changes": []
}
```

- [ ] 🤖 **Step 2: Reserve the reports directory**

Create `docs/sun-shade-eval/.gitkeep` as an empty file. Git otherwise won't track empty directories and the nightly trigger's first commit would fail.

- [ ] 🤖 **Step 3: Commit both**

```bash
git add homeassistant/eval-state.json docs/sun-shade-eval/.gitkeep
git commit -m "feat(eval): initialize eval-state.json and reports directory"
```

### Task 4.2: Gather evaluator secrets

These are one-time setup actions the user must take. The secrets are stored inside the trigger prompts (not in the repo) and are only accessible through the user's claude.ai account.

- [ ] 🧑 **Step 1: Reuse (or create) the HA long-lived access token**

If you created a token during Task 1.8 Step 3 and still have it saved, reuse that one — it already has the scope the evaluator needs, and reusing avoids token sprawl. If you discarded it: Settings → (click your profile avatar, bottom-left) → Security tab → scroll to "Long-lived access tokens" → Create Token → name it "Sun Shade Evaluator" → copy the token. Save it securely (1Password / Keychain) — HA will not show it again.

- [ ] 🧑 **Step 2: Have the Telegram bot token ready**

The user already has a Telegram bot (used by the telegram plugin MCP). Retrieve the bot token from wherever it lives locally. The evaluator will also need the target chat ID — easiest way to find it: open the bot in Telegram, send any message, then `curl https://api.telegram.org/bot<TOKEN>/getUpdates | jq` from the Mac and look at `.result[-1].message.chat.id`.

- [ ] 🧑 **Step 3: Test the HA token once**

From the Mac:

```bash
curl -s -H "Authorization: Bearer <HA_TOKEN>" \
  https://hacm1.sales4.it/api/ \
  | python3 -m json.tool
```

Expected: `{"message": "API running."}`. If you get 401, the token is wrong.

### Task 4.3: Draft the nightly trigger prompt

The trigger prompt is long and specific. It is the most load-bearing part of the evaluator. Write it in a scratch file first, review, then use it to create the trigger.

**Files:**
- Scratch: `/tmp/sun-shade-evaluator-nightly-prompt.md` (not committed)

- [ ] 🤖 **Step 1: Write the prompt to /tmp**

Use the Write tool. The full prompt template is below. Fill in the three secrets inline before creating the trigger:

````markdown
# Sun Shade Evaluator — Nightly Analysis

You are the nightly analyzer for an adaptive HA sun shade automation system. Your job each night is to review the day's data, decide whether any threshold should be nudged, and — if so — commit a pending-change entry and notify the user via Telegram. You do NOT apply the change yourself; that happens in the morning trigger after the user replies with an approval token.

## Constants (fill these in — they are secrets)

```
HA_BASE_URL=https://hacm1.sales4.it
HA_TOKEN=<FILL IN: long-lived access token>
TG_BOT_TOKEN=<FILL IN: telegram bot token>
TG_CHAT_ID=<FILL IN: numeric chat id>
```

## Reference spec

Before doing anything, read `docs/superpowers/specs/2026-04-07-intelligent-sun-shade-design.md` from the repo checkout — specifically:
- §Component 2 for the threshold list + bounds
- §State file format for the pending_changes schema
- §Telegram message formats for the exact output shape you must produce
- §Glossary for every entity name you will query

## Procedure

1. **Date**: compute today's local date in Europe/Rome as `YYYY-MM-DD`. You will need this for the report filename and the token.

2. **Load current thresholds**: for each of these entities, GET their state from `$HA_BASE_URL/api/states/<entity>` with `Authorization: Bearer $HA_TOKEN`:
   - input_number.shade_forecast_max_threshold
   - input_number.shade_clouds_close_threshold
   - input_number.shade_clouds_open_threshold
   - input_number.shade_room_cap
   - input_number.shade_rate_threshold
   - input_number.shade_room_reopen
   - input_number.shade_closed_position
   - input_number.shade_open_position
   - input_number.shade_grace_minutes
   - input_number.shade_today_outdoor_max_forecast

   Note that `shade_today_outdoor_max_forecast` is populator-owned — you NEVER propose changes to it.

3. **Load per-room snapshots** (for both meeting_room and mensa):
   - input_number.<room>_forecast_max_at_window_start
   - input_datetime.<room>_predictive_close_at
   - input_datetime.<room>_reactive_close_at
   - counter.<room>_manual_override_count

4. **Load today's history**: GET `$HA_BASE_URL/api/history/period/<today_midnight_iso>?filter_entity_id=sensor.outdoor_temperature,cover.shellypro2cover_34987a47c9b0_cover_0,cover.shellypro2cover_2cbcbbb1ff9c_cover_0,climate.meeting_room_climate,climate.mensa_climate,weather.forecast_home,sensor.meeting_room_temp,sensor.mensa_temp&minimal_response=true&no_attributes=false` with the same auth header.

5. **Read existing state**: `Read homeassistant/eval-state.json` from the repo checkout. Note `last_telegram_update_id` (leave untouched — that's for the morning trigger) and any existing `pending_changes` entries.

6. **Analyze per room**: for Meeting Room and Mensa, compute:
   - Outdoor max actual (from sensor.outdoor_temperature history max today)
   - Forecast snapshot at window start (from the input_number you loaded)
   - Room temp: start of day, max, peak time, time spent above shade_room_cap
   - Cloud coverage: average during the sun window (07–18 local is fine as a broad window)
   - Cover position timeline: was it ever closed? at what time? when re-opened?
   - Predictive close fired? (check input_datetime.<room>_predictive_close_at is today)
   - Reactive close fired? (check input_datetime.<room>_reactive_close_at is today)
   - Manual overrides: counter value

7. **Verdict logic**:
   - `ok`: room peaked below shade_room_cap — thresholds are doing their job
   - `not_aggressive_enough`: room peaked above shade_room_cap AND predictive did not fire → propose lowering shade_forecast_max_threshold by 0.5 (within bounds)
   - `too_aggressive`: manual_override_count > 0 AND predictive fired → propose raising shade_room_cap or forecast threshold by 0.5
   - `forecast_wrong`: predicted max was off from actual by > 3°C → note in report, do NOT auto-propose
   - `insufficient_data`: recorder returned < 2 hours of data for the sun window, OR HA unreachable → write a report saying so, do NOT propose anything

8. **Guardrails before proposing any change**:
   - Never propose a change outside the min/max of the `input_number` you read in step 2 (HA will reject it anyway, but check client-side so the pending entry isn't a dead letter)
   - Never propose more than one change per run
   - If an existing pending_change has the same target entity_id: supersede it in place (preserve `token` and `created_at`, refresh `expires_at`, `reasoning`, `changes`, `report_file`)
   - Never propose a change to input_number.shade_today_outdoor_max_forecast

9. **Write the report** to `docs/sun-shade-eval/<YYYY-MM-DD>.md`. Use the exact markdown format from the spec's "Nightly — analysis report" section as the top of the file, then append raw per-room metrics tables below (min/max/peak time/time-above-cap/cover timeline).

10. **If proposing a change**:
    - Generate a token `EVAL-<YYYY-MM-DD>-<XXXX>` where XXXX is 4 Crockford base32 characters (from the set `0123456789ABCDEFGHJKMNPQRSTVWXYZ` — NO I, L, O, U)
    - Update `eval-state.json`: add/supersede the pending_change
    - Send the Telegram message using the exact template from the spec's "Nightly — analysis report" section, ending with `apply EVAL-...` / `ignore EVAL-...` instructions

11. **If not proposing a change**: use the "Nightly — no change to propose" Telegram template.

12. **Expire old pending entries**: for any entry where `now() > expires_at`, send the "Expired" Telegram template and remove it from `pending_changes`.

13. **Commit and push**:

```bash
git config user.email "sun-shade-evaluator@noreply.anthropic.com"
git config user.name "Sun Shade Evaluator"
git add docs/sun-shade-eval/<YYYY-MM-DD>.md homeassistant/eval-state.json
git commit -m "eval(sun-shade): nightly report for <YYYY-MM-DD>

<verdict>. <one-line summary>."
git push
```

If `git push` fails due to remote changes, `git pull --rebase origin main` and retry up to 3 times. If still failing, send a Telegram error message and exit.

## Telegram helpers (bash)

```bash
tg_send() {
  curl -s -X POST "https://api.telegram.org/bot$TG_BOT_TOKEN/sendMessage" \
    -d "chat_id=$TG_CHAT_ID" \
    -d "parse_mode=Markdown" \
    --data-urlencode "text=$1"
}
```

## Error handling

- HTTP 401 from HA → send HIGH PRIORITY Telegram message ("HA token rejected — rotate LLT and update trigger prompts"), exit without retry
- HA network error (5xx, connection refused) → send Telegram error, exit (next run retries)
- Telegram unreachable → write report and commit anyway; log the Telegram failure in the report
- Any other exception → send Telegram error with traceback, exit
````

- [ ] 🤖 **Step 2: Replace the secret placeholders**

Use the Edit tool to fill in `HA_TOKEN`, `TG_BOT_TOKEN`, `TG_CHAT_ID` with the actual values from Task 4.2. The values live only in `/tmp/sun-shade-evaluator-nightly-prompt.md` which is never committed.

### Task 4.4: Create the nightly `RemoteTrigger`

- [ ] 🤖 **Step 1: Load `RemoteTrigger` tool schema**

```
ToolSearch query: select:RemoteTrigger
```

- [ ] 🤖 **Step 2: Discover `environment_id` and `connector_uuid`**

The `RemoteTrigger.create` body requires two IDs the user's account already owns but that are not obvious from the plan alone:

- `environment_id` — the compute environment where the remote agent runs. Default is the user's only environment: `env_01EP7aJQxSXdtL1rwX9hy9Kk`. This can also be verified by invoking the `schedule` skill, which lists available environments at the top of its output.
- `connector_uuid` for the HomeAssistant MCP — the Nabu Casa MCP connector attached to the user's claude.ai account. Default: `3e8341aa-e108-4345-97dd-8679a0bc7c8b`, name `HomeAssistant-CM1`, URL `https://3822rbmiomh8rs7l2mamadli3w0nv3w9.ui.nabu.casa/api/mcp`. This is available by invoking the `schedule` skill which lists connected MCP connectors.

Both values are hardcoded in the create body below based on the skill's current output. If the user has rotated connectors or environments since this plan was written, invoke the `schedule` skill first to refresh the values before creating the trigger.

- [ ] 🤖 **Step 3: Verify the GitHub remote URL**

```bash
cd /Volumes/docker/homeassistant
git remote -v
```

Expected: `origin` points at `https://github.com/daggy72/homeassistant-config-s4it` (or equivalent SSH form). The trigger config uses the HTTPS URL. If the remote is different, update the `sources[].git_repository.url` in the create body accordingly.

- [ ] 🤖 **Step 4: Create the trigger (disabled initially)**

Read the full prompt from `/tmp/sun-shade-evaluator-nightly-prompt.md` and pass it as the `events[0].data.message.content` field. Generate a fresh UUID for the event.

```
RemoteTrigger action: create
body: {
  "name": "sun-shade-evaluator-nightly",
  "cron_expression": "0 21 * * *",
  "enabled": false,
  "job_config": {
    "ccr": {
      "environment_id": "env_01EP7aJQxSXdtL1rwX9hy9Kk",
      "session_context": {
        "model": "claude-sonnet-4-6",
        "sources": [
          {"git_repository": {"url": "https://github.com/daggy72/homeassistant-config-s4it"}}
        ],
        "allowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]
      },
      "events": [
        {"data": {
          "uuid": "<GENERATE fresh lowercase v4 uuid>",
          "session_id": "",
          "type": "user",
          "parent_tool_use_id": null,
          "message": {
            "content": "<FULL PROMPT FROM /tmp/sun-shade-evaluator-nightly-prompt.md>",
            "role": "user"
          }
        }}
      ]
    }
  },
  "mcp_connections": [
    {
      "connector_uuid": "3e8341aa-e108-4345-97dd-8679a0bc7c8b",
      "name": "HomeAssistant-CM1",
      "url": "https://3822rbmiomh8rs7l2mamadli3w0nv3w9.ui.nabu.casa/api/mcp"
    }
  ]
}
```

- [ ] 🤖 **Step 5: Record the trigger ID**

The response contains a trigger ID. Note it — you'll need it for the smoke test in Task 4.6. Also output the management URL: `https://claude.ai/code/scheduled/<TRIGGER_ID>`.

### Task 4.5: Draft and create the morning trigger

- [ ] 🤖 **Step 1: Write the morning prompt to /tmp**

`/tmp/sun-shade-evaluator-morning-prompt.md`:

````markdown
# Sun Shade Evaluator — Morning Apply

You are the morning apply-check for an adaptive HA sun shade automation system. The nightly evaluator proposes threshold changes and sends them to Telegram. Your job is to poll Telegram for `apply` / `ignore` replies and apply approved changes to both the YAML file and the running HA instance.

## Constants

```
HA_BASE_URL=https://hacm1.sales4.it
HA_TOKEN=<FILL IN: long-lived access token>
TG_BOT_TOKEN=<FILL IN: telegram bot token>
TG_CHAT_ID=<FILL IN: numeric chat id>
```

## Reference spec

Read `docs/superpowers/specs/2026-04-07-intelligent-sun-shade-design.md` §State file format, §Telegram message formats, and §Glossary.

## Procedure

1. **Read state**: `Read homeassistant/eval-state.json`. Capture `last_telegram_update_id` (call it `offset`). Capture `pending_changes` list.

2. **Poll Telegram**:

```bash
curl -s "https://api.telegram.org/bot$TG_BOT_TOKEN/getUpdates?offset=$((offset + 1))&timeout=0"
```

3. **For each update** in `.result`:
   - Extract `update.message.text` and `update.update_id`
   - Match against regex `^\s*(apply|ignore)\s+(EVAL-\d{4}-\d{2}-\d{2}-[0-9A-HJKMNP-TV-Z]{4})\s*$` (case-insensitive)
   - If match: `verb = group(1).lower()`, `token = group(2).upper()`
   - Update `max_update_id = max(max_update_id, update.update_id)` regardless of match

4. **For each (verb, token) pair**:
   - Find the pending_change entry with `token == token`
   - If not found: send `tg_send "Unknown token: $token"`, continue
   - If verb == "apply":
     - **Sanity check**: reject any change whose `entity_id` is `input_number.shade_today_outdoor_max_forecast` (that helper is populator-owned and must never be tuned). Send Telegram alert and leave the pending entry in place for the user to clean up.
     - For each change in `entry.changes`:
       - **Edit the YAML file with strict contextual anchoring** to prevent corrupting adjacent entries that share the same `initial:` value. The input_numbers.yaml file structure is:
         ```yaml
         <entity_short_name>:
           name: "..."
           icon: ...
           initial: <old_value>
           min: ...
           max: ...
           ...
         ```
         The `entity_short_name` is the part of `change.entity_id` after the `input_number.` prefix. Use the Edit tool with `old_string` containing at least **3 contiguous lines** that are uniquely identifiable:
         1. First, `Read` the YAML file around the target entity to see the exact surrounding lines.
         2. Construct `old_string` as the entity-key line + the `name:` line + the `initial:` line (all three, with exact whitespace preserved), e.g.:
            ```
            shade_forecast_max_threshold:
              name: "Shade — Forecast Max Threshold"
              icon: mdi:thermometer-alert
              initial: 22.0
            ```
         3. Construct `new_string` as the same block with only the `initial:` value replaced:
            ```
            shade_forecast_max_threshold:
              name: "Shade — Forecast Max Threshold"
              icon: mdi:thermometer-alert
              initial: 21.0
            ```
         4. If the Edit fails ("string not found" or "not unique"), STOP — do not fall back to a less-specific match. Send Telegram alert "YAML edit failed for $token — manual intervention needed", leave the pending entry in place, and exit this apply loop without touching the HA REST API.
       - POST `$HA_BASE_URL/api/services/input_number/set_value` with body `{"entity_id": "<change.entity_id>", "value": <change.new_value>}` and `Authorization: Bearer $HA_TOKEN`. Only do this if the YAML edit succeeded — otherwise the on-disk YAML and the live HA state would diverge on the next HA restart.
     - Append to `docs/sun-shade-eval/applied.log`: `<iso_now> applied <token> <changes_summary>`
     - Remove the pending_change entry
     - `tg_send "✅ Applied $token\n\n<change summary>"`
   - If verb == "ignore":
     - Append to `docs/sun-shade-eval/ignored.log`
     - Remove the pending_change entry
     - `tg_send "❌ Ignored $token"`

5. **Expire old entries**: for any remaining pending_change where `now() > expires_at`:
   - Append to `ignored.log` as "expired"
   - Remove from pending_changes
   - `tg_send "⏰ Expired $token (no reply within 24h)"`

6. **Update state**: set `last_telegram_update_id = max_update_id`, write back to `eval-state.json`.

7. **Commit and push**:

```bash
git config user.email "sun-shade-evaluator@noreply.anthropic.com"
git config user.name "Sun Shade Evaluator"
git add homeassistant/eval-state.json homeassistant/config/input_numbers.yaml docs/sun-shade-eval/
git commit -m "eval(sun-shade): morning apply for <YYYY-MM-DD>

<summary of applied/ignored/expired>"
git push
```

If no changes to commit (no updates matched), exit without committing.

## Guardrails

- If `input_number.set_value` returns HTTP 401 → HIGH PRIORITY Telegram alert, leave pending entry in place, exit
- If `input_number.set_value` returns HTTP 4xx with bounds error → Telegram alert with the error, leave pending entry in place, do not retry this token
- If the YAML edit fails (pattern not found) → Telegram alert, leave pending entry, exit
- Never touch `input_number.shade_today_outdoor_max_forecast` even if someone sends an apply token for it (sanity check: reject)

## Telegram helper

```bash
tg_send() {
  curl -s -X POST "https://api.telegram.org/bot$TG_BOT_TOKEN/sendMessage" \
    -d "chat_id=$TG_CHAT_ID" \
    -d "parse_mode=Markdown" \
    --data-urlencode "text=$1"
}
```
````

- [ ] 🤖 **Step 2: Fill in the secrets**

Same pattern as Task 4.3 Step 2 — Edit to replace the three `<FILL IN: ...>` placeholders.

- [ ] 🤖 **Step 3: Create the morning trigger**

```
RemoteTrigger action: create
body: {
  "name": "sun-shade-evaluator-morning",
  "cron_expression": "0 5 * * *",
  "enabled": false,
  "job_config": {
    "ccr": {
      "environment_id": "env_01EP7aJQxSXdtL1rwX9hy9Kk",
      "session_context": {
        "model": "claude-sonnet-4-6",
        "sources": [
          {"git_repository": {"url": "https://github.com/daggy72/homeassistant-config-s4it"}}
        ],
        "allowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]
      },
      "events": [
        {"data": {
          "uuid": "<GENERATE fresh lowercase v4 uuid>",
          "session_id": "",
          "type": "user",
          "parent_tool_use_id": null,
          "message": {
            "content": "<FULL PROMPT FROM /tmp/sun-shade-evaluator-morning-prompt.md>",
            "role": "user"
          }
        }}
      ]
    }
  },
  "mcp_connections": [
    {
      "connector_uuid": "3e8341aa-e108-4345-97dd-8679a0bc7c8b",
      "name": "HomeAssistant-CM1",
      "url": "https://3822rbmiomh8rs7l2mamadli3w0nv3w9.ui.nabu.casa/api/mcp"
    }
  ]
}
```

Record the trigger ID and management URL.

### Task 4.6: Smoke test the nightly trigger

- [ ] 🤖 **Step 1: Run the nightly trigger manually**

```
RemoteTrigger action: run
trigger_id: <nightly trigger id from Task 4.4>
```

This executes the trigger immediately, bypassing the cron schedule.

- [ ] 🤖 **Step 2: Wait for completion and inspect the remote run logs**

The `RemoteTrigger.run` response should include a run identifier or link. Open it in the browser or poll for status.

- [ ] 🧑 **Step 3: Verify Telegram message arrived**

User: check Telegram for the report. Should be either a "no change to propose" or "analysis report with proposal" message.

- [ ] 🤖 **Step 4: Verify commits landed on main**

```bash
cd /Volumes/docker/homeassistant
git fetch origin
git log origin/main -3 --oneline
```

Expected: the most recent commit is by "Sun Shade Evaluator" and touches `docs/sun-shade-eval/YYYY-MM-DD.md` and possibly `homeassistant/eval-state.json`.

- [ ] 🤖 **Step 5: Pull to local**

```bash
git pull --rebase origin main
```

Verify the new report file exists:

```bash
ls -la docs/sun-shade-eval/
```

- [ ] 🤖 **Step 6: Inspect the report**

Read the committed `docs/sun-shade-eval/YYYY-MM-DD.md`. Does it match the expected structure? Per-room metrics present? Verdict reasonable for the day's weather?

If anything is wrong, the fix is in the trigger prompt — update `/tmp/sun-shade-evaluator-nightly-prompt.md`, then `RemoteTrigger.update` the trigger with the new prompt (same trigger id). Repeat until the smoke test passes.

### Task 4.7: Smoke test an approval cycle

This tests the morning trigger even if the nightly didn't propose a change. To exercise the apply path, we'll hand-inject a pending entry with a real (small) change to `shade_grace_minutes` so the Edit tool actually has something to diff.

**Critical:** Run this test *before* Task 4.8 (enabling the triggers). If a real nightly proposal lands before the smoke test is done, the morning trigger will process both the real and the test entries and the ordering/blast radius gets murky.

- [ ] 🤖 **Step 1: Inject a test pending entry**

Edit `homeassistant/eval-state.json` to add a bounded, reversible test change: bump `shade_grace_minutes` from 30 → 31 (one minute, inside bounds 10–59):

```json
{
  "version": 1,
  "last_telegram_update_id": 0,
  "pending_changes": [
    {
      "token": "EVAL-2026-04-08-TEST",
      "created_at": "<now iso, e.g. 2026-04-08T23:00:00+02:00>",
      "expires_at": "<now + 24h iso>",
      "reasoning": "Smoke test — bump grace timer by 1 minute to exercise apply path end-to-end",
      "changes": [
        {
          "entity_id": "input_number.shade_grace_minutes",
          "yaml_file": "homeassistant/config/input_numbers.yaml",
          "yaml_key": "shade_grace_minutes.initial",
          "old_value": 30,
          "new_value": 31
        }
      ],
      "report_file": "docs/sun-shade-eval/smoke-test.md"
    }
  ]
}
```

Commit and push:

```bash
git add homeassistant/eval-state.json
git commit -m "test(eval): inject smoke-test pending entry"
git push
```

- [ ] 🧑 **Step 2: Reply `apply EVAL-2026-04-08-TEST` in Telegram**

User sends the literal text `apply EVAL-2026-04-08-TEST` to the bot.

- [ ] 🤖 **Step 3: Run the morning trigger manually**

```
RemoteTrigger action: run
trigger_id: <morning trigger id from Task 4.5>
```

- [ ] 🤖 **Step 4: Verify the apply succeeded**

- Telegram: user received a "✅ Applied EVAL-2026-04-08-TEST" message
- `git log origin/main -3` shows a commit touching `eval-state.json` AND `homeassistant/config/input_numbers.yaml`
- `curl -H "Authorization: Bearer $HA_TOKEN" $HA_BASE/api/states/input_number.shade_grace_minutes` shows state `31`
- `eval-state.json` no longer contains the EVAL-2026-04-08-TEST entry
- Diffing `input_numbers.yaml`, ONLY the `shade_grace_minutes:` block has `initial: 31` — all other `initial:` values are unchanged (this verifies the contextual anchoring worked correctly)

If any step fails, inspect the morning trigger's run logs and iterate on its prompt.

- [ ] 🤖 **Step 5: Reset the smoke-test value back to 30**

```bash
curl -s -X POST \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "input_number.shade_grace_minutes", "value": 30}' \
  $HA_BASE/api/services/input_number/set_value
```

Then edit `homeassistant/config/input_numbers.yaml` back to `initial: 30` under `shade_grace_minutes:`, commit and push:

```bash
git add homeassistant/config/input_numbers.yaml
git commit -m "test(eval): reset shade_grace_minutes after smoke test"
git push
```

- [ ] 🤖 **Step 6: Optional — test the ignore path**

Repeat Task 4.7 Steps 1-4 with a new token `EVAL-2026-04-08-IGN2` (a new `new_value`, e.g. 32, so the YAML anchor differs from step 1's state) and reply `ignore EVAL-2026-04-08-IGN2`. Verify Telegram confirms "❌ Ignored" and the entry is removed from `eval-state.json`. The YAML is untouched on ignore, so no reset is needed.

### Task 4.8: Enable both triggers

- [ ] 🤖 **Step 1: Enable nightly**

```
RemoteTrigger action: update
trigger_id: <nightly id>
body: {"enabled": true}
```

- [ ] 🤖 **Step 2: Enable morning**

```
RemoteTrigger action: update
trigger_id: <morning id>
body: {"enabled": true}
```

- [ ] 🤖 **Step 3: List triggers to confirm**

```
RemoteTrigger action: list
```

Both triggers should show `enabled: true` and their next scheduled run times.

- [ ] 🧑 **Step 4: Week-1 watch**

Over the next 7 days, the user monitors:
- Nightly Telegram messages arriving at ~23:00 local
- Any morning `apply` confirmations land correctly
- No repeated "HA token rejected" errors
- Reports in `docs/sun-shade-eval/` look sensible — each one a day of data + verdict

If the evaluator proposes something questionable, reply `ignore` and move on. Patterns emerging after a week inform whether the thresholds need bigger manual adjustments.

---

## Definition of done

- [ ] All 9 `shade_*` threshold helpers visible in HA UI with correct defaults
- [ ] `shade_today_outdoor_max_forecast` is non-zero (populator working)
- [ ] Blueprint `Intelligent Sun Shade` appears in HA Blueprints list
- [ ] Both `sun_shade_meeting_room` and `sun_shade_mensa` automations appear and are enabled
- [ ] Legacy `mensa_sun_shade` is removed
- [ ] Dashboard panel visible with all 22 entities
- [ ] Reactive override live test passed (Task 3.6)
- [ ] 1-week soak complete with sensible behavior
- [ ] Both remote triggers created and both smoke tests passed
- [ ] Both triggers enabled; next scheduled run visible in `RemoteTrigger.list` output
- [ ] User received at least one real nightly report on Telegram after enablement
