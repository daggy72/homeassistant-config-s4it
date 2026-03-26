# VT-over-Valve Restructure for Old Fancoils

> Design spec for converting old 3-speed fancoil VTs from `thermostat_over_switch` to `thermostat_over_valve`

**Date**: 2026-03-26
**Status**: Approved

## Problem

The old fancoil VTs use `thermostat_over_switch` with dummy `input_boolean` entities. This gives binary TPI output (on/off duty cycle) with `on_percent` always 0 or 1. The VT cannot output proportional demand, so a separate temperature-gap automation was built as a workaround. This workaround:

- Polls every 5 minutes (delayed response)
- Duplicates thermostat logic (gap calculation) that the VT should handle
- Produces demand sensors that don't reflect actual VT output
- Makes the dashboard misleading (shows 0% or 100% only)

Meanwhile, the new fancoils (Projects 1, Mensa) use `thermostat_over_valve` with template number entities, giving smooth 0-100% proportional output. This works well.

## Solution

Convert all 7 old fancoil VTs to `thermostat_over_valve`, each pointing at a new template number entity. The template number's `set_value` action translates the 0-100% demand into the appropriate hardware control.

## Architecture

```
VT (thermostat_over_valve)
  |
  v
Template Number (0-100%)
  |
  set_value action translates to hardware:
  |
  +-- Dual rooms: 6-step cascade to two ESP32 fans
  +-- Single rooms: 3-step to one ESP32 fan
  +-- Dagmar: on/off smart switch (temporary, until Shelly 0-10V arrives)
```

### Future-proof

When a room's old fancoil is replaced with a new stepless unit:
- Change only the template number's `set_value` action (from ESP32 relay to Shelly 0-10V brightness)
- VT config stays unchanged
- No automation changes needed

## Zones and Entities

### New Template Numbers (to create in templates.yaml)

| Template Number | Zone | Type | Underlying Fans | set_value Logic |
|----------------|------|------|-----------------|-----------------|
| `number.fancoil_dagmar` | Dagmar | Single (on/off) | `switch.smart_switch_...outlet` | value > 0 → on, else off |
| `number.fancoil_tania` | Tania | Dual | `fan.fancoil_09_fancoil` (wall), `fan.fancoil_10_fancoil` (window) | 6-step cascade |
| `number.fancoil_cs` | CS | Dual | `fan.fancoil_08_fancoil` (left), `fan.fancoil_07_fancoil` (right) | 6-step cascade |
| `number.fancoil_meeting` | Meeting | Dual | `fan.fancoil_05_fancoil` (left), `fan.fancoil_06_fancoil` (right) | 6-step cascade |
| `number.fancoil_openspace` | OpenSpace | Dual | `fan.fancoilcontroller_01_fancoil` (left), `fan.fancoil_02_fancoil` (right) | 6-step cascade |
| `number.fancoil_reception` | Reception | Single | `fan.fancoil_04_fancoil` | 3-step |
| `number.fancoil_entrance` | Entrance | Single | `fan.fancoil_03_fancoil` | 3-step |

### VT Reconfigurations (via HA UI)

| VT | Change | New Underlying Entity |
|----|--------|-----------------------|
| Fancoil Dagmar | `thermostat_over_switch` → `thermostat_over_valve` | `number.fancoil_dagmar` |
| Fancoil Tania | `thermostat_over_switch` → `thermostat_over_valve` | `number.fancoil_tania` |
| Fancoil CS | `thermostat_over_switch` → `thermostat_over_valve` | `number.fancoil_cs` |
| Fancoil Meeting | `thermostat_over_switch` → `thermostat_over_valve` | `number.fancoil_meeting` |
| Fancoil OpenSpace | `thermostat_over_switch` → `thermostat_over_valve` | `number.fancoil_openspace` |
| Fancoil Reception | `thermostat_over_switch` → `thermostat_over_valve` | `number.fancoil_reception` |
| Fancoil Entrance | `thermostat_over_switch` → `thermostat_over_valve` | `number.fancoil_entrance` |

## Speed Mapping Logic

### 6-Step Cascade (Dual Rooms)

The template number receives 0-100% from VT. The `set_value` action maps to two 3-speed fans:

| VT % | Step | Fan A (%) | Fan B (%) | Description |
|------|------|-----------|-----------|-------------|
| 0 | 0 | off | off | No demand |
| 1-17 | 1 | 33 (low) | off | Minimal |
| 18-33 | 2 | 33 (low) | 33 (low) | Both low |
| 34-50 | 3 | 67 (med) | 33 (low) | A med, B low |
| 51-67 | 4 | 67 (med) | 67 (med) | Both medium |
| 68-83 | 5 | 100 (high) | 67 (med) | A high, B med |
| 84-100 | 6 | 100 (high) | 100 (high) | Both full |

### 3-Step (Single Rooms)

| VT % | Fan (%) | Description |
|------|---------|-------------|
| 0 | off | No demand |
| 1-33 | 33 (low) | Low speed |
| 34-67 | 67 (med) | Medium speed |
| 68-100 | 100 (high) | High speed |

### Dagmar (Temporary On/Off)

| VT % | Action |
|------|--------|
| 0 | Switch off |
| > 0 | Switch on |

## State Reading

Each template number reads its state from the actual fan entities:
- Dual rooms: average of both fans' speed percentages, mapped back to 0-100 range
- Single rooms: fan speed percentage directly
- Dagmar: 100 if switch on, 0 if off

## What Gets Removed

1. **Automation**: `fancoil_speed_control_esphome` — no longer needed, logic moves to template numbers
2. **Entities**: `input_boolean.fancoil_tania`, `input_boolean.fancoil_cs`, `input_boolean.fancoil_meeting`, `input_boolean.fancoil_openspace`, `input_boolean.fancoil_reception`, `input_boolean.fancoil_entrance`, `input_boolean.fancoil_dagmar_dummy` — no longer needed as VT underlying entities

## What Stays Unchanged

- Climate schedule automations (blueprint-based presets)
- ESPHome fan entities and firmware (fancoil-base.yaml v1.2.0)
- Shelly 0-10V template numbers (Projects 1, Mensa)
- Fancoil Demand sensors (on_percent * 100 — now shows real proportional values)
- All temperature sensors
- Sun shade automations
- Seasonal mode toggle

## Implementation Order

1. Create 7 template number entities in `templates.yaml`
2. Reload templates, verify entities appear in HA
3. Reconfigure VTs one at a time via HA UI (switch type + underlying entity)
4. Test each zone: verify VT outputs proportional %, fans respond correctly
5. Remove `fancoil_speed_control_esphome` automation from `automations.yaml`
6. Remove dummy `input_boolean` entities from `configuration.yaml`
7. Reload automations
8. Monitor overnight cycle (frost → preheat → comfort → eco → frost)

## Success Criteria

- VT demand sensors show proportional values (not just 0/100%)
- Fans respond to VT demand within seconds (no 5-minute polling delay)
- Morning preheat: fans spin up proportionally as gap closes
- Rooms reach target without overshooting
- Dashboard accurately reflects what fans are doing
- Eco/frost transitions turn fans off immediately
