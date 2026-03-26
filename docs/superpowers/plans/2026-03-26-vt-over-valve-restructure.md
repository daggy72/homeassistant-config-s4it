# VT-over-Valve Restructure Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 7 old fancoil VTs (thermostat_over_switch with dummy input_booleans) with new VTs (thermostat_over_valve with template number entities) so VT outputs proportional 0-100% demand that gets translated to 3-speed/6-speed ESP32 relay fan control.

**Architecture:** Each zone gets a template number entity (0-100%) in `templates.yaml`. The template number's `set_value` action translates VT demand to ESP32 fan speeds (6-step cascade for dual rooms, 3-step for single rooms). VTs are created fresh via HA UI as `thermostat_over_valve` pointing at these template numbers. Old VTs, dummy input_booleans, and the workaround speed control automation are deleted.

**Tech Stack:** Home Assistant YAML (templates.yaml, automations.yaml, configuration.yaml), Versatile Thermostat integration (HA UI), ESPHome fan entities

**Spec:** `docs/superpowers/specs/2026-03-26-vt-over-valve-restructure-design.md`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `homeassistant/config/templates.yaml` | Modify | Add 7 new template number entities for old fancoil zones |
| `homeassistant/config/automations.yaml` | Modify | Remove `fancoil_speed_control_esphome` automation |
| `homeassistant/config/configuration.yaml` | Modify | Remove duplicate `input_boolean` block with dummy fancoil entities |
| HA UI (VT integration) | Manual | Delete 7 old VTs, create 7 new VTs as `thermostat_over_valve` |

---

## Chunk 1: Template Numbers and Cleanup

### Task 1: Add 7 template number entities for old fancoil zones

**Files:**
- Modify: `homeassistant/config/templates.yaml` (append after existing Shelly 0-10V template numbers, before demand sensors)

- [ ] **Step 1: Add Dagmar template number (temporary on/off)**

Append to the `number:` list in `templates.yaml`, after "Fancoil Projects 2" (line 110):

```yaml
    # --- Old fancoil template numbers (ESP32 3-speed relay control) ---
    # VT (over_valve mode) sends 0-100% → template number → ESP32 fan speed

    - name: "Fancoil Dagmar"
      unique_id: fancoil_dagmar
      min: 0
      max: 100
      step: 1
      unit_of_measurement: "%"
      state: >
        {% if is_state('switch.smart_switch_25010986516751513702c4e7ae1293a2_outlet', 'on') %}
          100
        {% else %}
          0
        {% endif %}
      set_value:
        - if:
            - condition: template
              value_template: "{{ value | int > 0 }}"
          then:
            - action: switch.turn_on
              target:
                entity_id: switch.smart_switch_25010986516751513702c4e7ae1293a2_outlet
          else:
            - action: switch.turn_off
              target:
                entity_id: switch.smart_switch_25010986516751513702c4e7ae1293a2_outlet
```

- [ ] **Step 2: Add 4 dual-room template numbers (6-step cascade)**

Append after Dagmar. Each dual-room template number uses the same cascade logic with different fan entity IDs:

```yaml
    - name: "Fancoil Tania"
      unique_id: fancoil_tania_valve
      min: 0
      max: 100
      step: 1
      unit_of_measurement: "%"
      state: >
        {% set a = state_attr('fan.fancoil_09_fancoil', 'percentage') | int(0) %}
        {% set b = state_attr('fan.fancoil_10_fancoil', 'percentage') | int(0) %}
        {% if is_state('fan.fancoil_09_fancoil', 'off') %}{% set a = 0 %}{% endif %}
        {% if is_state('fan.fancoil_10_fancoil', 'off') %}{% set b = 0 %}{% endif %}
        {{ ((a + b) / 2) | round(0) }}
      set_value:
        - variables:
            step: >
              {% if value | int <= 0 %}0
              {% elif value | int <= 17 %}1
              {% elif value | int <= 33 %}2
              {% elif value | int <= 50 %}3
              {% elif value | int <= 67 %}4
              {% elif value | int <= 83 %}5
              {% else %}6
              {% endif %}
            spd_a: "{{ [0, 33, 33, 67, 67, 100, 100][step | int] }}"
            spd_b: "{{ [0, 0, 33, 33, 67, 67, 100][step | int] }}"
        - if:
            - condition: template
              value_template: "{{ spd_a | int > 0 }}"
          then:
            - action: fan.turn_on
              target:
                entity_id: fan.fancoil_09_fancoil
              data:
                percentage: "{{ spd_a }}"
          else:
            - action: fan.turn_off
              target:
                entity_id: fan.fancoil_09_fancoil
        - if:
            - condition: template
              value_template: "{{ spd_b | int > 0 }}"
          then:
            - action: fan.turn_on
              target:
                entity_id: fan.fancoil_10_fancoil
              data:
                percentage: "{{ spd_b }}"
          else:
            - action: fan.turn_off
              target:
                entity_id: fan.fancoil_10_fancoil

    - name: "Fancoil CS"
      unique_id: fancoil_cs_valve
      min: 0
      max: 100
      step: 1
      unit_of_measurement: "%"
      state: >
        {% set a = state_attr('fan.fancoil_08_fancoil', 'percentage') | int(0) %}
        {% set b = state_attr('fan.fancoil_07_fancoil', 'percentage') | int(0) %}
        {% if is_state('fan.fancoil_08_fancoil', 'off') %}{% set a = 0 %}{% endif %}
        {% if is_state('fan.fancoil_07_fancoil', 'off') %}{% set b = 0 %}{% endif %}
        {{ ((a + b) / 2) | round(0) }}
      set_value:
        - variables:
            step: >
              {% if value | int <= 0 %}0
              {% elif value | int <= 17 %}1
              {% elif value | int <= 33 %}2
              {% elif value | int <= 50 %}3
              {% elif value | int <= 67 %}4
              {% elif value | int <= 83 %}5
              {% else %}6
              {% endif %}
            spd_a: "{{ [0, 33, 33, 67, 67, 100, 100][step | int] }}"
            spd_b: "{{ [0, 0, 33, 33, 67, 67, 100][step | int] }}"
        - if:
            - condition: template
              value_template: "{{ spd_a | int > 0 }}"
          then:
            - action: fan.turn_on
              target:
                entity_id: fan.fancoil_08_fancoil
              data:
                percentage: "{{ spd_a }}"
          else:
            - action: fan.turn_off
              target:
                entity_id: fan.fancoil_08_fancoil
        - if:
            - condition: template
              value_template: "{{ spd_b | int > 0 }}"
          then:
            - action: fan.turn_on
              target:
                entity_id: fan.fancoil_07_fancoil
              data:
                percentage: "{{ spd_b }}"
          else:
            - action: fan.turn_off
              target:
                entity_id: fan.fancoil_07_fancoil

    - name: "Fancoil Meeting"
      unique_id: fancoil_meeting_valve
      min: 0
      max: 100
      step: 1
      unit_of_measurement: "%"
      state: >
        {% set a = state_attr('fan.fancoil_05_fancoil', 'percentage') | int(0) %}
        {% set b = state_attr('fan.fancoil_06_fancoil', 'percentage') | int(0) %}
        {% if is_state('fan.fancoil_05_fancoil', 'off') %}{% set a = 0 %}{% endif %}
        {% if is_state('fan.fancoil_06_fancoil', 'off') %}{% set b = 0 %}{% endif %}
        {{ ((a + b) / 2) | round(0) }}
      set_value:
        - variables:
            step: >
              {% if value | int <= 0 %}0
              {% elif value | int <= 17 %}1
              {% elif value | int <= 33 %}2
              {% elif value | int <= 50 %}3
              {% elif value | int <= 67 %}4
              {% elif value | int <= 83 %}5
              {% else %}6
              {% endif %}
            spd_a: "{{ [0, 33, 33, 67, 67, 100, 100][step | int] }}"
            spd_b: "{{ [0, 0, 33, 33, 67, 67, 100][step | int] }}"
        - if:
            - condition: template
              value_template: "{{ spd_a | int > 0 }}"
          then:
            - action: fan.turn_on
              target:
                entity_id: fan.fancoil_05_fancoil
              data:
                percentage: "{{ spd_a }}"
          else:
            - action: fan.turn_off
              target:
                entity_id: fan.fancoil_05_fancoil
        - if:
            - condition: template
              value_template: "{{ spd_b | int > 0 }}"
          then:
            - action: fan.turn_on
              target:
                entity_id: fan.fancoil_06_fancoil
              data:
                percentage: "{{ spd_b }}"
          else:
            - action: fan.turn_off
              target:
                entity_id: fan.fancoil_06_fancoil

    - name: "Fancoil OpenSpace"
      unique_id: fancoil_openspace_valve
      min: 0
      max: 100
      step: 1
      unit_of_measurement: "%"
      state: >
        {% set a = state_attr('fan.fancoilcontroller_01_fancoil', 'percentage') | int(0) %}
        {% set b = state_attr('fan.fancoil_02_fancoil', 'percentage') | int(0) %}
        {% if is_state('fan.fancoilcontroller_01_fancoil', 'off') %}{% set a = 0 %}{% endif %}
        {% if is_state('fan.fancoil_02_fancoil', 'off') %}{% set b = 0 %}{% endif %}
        {{ ((a + b) / 2) | round(0) }}
      set_value:
        - variables:
            step: >
              {% if value | int <= 0 %}0
              {% elif value | int <= 17 %}1
              {% elif value | int <= 33 %}2
              {% elif value | int <= 50 %}3
              {% elif value | int <= 67 %}4
              {% elif value | int <= 83 %}5
              {% else %}6
              {% endif %}
            spd_a: "{{ [0, 33, 33, 67, 67, 100, 100][step | int] }}"
            spd_b: "{{ [0, 0, 33, 33, 67, 67, 100][step | int] }}"
        - if:
            - condition: template
              value_template: "{{ spd_a | int > 0 }}"
          then:
            - action: fan.turn_on
              target:
                entity_id: fan.fancoilcontroller_01_fancoil
              data:
                percentage: "{{ spd_a }}"
          else:
            - action: fan.turn_off
              target:
                entity_id: fan.fancoilcontroller_01_fancoil
        - if:
            - condition: template
              value_template: "{{ spd_b | int > 0 }}"
          then:
            - action: fan.turn_on
              target:
                entity_id: fan.fancoil_02_fancoil
              data:
                percentage: "{{ spd_b }}"
          else:
            - action: fan.turn_off
              target:
                entity_id: fan.fancoil_02_fancoil
```

- [ ] **Step 3: Add 2 single-room template numbers (3-step)**

Append after OpenSpace:

```yaml
    - name: "Fancoil Reception"
      unique_id: fancoil_reception_valve
      min: 0
      max: 100
      step: 1
      unit_of_measurement: "%"
      state: >
        {% if is_state('fan.fancoil_04_fancoil', 'off') %}
          0
        {% else %}
          {{ state_attr('fan.fancoil_04_fancoil', 'percentage') | int(0) }}
        {% endif %}
      set_value:
        - variables:
            spd: >
              {% if value | int <= 0 %}0
              {% elif value | int <= 33 %}33
              {% elif value | int <= 67 %}67
              {% else %}100
              {% endif %}
        - if:
            - condition: template
              value_template: "{{ spd | int > 0 }}"
          then:
            - action: fan.turn_on
              target:
                entity_id: fan.fancoil_04_fancoil
              data:
                percentage: "{{ spd }}"
          else:
            - action: fan.turn_off
              target:
                entity_id: fan.fancoil_04_fancoil

    - name: "Fancoil Entrance"
      unique_id: fancoil_entrance_valve
      min: 0
      max: 100
      step: 1
      unit_of_measurement: "%"
      state: >
        {% if is_state('fan.fancoil_03_fancoil', 'off') %}
          0
        {% else %}
          {{ state_attr('fan.fancoil_03_fancoil', 'percentage') | int(0) }}
        {% endif %}
      set_value:
        - variables:
            spd: >
              {% if value | int <= 0 %}0
              {% elif value | int <= 33 %}33
              {% elif value | int <= 67 %}67
              {% else %}100
              {% endif %}
        - if:
            - condition: template
              value_template: "{{ spd | int > 0 }}"
          then:
            - action: fan.turn_on
              target:
                entity_id: fan.fancoil_03_fancoil
              data:
                percentage: "{{ spd }}"
          else:
            - action: fan.turn_off
              target:
                entity_id: fan.fancoil_03_fancoil
```

- [ ] **Step 4: Reload templates via HA API**

```bash
export TOKEN=$(cat /volume1/docker/homeassistant/.env | grep HA_API_TOKEN | cut -d= -f2)
curl -s -X POST http://localhost:8123/api/services/template/reload \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json"
```

Expected: 7 new `number.fancoil_*` entities appear in HA (Developer Tools → States → filter "number.fancoil").

- [ ] **Step 5: Verify template numbers exist**

Check via API that all 7 number entities are available:
```bash
for n in fancoil_dagmar fancoil_tania_valve fancoil_cs_valve fancoil_meeting_valve fancoil_openspace_valve fancoil_reception_valve fancoil_entrance_valve; do
  echo -n "number.$n: "
  curl -s http://localhost:8123/api/states/number.$n -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.loads(sys.stdin.read())['state'])"
done
```

Expected: Each shows a numeric value (likely 0).

---

### Task 2: Remove workaround speed control automation

**Files:**
- Modify: `homeassistant/config/automations.yaml`

- [ ] **Step 1: Remove the `fancoil_speed_control_esphome` automation**

Delete the entire automation block with `id: fancoil_speed_control_esphome` from `automations.yaml` (the large block with `time_pattern` trigger and `repeat.for_each` loop).

- [ ] **Step 2: Reload automations**

```bash
curl -s -X POST http://localhost:8123/api/services/automation/reload \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json"
```

---

### Task 3: Remove dummy input_booleans

**Files:**
- Modify: `homeassistant/config/configuration.yaml`

- [ ] **Step 1: Remove duplicate input_boolean block**

In `configuration.yaml`, there are two `input_boolean:` blocks. Remove the second one (lines ~41-62) that contains the dummy fancoil entities (`fancoil_tania`, `fancoil_cs`, `fancoil_meeting`, `fancoil_openspace`, `fancoil_reception`, `fancoil_entrance`). Keep the first block with just `heating_season`.

- [ ] **Step 2: Restart HA or reload input_booleans**

Input booleans require a restart to remove. This will be done after the VTs are deleted in Task 4.

---

## Chunk 2: VT Recreation (User Manual Steps)

### Task 4: Delete old VTs and create new ones (HA UI)

This task is performed by the user in the HA UI. Claude provides the exact settings for each new VT.

- [ ] **Step 1: Note current VT preset temperatures**

Before deleting, record the preset temperatures for each VT (they'll need to be re-entered). Current values:

| VT | Comfort | Eco | Frost | Boost |
|----|---------|-----|-------|-------|
| Fancoil Dagmar | 22.5 | 18 | 15 | 24 |
| Fancoil Tania | 22.5 | 18 | 15 | 24 |
| Fancoil CS | 22 | 18 | 15 | 24 |
| Fancoil Meeting | 20 | 17 | 15 | 23 |
| Fancoil OpenSpace | 20 | 17 | 15 | 22 |
| Fancoil Reception | 22 | 18 | 15 | 24 |
| Fancoil Entrance | 20 | 17 | 15 | 22 |

- [ ] **Step 2: Delete all 7 old VTs**

Settings → Devices & Services → Versatile Thermostat → delete each:
- Fancoil Dagmar
- Fancoil Tania
- Fancoil CS
- Fancoil Meeting
- Fancoil OpenSpace
- Fancoil Reception
- Fancoil Entrance

Do NOT delete: Projects 1, Climate Mensa, Central configuration.

- [ ] **Step 3: Restart HA**

Full restart to clear old entity registrations and remove dummy input_booleans.

- [ ] **Step 4: Create 7 new VTs as thermostat_over_valve**

Settings → Devices & Services → Add Integration → Versatile Thermostat

For each VT, use these settings:

**Common settings for all:**
- Thermostat type: `thermostat_over_valve` (or "over valve" in UI)
- Proportional function: TPI
- Use central TPI config: Yes (uses central `coef_int` and `coef_ext`)
- Use central presets: No (each zone has different comfort/eco/frost temps)
- Use central features: Yes for window, presence, power, lock (same as before)
- Step temperature: 0.5
- Cycle min: 5

**Per-zone settings:**

| Name (exact!) | Underlying entity | Temperature sensor | Presets (comfort/eco/frost/boost) |
|---------------|-------------------|-------------------|----------------------------------|
| Fancoil Dagmar | `number.fancoil_dagmar` | `sensor.up_sense_temperature_2` | 22.5 / 18 / 15 / 24 |
| Fancoil Tania | `number.fancoil_tania_valve` | `sensor.up_sense_temperature` | 22.5 / 18 / 15 / 24 |
| Fancoil CS | `number.fancoil_cs_valve` | `sensor.cc_up_sense_temperature` | 22 / 18 / 15 / 24 |
| Fancoil Meeting | `number.fancoil_meeting_valve` | `sensor.mt_meeting_room_up_sense_temperature` | 20 / 17 / 15 / 23 |
| Fancoil OpenSpace | `number.fancoil_openspace_valve` | `sensor.openspace_up_sense_temperature` | 20 / 17 / 15 / 22 |
| Fancoil Reception | `number.fancoil_reception_valve` | `sensor.reception_up_sense_temperature` | 22 / 18 / 15 / 24 |
| Fancoil Entrance | `number.fancoil_entrance_valve` | `sensor.openspace_up_sense_temperature` | 20 / 17 / 15 / 22 |

**Important:** Use the EXACT names above so HA generates matching entity IDs for the dashboard.

- [ ] **Step 5: Verify entity IDs match dashboard**

Check that these entity IDs exist after creation:
- `climate.fancoil_dagmar`
- `climate.fancoil_tania`
- `climate.fancoil_cs`
- `climate.fancoil_meeting`
- `climate.fancoil_openspace`
- `climate.fancoil_reception`
- `climate.fancoil_entrance`

If any got a `_2` suffix, rename via Settings → Entities → find entity → change entity ID.

- [ ] **Step 6: Set all VTs to comfort preset**

Via API (or HA UI):
```bash
curl -s -X POST http://localhost:8123/api/services/climate/set_preset_mode \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"entity_id":["climate.fancoil_dagmar","climate.fancoil_tania","climate.fancoil_cs","climate.fancoil_reception"],"preset_mode":"comfort"}'

curl -s -X POST http://localhost:8123/api/services/climate/set_preset_mode \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"entity_id":["climate.fancoil_meeting","climate.fancoil_openspace","climate.fancoil_entrance"],"preset_mode":"comfort"}'
```

---

### Task 5: Verify and test

- [ ] **Step 1: Check demand sensors show proportional values**

Check Fancoil Demand sensors on dashboard — they should now show proportional values (0-100%) instead of binary 0/100%.

- [ ] **Step 2: Test one zone manually**

Set Tania target to 25°C temporarily. Watch:
1. VT demand rises (e.g., 40-60%)
2. Template number receives the value
3. ESP32 fans turn on at proportional speed
4. Set target back to 22.5°C, watch demand drop and fans slow/stop

- [ ] **Step 3: Verify schedule automations still work**

Check that the blueprint-based automations reference the correct entity IDs. The automation entity IDs (`automation.office_climate_schedule_2` etc.) should still target the same climate entity IDs.

- [ ] **Step 4: Monitor overnight cycle**

Watch the full cycle: comfort → eco (17:00) → frost (19:00) → preheat (07:30) → comfort (08:00). Verify:
- Fans stop when preset changes to eco/frost
- Fans start proportionally on preheat/comfort
- No overshooting
- Demand sensors reflect reality

---

## Summary of Changes

| What | Action |
|------|--------|
| `templates.yaml` | Add 7 template number entities (1 on/off, 4 dual cascade, 2 single) |
| `automations.yaml` | Remove `fancoil_speed_control_esphome` automation |
| `configuration.yaml` | Remove duplicate `input_boolean` block with dummy entities |
| HA UI | Delete 7 old VTs, create 7 new VTs as `thermostat_over_valve` |
| Dashboard | No changes needed (entity IDs preserved by naming) |
| Demand sensors | No changes needed (on_percent * 100 now shows real proportional values) |
