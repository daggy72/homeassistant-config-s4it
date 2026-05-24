# Climate Control — Canonical Reference

> Sales4Italy Cassano Magnago office. Last updated 2026-05-24 (first full summer with new fancoils).
> Source of truth for: zones, hardware, Versatile Thermostat configuration, automations, schedule, chiller management, sunscreens, and operational rules. If something here contradicts code, the code wins and this doc needs an update — please update inline.

## Table of contents

1. [System overview](#1-system-overview)
2. [Zones & building orientation](#2-zones--building-orientation)
3. [Hardware layer](#3-hardware-layer)
4. [Power routing — master switches](#4-power-routing--master-switches)
5. [Versatile Thermostat configuration](#5-versatile-thermostat-configuration)
6. [Climate season selector](#6-climate-season-selector)
7. [Automation chain (workday morning → night)](#7-automation-chain-workday-morning--night)
8. [Sunscreens — first line of defense against solar load](#8-sunscreens--first-line-of-defense-against-solar-load)
9. [Operational rules](#9-operational-rules)
10. [Known issues & defenses](#10-known-issues--defenses)
11. [Weather playbook](#11-weather-playbook)
12. [Learning loop — daily journal](#12-learning-loop--daily-journal)
13. [Maintenance, calibration & future work](#13-maintenance-calibration--future-work)

---

## 1. System overview

The building has **10 cooling zones**, each driven by a `Versatile Thermostat` (VT) custom integration entity in `thermostat_over_valve` mode. VTs write a percent-demand (0–100%) into a `number.*` template entity, which abstracts the actual fancoil hardware (Shelly 0–10V for stepless fancoils, ESP32 Athom 4CH relay boards for legacy 3-speed fans).

The control chain is:

```
input_select.climate_season  (off / winter / summer)
        │
        ▼
Seasonal Climate Mode Switch  (automation, fires on state change)
        │  sets hvac_mode + preset on all 10 VTs, opens chiller
        ▼
 Versatile Thermostat (×10)
        │  computes valve demand (TPI algorithm), writes 0–100%
        ▼
 number.fancoil_*_valve  (template)
        │  set_value translates % → hardware command
        ▼
   Shelly 0–10V  OR  ESP32 Athom 4CH (3-speed relays)
        │
        ▼
        Fans + valves
```

Parallel to fancoils:
- **Chiller** (`switch.shellypro4pm_ece334eaf568_switch_2`) provides cold water to ALL fancoils. Managed by dedicated chiller automations, not directly by season switch.
- **Sunscreens** (Mensa, Meeting Room, CS) block direct solar gain before it ever enters a room — see [§8](#8-sunscreens--first-line-of-defense-against-solar-load).
- **Schedule blueprints** fire workday presets (preheat 07:30, comfort 08:00, eco 17:00, frost 19:00).
- **Summer Dynamic Temperature Adjustment** (every 30 min in summer) pushes outdoor-scaled comfort setpoints into VTs in comfort preset.

Configuration locations:
- VT configuration: `homeassistant/config/.storage/core.config_entries` (not in git — managed via HA UI)
- Template entities (`number.fancoil_*_valve`): `homeassistant/config/templates.yaml`
- Automations: `homeassistant/config/automations.yaml`
- Schedule blueprint: `homeassistant/config/blueprints/automation/custom/office_climate_schedule.yaml`
- Intelligent sun-shade blueprint: `homeassistant/config/blueprints/automation/custom/intelligent_sun_shade.yaml`
- Dashboards: `homeassistant/config/dashboards/climate.yaml`

---

## 2. Zones & building orientation

| Zone | VT entity | Orientation | Solar window | Notes |
|---|---|---|---|---|
| Office Dagmar | `climate.fancoil_dagmar` | West | 13:00–19:00 | Glass-wrapped west. No shade. |
| Office Accounting (Tania) | `climate.fancoil_tania` | West | 13:00–19:00 | No shade. |
| Projects 1 | `climate.projects_1` | South + West | 10:00–19:00 | Glass-wrapped S+W. Highest solar load. No shade. |
| Projects 2 | `climate.projects_2` | South + West | 10:00–19:00 | Glass-wrapped S+W. Highest solar load. No shade. |
| Customer Service (CS) | `climate.fancoil_cs` | East | 07:00–11:00 | Shade exists (Tenda CS). Legacy time-based automation. |
| Meeting Room | `climate.fancoil_meeting` | East | 07:00–11:00 | Shade exists (Tenda Meeting). Intelligent shade blueprint. Temp sensor currently dead — needs replacement. |
| Open Space | `climate.fancoil_openspace` | Internal | n/a | Shared air with Meeting, CS, Entrance. |
| Entrance Main | `climate.fancoil_entrance` | Internal | n/a | Single-fan zone. |
| Reception | `climate.fancoil_reception` | North | n/a | Single-fan zone, poor insulation per blueprint config. |
| Mensa | `climate.climate_mensa` | South | 10:00–14:00 | Shade exists (Tende Mensa). Intelligent shade blueprint. |

**Critical insight on orientation**: cooling timing follows solar load timing. East rooms heat up first (07:00–11:00), South rooms midday (10:00–14:00), West rooms afternoon (13:00–19:00). The Projects rooms sit on the south-west corner with full glass on two sides — they take the full midday + afternoon solar hit and have no shade defense.

---

## 3. Hardware layer

### Fancoil control

| Zone | Template number | Underlying hardware |
|---|---|---|
| Mensa | `number.fancoil_mensa_1` (display: "Fancoil Mensa") | Shelly 0-10V `light.shellypro0110pm_8813bfe0fc18` ("Fancoils-Mensa") — both ceiling fancoils wired electrically in parallel on one channel |
| Office Dagmar | `number.fancoil_dagmar` | Shelly 0-10V `light.shellypro0110pm_8813bfd9525c` ("Fancoils-Dagmar") — both fancoils in parallel (rewired 2026-05-23, replaced old binary smart plug) |
| Projects 1 | `number.fancoil_projects_1` | Shelly 0-10V `light.shellypro0110pm_8813bfd95330` |
| Projects 2 | `number.fancoil_projects_2` | Shelly 0-10V `light.shellypro0110pm_8813bfe0e42c` |
| Tania | `number.fancoil_tania_valve` | ESP32 Athom 4CH (3-speed, dual fans → cascaded 6-speed mapping) |
| CS | `number.fancoil_cs_valve` | ESP32 Athom 4CH (3-speed, dual fans → 6-speed) |
| Meeting | `number.fancoil_meeting_valve` | ESP32 Athom 4CH (3-speed, dual fans → 6-speed) |
| OpenSpace | `number.fancoil_openspace_valve` | ESP32 Athom 4CH (3-speed, dual fans → 6-speed) |
| Reception | `number.fancoil_reception_valve` | ESP32 Athom 4CH (3-speed, single fan, wider low-speed band) |
| Entrance | `number.fancoil_entrance_valve` | ESP32 Athom 4CH (3-speed, single fan) |

Shelly 0-10V brightness maps to 0-10V analog signal that drives stepless fancoils. ESP32 Athom 4CH relays control 3-speed fans with on/off-per-speed relays; templates implement staged turn-on (off → low → target speed) to avoid relay/motor stress.

### Temperature sensors

| Zone | Sensor entity | Type |
|---|---|---|
| Mensa | `sensor.shellywalldisplay_00a90b53f68a_temperature` | Shelly Wall Display |
| Office Dagmar | `sensor.up_sense_temperature_2` (a.k.a. `MT Dagmar - UP Sense Temperature`) | UP Sense |
| Tania | UP Sense (`MT Tania - UP Sense`) | UP Sense |
| CS | UP Sense (`CC - UP Sense`) | UP Sense |
| Meeting | `MT meeting room - UP Sense Temperature` | UP Sense — **currently dead, needs replacement** |
| OpenSpace | `OpenSpace - UP Sense Temperature` | UP Sense |
| Reception | `Reception UP Sense Temperature` | UP Sense |
| Projects 1, 2, Entrance | (various, see VT config) | UP Sense / Shelly DeskDisplay |
| Outdoor | `sensor.outdoor_temperature` | (driving dynamic comfort) |

EMA (exponential moving average) variants exist per VT zone (e.g. `sensor.fancoil_dagmar_ema_temperature`) — useful for monitoring but lag the raw sensor by several minutes.

### Chiller

- Entity: `switch.shellypro4pm_ece334eaf568_switch_2`, alias **Chiller**, area WH6.
- Physical: industrial chiller providing cold water to all fancoils via building piping loop.
- **The Shelly Pro 4PM at IP 10.0.11.42 also hosts the `Fancoils CS` master switch — single point of failure for two critical zones.** See [§10](#10-known-issues--defenses).

---

## 4. Power routing — master switches

The old 3-speed ESP32 fancoil controllers are powered through Shelly relay switches. When the master is OFF, the controller has no power → fancoils appear `unavailable` in HA, and any VT cool demand will fail silently (fan never spins).

| Master switch | Powers | On which Shelly |
|---|---|---|
| `switch.fancoils_cs` ("Fancoils CS") | fancoil CS left + right | **same Shelly as Chiller** (`shellypro4pm-ece334eaf568`, IP 10.0.11.42) — SPOF |
| `switch.fancoils_os_meeting` ("Fancoils OS & Meeting") | fancoil OpenSpace left/right + fancoil MeetingRoom left/right | (separate Shelly Pro 4PM) |
| `switch.fancoils_tania` ("Fancoils Tania") | fancoil Tania wall + window | (separate Shelly Pro 4PM) |

Reception and Entrance fancoils have **no master switch** — always powered.

Office Dagmar / Mensa / Projects fancoils (Shelly 0-10V controlled) have **no master switch** either — the Shelly itself is always powered, fancoils are powered via the Shelly's relay/output.

**Operational rule**: Before any summer engagement, confirm all 3 master switches are ON. The summer engagement automations DO NOT currently auto-power these masters — they assume the masters are on. Add this to a season-summer-startup checklist, or eventually fold it into the Seasonal Mode Switch automation.

---

## 5. Versatile Thermostat configuration

Each VT entity is configured via HA UI (Settings → Devices & Services → Versatile Thermostat). Config is persisted in `.storage/core.config_entries` (not in git).

### Mode

All 10 zone VTs use `thermostat_type: thermostat_over_valve`. VT computes a TPI (proportional-integral) demand 0–100% and writes it to its underlying `number.fancoil_*_valve` entity.

### Underlying entity

Each VT has exactly one underlying entity: the template `number.fancoil_*_valve` listed in [§3](#3-hardware-layer). VT does NOT talk to fans/Shellies directly.

### Central configuration

There is one VT entry of type `thermostat_central_config` named "Central configuration". It holds defaults inherited by VTs that opt in via flags like `use_advanced_central_config`, `use_lock_central_config`, `use_presets_central_config`, etc.

Current central settings (excerpt):

| Setting | Value | Meaning |
|---|---|---|
| `external_temperature_sensor_entity_id` | `sensor.outdoor_temperature` | Reference outdoor temperature |
| `temp_min` / `temp_max` | 15.0 / 30.0 | Allowed range for any preset (clamps) |
| `tpi_coef_int` / `tpi_coef_ext` | 0.6 / 0.01 | TPI gain (internal / external delta) |
| `safety_default_on_percent` | 0.1 | Default 10% demand if safety triggered |
| `safety_delay_min` | 60 | Minutes before triggering safety mode |

### Cool-mode presets

⚠️ **Currently unconfigured** — neither central nor per-VT cool-mode preset temperatures are set. This causes the 0 °C frost bug (see [§10](#10-known-issues--defenses)). Until configured, only the `comfort` preset is safe to be in during summer (the `Summer Dynamic Temperature Adjustment` automation pushes a sane setpoint).

Recommended defaults to configure (per VT, or in Central for VTs with `use_presets_central_config: true`):

| Preset | Office target | Common target | Note |
|---|---|---|---|
| Comfort | 25.0 °C | 26.0 °C | Will be overridden by dynamic temp sensor in summer |
| Eco | 28.0 °C | 28.0 °C | Evening / unoccupied buffer |
| Frost | 30.0 °C | 30.0 °C | Effectively "no cooling" — at temp_max |
| Boost | 22.0 °C | 23.0 °C | Aggressive cooling for short bursts |

VTs inheriting from Central via `use_presets_central_config: true`: Mensa, OpenSpace, Entrance.

VTs with their own presets (`use_presets_central_config: false`, must be configured individually): Projects 1, Projects 2, Office Dagmar, Tania, CS, Meeting, Reception.

### Per-VT settings of note

| VT | Notable |
|---|---|
| Office Dagmar | `cycle_min: 10`, `auto_regulation_dtemp: 10.0` — legacy values from binary-smart-plug era. Now overkill; consider reducing to `5` / `1.0` for smoother modulation. |
| Mensa, OpenSpace, Entrance | Inherit presets from Central |
| Meeting, Reception | `motion_preset: comfort`, `no_motion_preset: eco` — currently not actively used (no motion sensors wired); harmless |
| Reception | Wider low-speed band in template (poor insulation, single fan) |

---

## 6. Climate season selector

`input_select.climate_season` has three states: `off`, `winter`, `summer`. Persistent across HA restarts.

| State | Effect |
|---|---|
| `off` | All VTs off, chiller off (if min-cycle satisfied). No cooling, no heating. |
| `winter` | All VTs to `heat`, chiller off. Comfort preset. Schedule blueprint manages presets per workday. |
| `summer` | All VTs to `cool`, chiller managed by dedicated automations. Comfort preset on transition. Schedule blueprint manages presets per workday. Dynamic temp sensor adjusts comfort setpoints every 30 min. |

State change is the only trigger for `Seasonal Climate Mode Switch` — manual click or automation. Set it to `summer` the evening before the season (or first cool morning); leave it on `summer` for the whole season.

---

## 7. Automation chain (workday morning → night)

In firing order on a summer workday:

| Time | Automation | What it does |
|---|---|---|
| **on `input_select.climate_season` state change** | `Seasonal Climate Mode Switch` | Sets all VTs to off → wait 5 s → set to target mode (heat/cool/off) → set chiller (with 10-min min-cycle guard) → wait 5 s → force comfort preset. **This automation is the safety net that kills the 0 °C bug on every transition.** |
| **HA startup / 07:00 workday** | `Morning VT Alignment` | Ensures every VT's hvac_mode matches the current season selector and forces comfort preset. Recovers from manual VT-off overrides, weekend HA reboots, etc. Does NOT touch chiller. |
| **06:30 workday** (summer) | `Chiller Pre-start` | Turns chiller ON, respecting 10-min min-cycle. Pre-charges piping with cold water so by 07:30 (precool) or 08:00 (comfort) cold water is already flowing. Measured chiller→useful-cooling delay: ~10–15 min. |
| **07:30 workday** | `Office Climate Schedule` (preheat trigger) | Sets `comfort` preset on Office VTs (Dagmar, Tania, Projects 1, CS, Reception) and Common VTs (OpenSpace, Entrance, Mensa, Projects 2). In summer this is effectively "precool". |
| **08:00 workday** | Schedule blueprint (comfort trigger) | Sets `comfort` preset again (redundant if preheat already fired). Meeting Room schedule fires here too. |
| **every 30 min**, summer mode, comfort preset only | `Summer Dynamic Temperature Adjustment` | Pushes `sensor.summer_comfort_office` (24–27 °C scaled by outdoor temp) into Office VTs, and `sensor.summer_comfort_common` (25–28 °C) into Common VTs. Comfort target tracks outdoor temp to avoid cold shock. |
| **12:00 workday** | `Meeting Room Boost (12-14)` | Boosts Meeting Room to 22 °C target during lunch. Fires `boost` preset. |
| **14:00 workday** | Same automation, end of boost | Returns Meeting Room to `comfort`. |
| **17:00** | Schedule blueprint (eco trigger) | Sets `eco` preset on all zones. **⚠️ Without cool-mode eco preset configured, this triggers the 0 °C bug. Configure presets before relying on this.** |
| **19:00** | Schedule blueprint (frost trigger) | Sets `frost` preset. Same caveat as eco. |
| **19:30** (summer) | `Chiller End-of-day Off` | Turns chiller OFF if (a) summer, (b) chiller has been on ≥ 10 min, (c) no VT currently `hvac_action: cooling`. |
| **00:00** non-workday | Schedule blueprint (midnight trigger) | Sets frost preset on non-workdays (weekend / holiday). |

Other related automations (always-on):

- `boost_auto_revert` — when any VT enters `boost` preset, converts to a 60-min timed preset and reverts when target reached or 60 min elapses. Defends against sticky-boost.
- `Kitchen Appliances` — 08:00 on / 19:00 off (Mon–Sat) for kitchen smart plugs. Not climate.
- `Auto Unlock Wallbox` — geofence-driven. Not climate.

---

## 8. Sunscreens — first line of defense against solar load

**Shades block heat from entering a room. AC removes heat after it's already inside. Shades are vastly more efficient per joule moved.** A well-timed shade close can prevent 30–40 % of summer cooling demand on a sunny day. They are the cheapest cooling lever the building has.

The building has 3 controllable shades:

| Cover entity | Display | Room | Orientation | Sun window |
|---|---|---|---|---|
| `cover.shellypro2cover_2cbcbbb1ff9c_cover_0` | Tende Mensa | Mensa | SSW | 10:00–14:00 (peak ~12:00) |
| `cover.shellypro2cover_34987a47c9b0_cover_0` | Tenda Meeting | Meeting Room | ESE | 07:00–11:00 (peak ~09:00) |
| `cover.shellypro2cover_34987a47c9b0_cover_1` | Tenda CS | CS | ESE | 08:00–11:00 (peak ~09:00) |

(There's also `shellypro2cover-2cbcbbb1ff9c Cover 1` — unnamed, second channel of the Mensa shade Shelly. Currently unused / unintegrated.)

### Mensa and Meeting Room — intelligent shade blueprint

Both use `blueprints/automation/custom/intelligent_sun_shade.yaml` (instantiated as `sun_shade_mensa` and `sun_shade_meeting_room` in `automations.yaml`). Decision model is **hybrid predictive + reactive**:

- **Predictive close**: at the start of the sun window (e.g. 08:00 ESE for Meeting), if today's forecast max ≥ threshold AND clouds < threshold, lower to a target position (e.g. 30 %).
- **Reactive override**: mid-window, if room temperature crosses a cap OR rises faster than a rate threshold sustained over 30 min, close even if the predictive condition wasn't met.
- **Re-open**: sun moves out of window, clouds roll in (cloud-coverage threshold), room cools AND clouds, or end of window.
- **Manual override**: if a user physically moves the cover, a 30-min grace timer suppresses automation actions. Re-evaluate when timer expires.

All thresholds are externalized as `input_number.*` helpers, tunable from the HA UI. A nightly LLM-driven evaluator (separate, remote, optional) reviews recent days and proposes threshold tweaks via Telegram.

See `docs/superpowers/specs/2026-04-07-intelligent-sun-shade-design.md` for full design.

### CS — legacy time-based automation

`cs_sun_shade` in `automations.yaml`. Simpler model:

- Trigger at 08:00 OR when cloud coverage drops below 50 % during 08:00–11:00 → lower CS shade to 30 % if currently > 50 % open and sun is above horizon.
- Trigger at 11:00 OR when cloud coverage rises above 70 % → raise CS shade.
- Only fires on workdays.

**Migration candidate**: move CS to the intelligent_sun_shade blueprint for consistency (same predictive + reactive + manual-override logic as Meeting). The blueprint is parameterized — a new instance with CS's azimuth (ESE, similar to Meeting) and threshold helpers is a ~15-min config change. Not blocking, but recommended for the 2026 summer based on observed behavior.

### Shade ↔ climate interaction

The shades and the AC are **complementary, not redundant**:

1. **Predictive shade close** reduces solar gain before AC has to respond. Cuts peak demand.
2. **Reactive shade close** kicks in when shade-only is insufficient or the predictive threshold was wrong — backstop.
3. **AC** removes whatever heat got through despite the shade. With shades doing their job, AC operates at lower demand → lower noise, less energy, less chiller load.

On clear hot days with shades closed predictively, the AC may run at 50–70 % demand instead of 100 %. On overcast or shade-failed days the AC takes the full load. The journal (§12) will tell us actual savings.

**No west-facing shades exist** — Projects 1+2, Dagmar, Tania take the afternoon sun unmitigated. This is the single biggest passive-cooling gap in the building. Future work: external blinds, awnings, or solar film on west glazing.

### Operational rule for shades

Always **respect user overrides**. If someone manually opens a shade, the automation must back off (30-min grace). Annoying users with auto-closing shades when they want light is worse than the energy saved.

---

## 9. Operational rules

1. **Chiller minimum cycle = 10 min** between any ON↔OFF transition. Hard rule, no exceptions. Compressor + circulation pump damage risk. Every automation that calls `switch.turn_on`/`turn_off` on the chiller must check `last_changed` and refuse if < 600 s elapsed.
2. **Cold-water pre-charge = ~10–15 min** (measured 2026-05-24 on a mild 23 °C outdoor day). Hotter days may need longer (warmer starting pipe water). `Chiller Pre-start` at 06:30 gives a 60-min margin for 07:30 first cooling demand.
3. **Master power switches must be ON before summer engagement.** `Fancoils CS`, `Fancoils OS & Meeting`, `Fancoils Tania`. Otherwise the ESP32 fancoils stay unavailable and cool demand is silently dropped.
4. **One single chiller cycle per workday.** Chiller on at 06:30, off at 19:30. No on/off churn during the day even if demand is intermittent — the cost of fluttering the chiller is far higher than the cost of running it idle.
5. **Weekend default: chiller off, all VTs off.** Optional weekend intervention if Sat/Sun morning indoor ≥ 28 °C AND forecast is warm/heatwave — see [§11](#11-weather-playbook).
6. **Respect user manual overrides on shades** (30-min grace before automation re-engages).
7. **Schedule lives in HA UI for VT presets**, in YAML for everything else. Document changes inline (this file).

---

## 10. Known issues & defenses

### 0 °C frost bug

**Symptom**: switching to summer mode briefly (or persistently, depending on preset) shows VT target = 0 °C, demand = 100 %.

**Root cause**: cool-mode preset temperatures are unconfigured in VT (neither central nor per-VT). When VT enters cool mode with any preset other than `comfort` (boost, eco, frost), the integration falls back to 0 °C as a safety default.

**Defenses in place**:

1. `Seasonal Climate Mode Switch` forces `comfort` preset after every hvac_mode transition. Window where 0 °C is visible is reduced from "permanent" to "a few ms gap between service calls".
2. `Morning VT Alignment` (07:00 workday) forces comfort preset again.
3. `Summer Dynamic Temperature Adjustment` (every 30 min, comfort preset only) writes a sane setpoint (24–28 °C scaled by outdoor).

**Defenses still required**:

- **Configure cool-mode preset temperatures per VT** (§5). Until done, the 17:00 eco transition and 19:00 frost transition will RECREATE the bug because the schedule blueprint directly calls `set_preset_mode: eco` / `frost` without going through the protected Seasonal Mode Switch path.

### WH6 Shelly (chiller + Fancoils CS) intermittent drop

**Symptom**: `switch.Chiller` and `switch.Fancoils_CS` go `unavailable` in HA despite UniFi seeing the device.

**Observed**: 2026-05-24 ~09:18, Shelly went unavailable ~3 min after chiller turn-on. Could be coincidence (Shellies do this) or relay-load brown-out / Wi-Fi drop. Recovered by cycling the UniFi LAN port the Shelly is on.

**Impact**: when unreachable, chiller cannot be commanded AND CS fancoils are powerless. Two critical zones bricked simultaneously.

**Mitigations** (in order of effort):
1. **Now**: keep an eye on this Shelly. If it drops again on chiller engage, escalate to hardware investigation.
2. **Short term**: separate the Fancoils CS master onto a different Shelly (any spare Pro 4PM output). Removes the SPOF.
3. **Long term**: move this Shelly to PoE Ethernet (eliminates Wi-Fi flakiness entirely). Shelly Pro 4PM supports PoE.

### VT off-mode fights manual ESP32 fan control

**Symptom**: manually turning on a `fan.fancoil_XX_fancoil` entity while its parent VT is `hvac_mode: off` results in the fan turning off again within ~5–10 min.

**Cause**: VT in `over_valve` off-mode periodically writes `0` to its underlying `number.fancoil_*_valve` (every `cycle_min`). The template's `set_value(0)` runs the `else` branch which calls `fan.turn_off` on both physical fans.

**Workaround for testing**: temporarily disable the VT entity in HA UI (Settings → Devices & Services → VT → ⋮ → Disable), or use the Shelly 0-10V path (Office Dagmar, Mensa, Projects) which doesn't have this fight because the template just mirrors brightness.

**For production**: never matter — VTs should drive fans, not us manually.

### Meeting Room temp sensor dead

`MT meeting room - UP Sense Temperature` is `unavailable`. As a result `climate.fancoil_meeting` has no `current_temperature` and cannot regulate properly. The Meeting Room Boost (12:00–14:00) automation will fire but VT cannot decide demand without a sensor.

**Action**: replace the UP Sense sensor in the Meeting Room.

---

## 11. Weather playbook

Day classification from `weather.forecast_home` + `sensor.outdoor_temperature`:

| Class | Forecast max | Cloud cover | Strategy |
|---|---|---|---|
| Cool | < 24 °C | any | No cooling. Chiller off all day. Shades may still close intelligently. |
| Medium | 24–28 °C | mostly cloudy | Standard schedule. Chiller on 06:30. Comfort 25–26 °C office. |
| Warm | 28–32 °C | clear | Standard + deeper pre-cool. Chiller 06:00. Comfort 24–25 °C office. Close east shades 08:00–11:00 predictively, south from 10:30. |
| Heat wave | > 32 °C OR ≥ 30 °C × 3+ consecutive days | clear | Chiller 05:30. Pre-cool to comfort − 1 °C. Aggressive shade. Consider weekend light-cooling. Engage west zones an hour earlier than schedule. |

**Forecast-driven automations (planned, not yet built)**:

- **Tomorrow's class** (daily 20:30): read forecast, set `input_text.tomorrow_climate_class`.
- **Chiller pre-start time** scales with class (heatwave 05:30, warm 06:00, medium 06:30, cool: skip). Today's chiller pre-start automation is hard-coded to 06:30 — refine once we have a few days of journal data.
- **Weekend light-cooling check** (Sat/Sun 09:30): if indoor ≥ 28 °C AND class warm+, run a 2–3 h light cooling pass (chiller + cool mode + comfort+2 °C target).
- **Heat-wave evening pre-cool** (21:00 if next-day = heatwave): deep pre-cool to comfort − 1 °C until 23:00. Uses cheap night electricity if applicable.

All forecast automations must respect [§9.1](#9-operational-rules) (10-min chiller min-cycle).

---

## 12. Learning loop — daily journal

The system is in its first summer (2026). Strategy will be refined as data accumulates.

**Journal location**: `~/.claude/projects/-Users-dagmar-DEV-DOMOTICA/memory/climate-weather-playbook.md` (bottom of file). Auto-loaded into Claude Code sessions for context. Optionally mirrored to an Obsidian note in the Mnemo vault for richer formatting.

**Daily entry format**:

```
YYYY-MM-DD | class | forecast_max | outdoor_max_actual | indoor_peak_by_zone | comfort_feedback | notes
```

Append at the end of each workday. The data feeds:
- Threshold tuning for the weather playbook (e.g. "we set heat-wave at 32 °C but the building struggled at 30 °C")
- Identification of zone-specific issues ("Projects 2 always peaks 28 °C, regardless of class — needs west shade")
- Year-over-year comparison so 2027 starts calibrated
- Optional remote LLM evaluator (separate process) for shade-threshold tuning

---

## 13. Maintenance, calibration & future work

### Calibration checklist (do at least once per summer)

- [ ] **Configure cool-mode VT presets** (Comfort / Eco / Frost / Boost) for all 7 VTs not using central. ~10 min in HA UI. **Highest priority.**
- [ ] Confirm `Office Dagmar` VT settings (cycle_min: 5, auto_regulation_dtemp: 1.0) are reduced from the legacy binary-plug defaults (10 / 10.0).
- [ ] Replace Meeting Room UP Sense temperature sensor.
- [ ] Verify all master switches (`Fancoils CS`, `Fancoils OS & Meeting`, `Fancoils Tania`) are ON before first summer engagement.
- [ ] Walk-through after first hot day: any zone consistently above comfort? Adjust shade thresholds, comfort temp, or schedule timing.

### Future work / known gaps

- **West-facing shades** (Dagmar, Tania, Projects 1, Projects 2). Highest passive-cooling gap. Options: external blinds, awnings, solar film on glazing.
- **CS shade migration to intelligent_sun_shade blueprint** (parity with Meeting / Mensa). ~15 min config change.
- **Forecast classifier automations** ([§11](#11-weather-playbook)). Build after a few days of journal data.
- **Move chiller + CS master off the same Shelly**. Separate `Fancoils CS` to a different Shelly Pro 4PM output. Removes the WH6 SPOF.
- **PoE/Ethernet for the chiller Shelly** (eliminates Wi-Fi flakiness root cause).
- **Occupancy-aware eco preset** — currently Meeting and CS stay at comfort even when empty. With a presence sensor, drop to eco when empty for ≥ 30 min. Connected-air-mass concern (§intro) limits how much we can drift before OpenSpace suffers.
- **Mensa shade Shelly Cover 1** — second channel unused. Possibly a second shade not yet wired/named.
- **Replace `cs_sun_shade` legacy automation** with intelligent blueprint instance (see above).

### Where to learn more

- VT integration (Versatile Thermostat): https://github.com/jmcollin78/versatile_thermostat — `over_valve` mode docs
- Intelligent shade design: `docs/superpowers/specs/2026-04-07-intelligent-sun-shade-design.md`
- VT-over-valve restructure design: `docs/superpowers/specs/2026-03-26-vt-over-valve-restructure-design.md`
- This building's project CLAUDE.md: `CLAUDE.md` (root of this repo)
- Cassano building HVAC memory (auto-loaded in Claude Code sessions): `~/.claude/projects/-Users-dagmar-DEV-DOMOTICA/memory/climate-*.md`
