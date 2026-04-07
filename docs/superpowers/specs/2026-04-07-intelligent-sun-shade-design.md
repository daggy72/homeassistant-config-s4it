# Intelligent Sun Shade with Nightly Evaluator

> Adaptive sun-shade automation for Meeting Room and Mensa, with a remote-scheduled LLM-driven nightly evaluator that proposes threshold tweaks via Telegram.

**Date**: 2026-04-07
**Status**: Approved
**Scope**: `homeassistant/` + new remote triggers + new `docs/sun-shade-eval/` output directory

## Problem

The existing sun-shade automations (`cs_sun_shade`, `mensa_sun_shade` in `homeassistant/config/automations.yaml`) are open-loop: they trigger purely on sun azimuth + cloud coverage and close the cover to 30% on sunny mornings / afternoons. They have no awareness of:

1. Whether today's forecast predicts enough outdoor heat to warrant closing
2. What the actual room temperature is doing in real time
3. Whether the user manually re-opened the shade (signal that the automation is too aggressive)
4. Whether the threshold values are still well-tuned after weeks of use

The Meeting Room has no shade automation at all, despite having a cover entity (`cover.shellypro2cover_34987a47c9b0_cover_0` labeled "Tenda Meeting" in `dashboards/climate.yaml`) on the same facade as CS.

Evidence this matters: on April 7 2026 (recorded in the Temp Graph shared during brainstorming), the Meeting Room rose from ~23°C at 08:00 to ~26°C at 12:00 while outdoor went from ~12°C to ~24°C. The shade was never lowered. Room spent more than an hour above comfort threshold.

## Solution overview

Two independent subsystems that communicate only via the git repo and the HA REST API:

### Subsystem 1 — HA runtime (self-sufficient)

A blueprint `intelligent_sun_shade.yaml` instantiated twice (Meeting Room ESE, Mensa SSW). It replaces the existing `mensa_sun_shade` (removed) and adds Meeting Room (new). The legacy `cs_sun_shade` is left untouched — out of scope, future migration candidate.

Decision logic is **hybrid**:
- **Predictive**: close at sun-window start if today's forecast max ≥ threshold AND clouds < threshold
- **Reactive override**: close mid-window if actual room temperature crosses a cap OR rises faster than a rate threshold sustained over 30 min
- **Re-open**: sun moves out of window, clouds roll in, room cools + clouds, or end of window
- **Manual override**: if a user moves the cover manually, start a 30-minute grace timer during which the automation refuses to act; re-evaluate when the timer expires

All thresholds are externalized as `input_number.*` helpers with bounded min/max, so they can be tuned from the HA UI and by the evaluator.

The HA side is **fully self-sufficient**. If the evaluator never runs again, the automations keep working with whatever values are in the helpers. The evaluator is a tuning loop, not a critical path.

### Subsystem 2 — Nightly evaluator (remote, LLM-driven)

Two `RemoteTrigger` scheduled agents running in Anthropic's cloud, checking out this repo from GitHub and using the Claude Code session to analyze HA data:

1. **Nightly analysis** (`0 21 * * *` UTC = 23:00 CEST / 22:00 CET): pulls today's history via HA REST API, compares forecast vs actual, detects manual overrides, writes a report to `docs/sun-shade-eval/YYYY-MM-DD.md`, and — if a threshold change is warranted — appends a pending entry to `homeassistant/eval-state.json` and sends a Telegram message with the proposed diff and a unique token (`EVAL-YYYY-MM-DD-XXXX`).

2. **Morning apply** (`0 5 * * *` UTC = 07:00 CEST / 06:00 CET): polls Telegram `getUpdates`, scans for `apply TOKEN` / `ignore TOKEN` replies, and for each approved change edits the YAML default AND calls `input_number.set_value` on the running HA to apply immediately. Expires pending entries older than 24h.

The evaluator never edits automation logic, only the `input_number` values in YAML within the bounded min/max. Every change is a git commit with the reasoning in the message body.

## Decisions (locked)

| # | Decision | Value |
|---|---|---|
| 1 | Scope — rooms | Meeting Room (new) + Mensa (replace existing) |
| 2 | Out of scope | CS (existing `cs_sun_shade` untouched), other rooms |
| 3 | Architecture | Single blueprint + 2 instantiations |
| 4 | Meeting Room orientation | Azimuth 90°–150°, elevation > 15° (ESE, roughly 08:00–11:00) |
| 5 | Mensa orientation | Azimuth 170°–240°, elevation > 15° (SSW afternoon, same as existing) |
| 6 | Decision philosophy | Hybrid: predictive + reactive override |
| 7 | Activation gate | `input_select.climate_season != winter` |
| 8 | Predictive trigger | `forecast outdoor max ≥ 22°C` AND `cloud_coverage < 50%` |
| 9 | Reactive override | `room_temp ≥ 25°C` OR `rate ≥ 0.6°C/h` sustained 30 min (with `for: 5m` debounce on trigger) |
| 10 | Re-open | `room < 23°C AND clouds > 50%` OR `clouds > 70%` OR sun out of window |
| 11 | Position values | closed = 30%, open = 100% |
| 12 | Manual override behavior | 30-min grace timer, then re-assert if close conditions still true |
| 13 | Thresholds scope | Global (shared between both rooms for v1); split later if evaluator data shows divergent needs |
| 14 | Nightly evaluator | Remote trigger via `schedule` skill, model `claude-sonnet-4-6` |
| 15 | Approval pattern | Pattern B — two triggers (nightly propose + morning apply) |
| 16 | Nightly trigger time | `0 21 * * *` UTC (= 23:00 CEST summer / 22:00 CET winter) |
| 17 | Morning trigger time | `0 5 * * *` UTC (= 07:00 CEST summer / 06:00 CET winter) |
| 18 | Delivery channel | Telegram via `curl` to Bot API (no MCP plugin needed in remote agent) |
| 19 | Data access | HA REST API with long-lived access token embedded in trigger prompt |
| 20 | State file | `homeassistant/eval-state.json` (no secrets, just pending change metadata) |
| 21 | Phased rollout | HA side runs 1 week before enabling evaluator triggers |
| 22 | Dashboard panel | Add threshold/override panel to `dashboards/climate.yaml` |

## Architecture diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     HA RUNTIME (always-on, on-prem)                 │
│                                                                     │
│  Blueprint: intelligent_sun_shade.yaml                              │
│  Instantiated:  Meeting Room (az 90–150)                            │
│                 Mensa        (az 170–240)                           │
│                                                                     │
│  Reads:  input_number.shade_* (9 tunable thresholds + 1 forecast)   │
│          timer.shade_*_manual_grace                                 │
│          sensor.<room>_temp_rate                                    │
│          climate.<room>_climate.current_temperature                 │
│          weather.forecast_home (cloud_coverage, forecast)           │
│          sun.sun (azimuth, elevation)                               │
│          input_select.climate_season                                │
│                                                                     │
│  Writes: cover.set_cover_position                                   │
│          timer.start (grace)                                        │
│          counter.<room>_manual_override_count                       │
│          input_datetime.<room>_predictive_close_at                  │
│          input_datetime.<room>_reactive_close_at                    │
│          input_number.<room>_forecast_max_at_window_start           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS REST API
                              │ Authorization: Bearer <HA_LLT>
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              EVALUATOR (remote, Anthropic cloud CCR)                │
│                                                                     │
│  Repo: git clone https://github.com/daggy72/homeassistant-config-s4it
│  Tools: Bash, Read, Write, Edit, Glob, Grep                         │
│  MCP:   HomeAssistant CM1 (fallback for live state)                 │
│  Model: claude-sonnet-4-6                                           │
│                                                                     │
│  Trigger #1: sun-shade-evaluator-nightly  (0 21 * * *)              │
│    1. Clone repo                                                    │
│    2. GET /api/states/input_number.shade_*                          │
│    3. GET /api/states/input_number.<room>_forecast_max_at_window_start
│    4. GET /api/states/input_datetime.<room>_*_close_at              │
│    5. GET /api/states/counter.<room>_manual_override_count          │
│    6. GET /api/history/period/<today_midnight> (all relevant ents)  │
│    7. Read homeassistant/eval-state.json                            │
│    8. Analyze → verdict per room                                    │
│    9. Write docs/sun-shade-eval/YYYY-MM-DD.md                       │
│    10. If change warranted:                                         │
│          - append pending entry to eval-state.json                  │
│          - curl Telegram Bot API with diff + token                  │
│    11. Expire entries older than 24h                                │
│    12. git add / commit / push                                      │
│                                                                     │
│  Trigger #2: sun-shade-evaluator-morning  (0 5 * * *)               │
│    1. Clone repo                                                    │
│    2. Read eval-state.json                                          │
│    3. curl Telegram getUpdates?offset=<last_update_id+1>            │
│    4. Scan for "apply|ignore EVAL-YYYY-MM-DD-XXXX"                  │
│    5. For each "apply" match:                                       │
│          - edit input_number default in YAML                        │
│          - POST /api/services/input_number/set_value                │
│          - remove pending entry                                     │
│          - curl Telegram confirmation                               │
│    6. For each "ignore" match: remove entry + confirm               │
│    7. Expire 24h-old pending entries                                │
│    8. Update last_telegram_update_id                                │
│    9. git add / commit / push                                       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                        Telegram (push notifications + approval replies)
                        NAS (manual git pull at user's convenience)
```

## Component 1 — Blueprint `intelligent_sun_shade.yaml`

### Location

`homeassistant/config/blueprints/automation/custom/intelligent_sun_shade.yaml`

### Inputs (per instantiation)

| Input | Type | Meeting Room | Mensa |
|---|---|---|---|
| `cover_entity` | entity (cover) | `cover.shellypro2cover_34987a47c9b0_cover_0` | `cover.shellypro2cover_2cbcbbb1ff9c_cover_0` |
| `room_climate_entity` | entity (climate) | `climate.meeting_room_climate` | `climate.mensa_climate` |
| `rate_sensor_entity` | entity (sensor) | `sensor.meeting_room_temp_rate` | `sensor.mensa_temp_rate` |
| `manual_grace_timer` | entity (timer) | `timer.shade_meeting_manual_grace` | `timer.shade_mensa_manual_grace` |
| `manual_override_counter` | entity (counter) | `counter.meeting_room_manual_override_count` | `counter.mensa_manual_override_count` |
| `predictive_close_dt` | entity (input_datetime) | `input_datetime.meeting_room_predictive_close_at` | `input_datetime.mensa_predictive_close_at` |
| `reactive_close_dt` | entity (input_datetime) | `input_datetime.meeting_room_reactive_close_at` | `input_datetime.mensa_reactive_close_at` |
| `forecast_snapshot` | entity (input_number) | `input_number.meeting_room_forecast_max_at_window_start` | `input_number.mensa_forecast_max_at_window_start` |
| `sun_azimuth_min` | number | 90 | 170 |
| `sun_azimuth_max` | number | 150 | 240 |
| `sun_elevation_min` | number | 15 | 15 |
| `room_label` | text | "Meeting Room" | "Mensa" |

The 9 tunable global threshold `input_number.shade_*` entities (plus the populator-owned `shade_today_outdoor_max_forecast`) are referenced **directly** inside the blueprint (not as inputs) because they are shared between instantiations. If we ever want per-room thresholds, we add them as inputs then.

### Trigger list (all inside `triggers:`)

All `numeric_state` triggers that compare against an `input_number.shade_*` value MUST use a **single consistent form** throughout the blueprint. Two forms are acceptable:

1. **Templated form**: `above: "{{ states('input_number.shade_X') | float }}"` — explicit Jinja templating, matches the style used in the condition blocks below.
2. **Entity-id form**: `above: input_number.shade_X` — HA's native "compare against another entity's state" syntax, cleaner and avoids template parsing overhead. Supported for both `numeric_state` triggers and `numeric_state` conditions since HA 2023.x.

Pick one and apply it consistently. The spec's contract is "single form, no mixing"; the specific form is a writing-plans decision. The implementation plan at `docs/superpowers/plans/2026-04-08-intelligent-sun-shade.md` chose the entity-id form for the blueprint because it's shorter and renders cleaner in the HA UI's trace viewer.

| id | Type | Notes |
|---|---|---|
| `window_start` | `numeric_state` on `sun.sun` attribute `azimuth`, `above: "{{ sun_azimuth_min }}"` | Fires when sun enters the room's azimuth window |
| `window_end` | `numeric_state` on `sun.sun` attribute `azimuth`, `above: "{{ sun_azimuth_max }}"` | Fires when sun exits the window |
| `elevation_drop` | `numeric_state` on `sun.sun` attribute `elevation`, `below: "{{ sun_elevation_min }}"` | Fires at end of day / winter low sun |
| `clear_sky` | `numeric_state` on `weather.forecast_home` attribute `cloud_coverage`, `below: "{{ states('input_number.shade_clouds_close_threshold') | float }}"` | Fires when skies clear mid-window |
| `cloudy` | `numeric_state` on `weather.forecast_home` attribute `cloud_coverage`, `above: "{{ states('input_number.shade_clouds_open_threshold') | float }}"` | Fires when clouds roll in |
| `room_hot` | `numeric_state` on `{{ room_climate_entity }}` attribute `current_temperature`, `above: "{{ states('input_number.shade_room_cap') | float }}"`, `for: "00:05:00"` | Reactive close trigger |
| `rate_high` | `numeric_state` on `{{ rate_sensor_entity }}`, `above: "{{ states('input_number.shade_rate_threshold') | float }}"`, `for: "00:05:00"` | Reactive close trigger |
| `room_cool` | `numeric_state` on `{{ room_climate_entity }}` attribute `current_temperature`, `below: "{{ states('input_number.shade_room_reopen') | float }}"` | Re-open trigger |
| `manual_override` | `state` on `{{ cover_entity }}` — no `to:` constraint, fires on any state change | The `user_id is not none` filter is enforced as a **condition** inside Branch 1, not on the trigger, so automation-driven cover changes are ignored safely |
| `grace_expired` | `event` `timer.finished` where `event_data.entity_id == "{{ manual_grace_timer }}"` | Re-evaluate after grace period |
| `season_change` | `state` on `input_select.climate_season` | Top-level `not winter` condition handles the actual gating; this trigger just re-checks |
| `startup` | `homeassistant`, `event: start` | Cold-start re-evaluation, handled by Branch 7 |

### Conditions (top-level)

```yaml
condition:
  - condition: not
    conditions:
      - condition: state
        entity_id: input_select.climate_season
        state: winter
```

### Actions (choose pattern with 6 branches)

All branches additionally check that `sun.sun` is above horizon and the sun is in the room's azimuth window (except branches 1 and 6 which handle grace/override logic).

**Branch 1 — Manual override detected**

The trigger fires on any state change of the cover; the `user_id is not none` filter lives in this branch's conditions (not on the trigger) so that automation-driven cover changes are safely ignored without short-circuiting other branches.

```yaml
- conditions:
    - condition: trigger
      id: manual_override
    - condition: template
      value_template: >
        {{ trigger.to_state is not none and trigger.to_state.context.user_id is not none }}
  sequence:
    - service: counter.increment
      target: { entity_id: "{{ manual_override_counter }}" }
    - service: timer.start
      target: { entity_id: "{{ manual_grace_timer }}" }
      data:
        duration: "00:{{ '%02d' | format(states('input_number.shade_grace_minutes') | int) }}:00"
    - service: logbook.log
      data:
        name: "Intelligent Sun Shade"
        message: "{{ room_label }}: manual override detected, grace timer started"
```

Because `shade_grace_minutes` is bounded to 10–59, the formatted string is always a legal `HH:MM:SS` value (e.g. `"00:30:00"`).

**Branch 2 — Predictive close at window start**

Reads today's forecast max from `input_number.shade_today_outdoor_max_forecast` (populated by the forecast populator automation above), not from `weather.forecast_home`'s deprecated `forecast` attribute. This decouples the blueprint from weather-platform API changes.

```yaml
- conditions:
    - condition: trigger
      id: window_start
    - condition: state
      entity_id: "{{ manual_grace_timer }}"
      state: idle
    - condition: numeric_state
      entity_id: sun.sun
      attribute: elevation
      above: "{{ sun_elevation_min }}"
    - condition: numeric_state
      entity_id: input_number.shade_today_outdoor_max_forecast
      above: "{{ states('input_number.shade_forecast_max_threshold') | float }}"
    - condition: numeric_state
      entity_id: weather.forecast_home
      attribute: cloud_coverage
      below: "{{ states('input_number.shade_clouds_close_threshold') | float }}"
    - condition: numeric_state
      entity_id: "{{ cover_entity }}"
      attribute: current_position
      above: 50
  sequence:
    - service: input_number.set_value
      target: { entity_id: "{{ forecast_snapshot }}" }
      data:
        value: "{{ states('input_number.shade_today_outdoor_max_forecast') | float }}"
    - service: cover.set_cover_position
      target: { entity_id: "{{ cover_entity }}" }
      data:
        position: "{{ states('input_number.shade_closed_position') | int }}"
    - service: input_datetime.set_datetime
      target: { entity_id: "{{ predictive_close_dt }}" }
      data:
        datetime: "{{ now().isoformat() }}"
    - service: logbook.log
      data:
        name: "Intelligent Sun Shade"
        message: >
          {{ room_label }}: predictive close
          (forecast max {{ states('input_number.shade_today_outdoor_max_forecast') }}°C,
           clouds {{ state_attr('weather.forecast_home', 'cloud_coverage') }}%)
```

**Branch 3 — Reactive override (room hot or rising fast)**
```yaml
- conditions:
    - condition: or
      conditions:
        - condition: trigger
          id: room_hot
        - condition: trigger
          id: rate_high
    - condition: state
      entity_id: "{{ manual_grace_timer }}"
      state: idle
    - condition: numeric_state
      entity_id: sun.sun
      attribute: azimuth
      above: "{{ sun_azimuth_min }}"
    - condition: numeric_state
      entity_id: sun.sun
      attribute: azimuth
      below: "{{ sun_azimuth_max }}"
    - condition: numeric_state
      entity_id: sun.sun
      attribute: elevation
      above: "{{ sun_elevation_min }}"
    - condition: numeric_state
      entity_id: "{{ cover_entity }}"
      attribute: current_position
      above: 50
  sequence:
    - service: cover.set_cover_position
      target: { entity_id: "{{ cover_entity }}" }
      data:
        position: "{{ states('input_number.shade_closed_position') | int }}"
    - service: input_datetime.set_datetime
      target: { entity_id: "{{ reactive_close_dt }}" }
      data:
        datetime: "{{ now().isoformat() }}"
    - service: logbook.log
      data:
        name: "Intelligent Sun Shade"
        message: >
          {{ room_label }}: reactive close
          (room {{ state_attr(room_climate_entity, 'current_temperature') }}°C,
           rate {{ states(rate_sensor_entity) }}°C/h)
```

**Branch 4 — Re-open (cool + cloudy)**

The "above `shade_clouds_close_threshold`" condition reuses the same threshold as the predictive-close gate, so the two directions are symmetric: below the threshold is "clear enough to warrant closing", above it is "cloudy enough that heating is no longer a concern."

```yaml
- conditions:
    - condition: or
      conditions:
        - condition: trigger
          id: room_cool
        - condition: trigger
          id: cloudy
    - condition: numeric_state
      entity_id: "{{ cover_entity }}"
      attribute: current_position
      below: 50
    - condition: or
      conditions:
        - condition: and
          conditions:
            - condition: numeric_state
              entity_id: "{{ room_climate_entity }}"
              attribute: current_temperature
              below: "{{ states('input_number.shade_room_reopen') | float }}"
            - condition: numeric_state
              entity_id: weather.forecast_home
              attribute: cloud_coverage
              above: "{{ states('input_number.shade_clouds_close_threshold') | float }}"
        - condition: numeric_state
          entity_id: weather.forecast_home
          attribute: cloud_coverage
          above: "{{ states('input_number.shade_clouds_open_threshold') | float }}"
  sequence:
    - service: cover.set_cover_position
      target: { entity_id: "{{ cover_entity }}" }
      data:
        position: "{{ states('input_number.shade_open_position') | int }}"
```

**Branch 5 — Window end (sun moves out or elevation drops)**
```yaml
- conditions:
    - condition: or
      conditions:
        - condition: trigger
          id: window_end
        - condition: trigger
          id: elevation_drop
    - condition: numeric_state
      entity_id: "{{ cover_entity }}"
      attribute: current_position
      below: 50
  sequence:
    - service: cover.set_cover_position
      target: { entity_id: "{{ cover_entity }}" }
      data:
        position: "{{ states('input_number.shade_open_position') | int }}"
```

**Branch 6 — Grace expired, re-evaluate**
```yaml
- conditions:
    - condition: trigger
      id: grace_expired
    - condition: numeric_state
      entity_id: sun.sun
      attribute: azimuth
      above: "{{ sun_azimuth_min }}"
    - condition: numeric_state
      entity_id: sun.sun
      attribute: azimuth
      below: "{{ sun_azimuth_max }}"
    - condition: numeric_state
      entity_id: "{{ cover_entity }}"
      attribute: current_position
      above: 50
    # Re-check whether we should close (room still hot / forecast still warrants)
    - condition: or
      conditions:
        - condition: numeric_state
          entity_id: "{{ room_climate_entity }}"
          attribute: current_temperature
          above: "{{ states('input_number.shade_room_cap') | float }}"
        - condition: and
          conditions:
            - condition: numeric_state
              entity_id: input_number.shade_today_outdoor_max_forecast
              above: "{{ states('input_number.shade_forecast_max_threshold') | float }}"
            - condition: numeric_state
              entity_id: weather.forecast_home
              attribute: cloud_coverage
              below: "{{ states('input_number.shade_clouds_close_threshold') | float }}"
  sequence:
    - service: cover.set_cover_position
      target: { entity_id: "{{ cover_entity }}" }
      data:
        position: "{{ states('input_number.shade_closed_position') | int }}"
```

**Branch 7 — Startup re-evaluation (HA cold start mid-day)**

Handles the case where HA restarts after the sun has already crossed `sun_azimuth_min` for the day. Without this, `numeric_state` triggers wouldn't fire until the next azimuth crossing tomorrow morning. The startup branch re-runs the same predictive-close check that Branch 2 would have run, and also writes the per-room `forecast_snapshot` so the evaluator's nightly comparison has the correct "predicted vs actual" delta to analyze.

The sequence begins with a 30-second delay so that `weather.forecast_home`, `sensor.<room>_temp_rate`, and the forecast populator's output have all stabilized before conditions are re-checked (HA fires `homeassistant.start` before all integrations are fully loaded).

```yaml
- conditions:
    - condition: trigger
      id: startup
  sequence:
    - delay: "00:00:30"
    - condition: state
      entity_id: "{{ manual_grace_timer }}"
      state: idle
    - condition: numeric_state
      entity_id: sun.sun
      attribute: azimuth
      above: "{{ sun_azimuth_min }}"
    - condition: numeric_state
      entity_id: sun.sun
      attribute: azimuth
      below: "{{ sun_azimuth_max }}"
    - condition: numeric_state
      entity_id: sun.sun
      attribute: elevation
      above: "{{ sun_elevation_min }}"
    - condition: numeric_state
      entity_id: input_number.shade_today_outdoor_max_forecast
      above: "{{ states('input_number.shade_forecast_max_threshold') | float }}"
    - condition: numeric_state
      entity_id: weather.forecast_home
      attribute: cloud_coverage
      below: "{{ states('input_number.shade_clouds_close_threshold') | float }}"
    - condition: numeric_state
      entity_id: "{{ cover_entity }}"
      attribute: current_position
      above: 50
    - service: input_number.set_value
      target: { entity_id: "{{ forecast_snapshot }}" }
      data:
        value: "{{ states('input_number.shade_today_outdoor_max_forecast') | float }}"
    - service: cover.set_cover_position
      target: { entity_id: "{{ cover_entity }}" }
      data:
        position: "{{ states('input_number.shade_closed_position') | int }}"
    - service: input_datetime.set_datetime
      target: { entity_id: "{{ predictive_close_dt }}" }
      data:
        datetime: "{{ now().isoformat() }}"
    - service: logbook.log
      data:
        name: "Intelligent Sun Shade"
        message: "{{ room_label }}: startup re-evaluation — closing (conditions met)"
```

Note: this branch uses inline `condition:` items inside the sequence (after the delay) rather than the outer `conditions:` list, because the conditions must be re-checked *after* the delay — the entities they reference may not be loaded yet at the moment the trigger fires. If any inline condition fails, the sequence exits cleanly without writing anything.

The `startup` trigger is added to the trigger list as `- trigger: homeassistant, event: start, id: startup`.

### Mode

`mode: single` — prevent overlapping runs. If a trigger fires during execution, it's dropped. The next trigger fire will re-evaluate.

## Component 2 — Helper entities

### Global thresholds (`input_numbers.yaml`)

Single source of truth, shared between both blueprint instances:

| Entity | Initial | Min | Max | Step | Unit |
|---|---|---|---|---|---|
| `input_number.shade_forecast_max_threshold` | 22.0 | 18 | 26 | 0.5 | °C |
| `input_number.shade_clouds_close_threshold` | 50 | 20 | 80 | 5 | % |
| `input_number.shade_clouds_open_threshold` | 70 | 40 | 90 | 5 | % |
| `input_number.shade_room_cap` | 25.0 | 23 | 28 | 0.5 | °C |
| `input_number.shade_rate_threshold` | 0.6 | 0.3 | 1.2 | 0.1 | °C/h |
| `input_number.shade_room_reopen` | 23.0 | 21 | 25 | 0.5 | °C |
| `input_number.shade_closed_position` | 30 | 0 | 50 | 5 | % |
| `input_number.shade_open_position` | 100 | 50 | 100 | 5 | % |
| `input_number.shade_grace_minutes` | 30 | 10 | 59 | 1 | min |
| `input_number.shade_today_outdoor_max_forecast` | 0 | -20 | 50 | 0.1 | °C |

All have `mode: box` so the user can also type a value directly in the UI.

**Note on `shade_grace_minutes` max=59**: HA's `timer.start` service expects duration in `HH:MM:SS` format. Capping at 59 guarantees the minutes-only formatted duration string is always valid. If a longer grace period is ever needed, change the duration template to include an `HH:` component.

**`shade_today_outdoor_max_forecast` is NOT user-tunable by the evaluator.** It is overwritten daily by the populator automation below. It is listed with the threshold helpers because it lives in the same file, but the evaluator must not propose changes to it.

### Forecast populator automation (new automation in `automations.yaml`)

`weather.forecast_home`'s `forecast` attribute was deprecated in HA 2024.4. The modern way is to call the `weather.get_forecasts` action with a response variable. We do this in a dedicated automation that writes today's max into `input_number.shade_today_outdoor_max_forecast`, so the blueprint can read a single sensor state instead of calling a service from within a condition (which HA does not support).

```yaml
- id: sun_shade_forecast_populator
  alias: Sun Shade — Populate today's outdoor max forecast
  description: >
    Fetches today's forecast max from weather.forecast_home via the
    get_forecasts action and stores it in input_number.shade_today_outdoor_max_forecast
    for the blueprint's predictive-close condition.
  triggers:
    - trigger: homeassistant
      event: start
    - trigger: time
      at: "06:00:00"
    - trigger: time_pattern
      hours: "/1"
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

Runs on HA startup (for cold-start recovery), at 06:00 daily (before the sun window), and every hour at :05 (to catch forecast updates during the day).

### Per-room snapshots (`input_numbers.yaml`, same file)

| Entity | Initial | Min | Max | Step | Purpose |
|---|---|---|---|---|---|
| `input_number.meeting_room_forecast_max_at_window_start` | 0 | -20 | 50 | 0.1 | Evaluator reads this to compare predicted vs actual |
| `input_number.mensa_forecast_max_at_window_start` | 0 | -20 | 50 | 0.1 | Same, for Mensa |

### Per-room datetimes (`input_datetimes.yaml`)

| Entity | has_date | has_time | Purpose |
|---|---|---|---|
| `input_datetime.meeting_room_predictive_close_at` | true | true | Timestamp of last predictive close |
| `input_datetime.meeting_room_reactive_close_at` | true | true | Timestamp of last reactive close |
| `input_datetime.mensa_predictive_close_at` | true | true | Same, for Mensa |
| `input_datetime.mensa_reactive_close_at` | true | true | Same, for Mensa |

### Timers (`timers.yaml`)

| Entity | Duration | Restore |
|---|---|---|
| `timer.shade_meeting_manual_grace` | 00:30:00 (default; actual duration overridden at start from `shade_grace_minutes`) | true |
| `timer.shade_mensa_manual_grace` | 00:30:00 | true |

### Counters (`counters.yaml`)

| Entity | Initial | Restore | Reset |
|---|---|---|---|
| `counter.meeting_room_manual_override_count` | 0 | true | Midnight, via automation |
| `counter.mensa_manual_override_count` | 0 | true | Midnight, via automation |

### Sensors — two locations

Modern `template:` sensors and legacy `sensor:` platform entries must live in **separate files** because `configuration.yaml` includes them under different top-level keys. We use:

- **`homeassistant/config/templates.yaml`** (already wired as `template: !include templates.yaml` in `configuration.yaml:36`) — for the two new template sensors that expose climate attributes as plain sensors
- **`homeassistant/config/sensors.yaml`** (new file, wired as `sensor: !include sensors.yaml`) — for the two new derivative sensors

#### Template sensors — append to existing `homeassistant/config/templates.yaml`

```yaml
# (append to the existing `- sensor:` list that already holds the fancoil demand sensors)
    - name: "Meeting Room Temp"
      unique_id: meeting_room_temp
      state: "{{ state_attr('climate.meeting_room_climate', 'current_temperature') }}"
      unit_of_measurement: "°C"
      device_class: temperature
      availability: >
        {{ state_attr('climate.meeting_room_climate', 'current_temperature') is not none }}

    - name: "Mensa Temp"
      unique_id: mensa_temp
      state: "{{ state_attr('climate.mensa_climate', 'current_temperature') }}"
      unit_of_measurement: "°C"
      device_class: temperature
      availability: >
        {{ state_attr('climate.mensa_climate', 'current_temperature') is not none }}
```

These sensors are needed because HA's `derivative` platform reads from an entity's primary state, not from an attribute. We materialize the `current_temperature` attribute as a numeric sensor state, then derivative-difference it.

#### Derivative sensors — new file `homeassistant/config/sensors.yaml`

```yaml
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

Wire into `configuration.yaml` with `sensor: !include sensors.yaml`.

### Midnight counter reset (new automation in `automations.yaml`)

```yaml
- id: sun_shade_midnight_reset
  alias: Sun Shade — Midnight counter reset
  description: Resets manual override counters at midnight for the evaluator's daily window
  triggers:
    - trigger: time
      at: "00:00:01"
  actions:
    - service: counter.reset
      target:
        entity_id:
          - counter.meeting_room_manual_override_count
          - counter.mensa_manual_override_count
```

### Dashboard panel (modification to `dashboards/climate.yaml`)

Add this card under the existing "Window Shades" card so the evaluator's current configuration and recent activity are visible at a glance:

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
      name: Meeting — forecast at 08:00
    - entity: input_number.mensa_forecast_max_at_window_start
      name: Mensa — forecast at 11:00
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

## Component 3 — Evaluator (remote triggers)

### Timezone and ordering invariants

**Timezone**: `RemoteTrigger` cron expressions are **always interpreted in UTC**, never local time. The spec pins schedules in UTC and accepts that local clock-time shifts by 1 hour between CEST and CET.

**Ordering invariant**: The schedule must satisfy `nightly_trigger_time < midnight_local < midnight_counter_reset < morning_trigger_time`. With 21:00 UTC nightly + 00:00:01 local counter reset + 05:00 UTC morning, this holds year-round for Europe/Rome. If anyone later moves the nightly trigger to after 22:00 UTC (= after 00:00 CEST), the nightly run would read a zeroed counter instead of the day's actual override count. The nightly time must not drift past 21:59 UTC without also moving the counter reset.

### Trigger #1: `sun-shade-evaluator-nightly`

**Schedule**: `0 21 * * *` (21:00 UTC = 23:00 CEST / 22:00 CET)
**Model**: `claude-sonnet-4-6`
**Allowed tools**: `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`
**Sources**: `https://github.com/daggy72/homeassistant-config-s4it`
**MCP connections**: `HomeAssistant-CM1` (connector_uuid `3e8341aa-e108-4345-97dd-8679a0bc7c8b`) — attached as a fallback for live state queries; most data comes via HA REST API with the LLT

**Prompt structure** (skeleton — see the Report and Telegram message templates in the sections below for the exact prose this trigger emits):

1. Preamble explaining the system, referencing this spec file (`docs/superpowers/specs/2026-04-07-intelligent-sun-shade-design.md`) in the repo
2. Constants section:
   - `HA_BASE_URL=https://hacm1.sales4.it`
   - `HA_TOKEN=<long-lived access token>`  ← embedded literal, never in git
   - `TG_BOT_TOKEN=<telegram bot token>`   ← embedded literal
   - `TG_CHAT_ID=<telegram chat id>`       ← embedded literal
3. Step-by-step procedure — follows the architecture-diagram step list for Trigger #1 exactly
4. **Report format**: use the structure defined in "Telegram message formats" below (the "Nightly — analysis report" and "Nightly — no change to propose" templates). The markdown file in `docs/sun-shade-eval/YYYY-MM-DD.md` is the Telegram message plus per-room raw metrics (min/max/peak-time/time-above-cap/cover timeline tables).
5. **Telegram message format**: reuse the "Nightly — analysis report" or "Nightly — no change to propose" template verbatim; never invent new formats ad-hoc.
6. Guardrails:
   - Never edit blueprint YAML, only `input_number` values
   - Never propose a change to `input_number.shade_today_outdoor_max_forecast` (it is populator-owned, not a tunable threshold)
   - Never propose a change outside the `input_number`'s min/max bounds
   - If `insufficient_data` (e.g., both automations disabled, HA unreachable, or recorder has < 2 hours of data for the sun window), write report but do not propose changes
   - Do not create more than one pending change per run
   - If there is already an open pending change for the same `input_number`, do not create a new one — supersede the existing one by updating the `reasoning`, `changes`, and `report_file` fields in place, and **refreshing** `expires_at` to `now + 24h`. The original `token` and `created_at` are preserved so the user's in-flight Telegram approval still resolves against the same token. (This means the user always has a full 24h from the most recent proposal, not a dwindling window from the original.)

### Trigger #2: `sun-shade-evaluator-morning`

**Schedule**: `0 5 * * *` (05:00 UTC = 07:00 CEST / 06:00 CET)
**Model**: `claude-sonnet-4-6`
**Allowed tools**: `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`
**Sources**: same as nightly
**MCP connections**: same as nightly
**Secrets**: same three (HA_TOKEN, TG_BOT_TOKEN, TG_CHAT_ID)

**Prompt structure**:

1. Preamble referencing this spec
2. Constants section
3. Procedure:
   - Read `eval-state.json`
   - Call `https://api.telegram.org/bot<TG_BOT_TOKEN>/getUpdates?offset=<last_update_id + 1>`
   - Parse replies; match (case-insensitive, leading/trailing whitespace tolerated): `^\s*(apply|ignore)\s+(EVAL-\d{4}-\d{2}-\d{2}-[0-9A-HJKMNP-TV-Z]{4})\s*$`
   - For each `apply` that matches a pending entry:
     - For each change in the entry: use `Edit` tool on the YAML file to set the new value; then `curl` to `POST /api/services/input_number/set_value` with payload `{"entity_id": "...", "value": ...}` and `Authorization: Bearer <HA_TOKEN>`
     - Append to `docs/sun-shade-eval/applied.log` a line `YYYY-MM-DD HH:MM:SS applied <token> <changes>`
     - Send Telegram confirmation
     - Remove pending entry from state file
   - For each `ignore`: remove entry, send Telegram confirmation, log to `ignored.log`
   - Expire any pending entry where `now() > expires_at`: send Telegram "expired" message, remove entry
   - Update `last_telegram_update_id` to `max(update_id)` seen
   - `git add / commit / push`
4. Error handling: if Telegram unreachable, log and exit cleanly (next run retries); if HA REST unreachable during apply, leave pending entry in place and send Telegram error

## State file format

**Path**: `homeassistant/eval-state.json`

```json
{
  "version": 1,
  "last_telegram_update_id": 0,
  "pending_changes": []
}
```

**Pending entry schema**:

```json
{
  "token": "EVAL-2026-04-07-A1B2",
  "created_at": "2026-04-07T23:00:12+02:00",
  "expires_at": "2026-04-08T23:00:12+02:00",
  "reasoning": "Meeting Room peaked at 26.4°C, predictive did not fire (forecast was 21°C, actual 24°C). Lowering forecast threshold.",
  "changes": [
    {
      "entity_id": "input_number.shade_forecast_max_threshold",
      "yaml_file": "homeassistant/config/input_numbers.yaml",
      "yaml_key": "shade_forecast_max_threshold.initial",
      "old_value": 22.0,
      "new_value": 21.0
    }
  ],
  "report_file": "docs/sun-shade-eval/2026-04-07.md"
}
```

**Token format**: `EVAL-YYYY-MM-DD-XXXX` where XXXX is 4 characters drawn from the Crockford base32 alphabet (`0123456789ABCDEFGHJKMNPQRSTVWXYZ` — no I, L, O, U) for low misread rate on mobile. Matches the regex `EVAL-\d{4}-\d{2}-\d{2}-[0-9A-HJKMNP-TV-Z]{4}`. The morning trigger's reply parser is case-insensitive and tolerates leading/trailing whitespace.

**Invariants**:
- At most one pending entry per `input_number.entity_id` at any time
- `expires_at` = `created_at + 24h`
- Entries are removed only by the morning trigger (via apply/ignore/expire) or by the nightly trigger when it supersedes an entry with a newer proposal

## Telegram message formats

### Nightly — analysis report

```
🌞 Sun Shade Evaluator — 2026-04-07

Meeting Room: peaked 26.4°C at 12:15 (above cap 25.0°C for 1h40m)
  • Predictive close: ❌ did not fire (forecast 21°C < threshold 22°C)
  • Reactive close: ✅ fired at 11:20 on room_cap breach
  • Manual overrides: 0

Mensa: peaked 24.2°C at 13:30 (below cap, ok)
  • Predictive close: ✅ fired at 11:45 (forecast 23°C, clouds 20%)
  • Manual overrides: 0

📊 Verdict: Meeting Room forecast threshold is too conservative.

Proposed change:
  input_number.shade_forecast_max_threshold: 22.0 → 21.0

Reasoning: The forecast was 21°C, actual outdoor max was 24°C. Lowering
the threshold to 21 would have triggered the predictive close at 08:00
instead of waiting for the reactive override at 11:20, saving ~3h of
above-cap room temperature.

To apply:  apply EVAL-2026-04-07-A1B2
To ignore: ignore EVAL-2026-04-07-A1B2

Full report: docs/sun-shade-eval/2026-04-07.md
(Auto-expires in 24h if no reply.)
```

### Morning — apply confirmation

```
✅ Applied EVAL-2026-04-07-A1B2

input_number.shade_forecast_max_threshold: 22.0 → 21.0

Committed to main. `git pull` on the NAS when convenient; the
running HA instance has already been updated via REST API.
```

### Morning — ignore confirmation

```
❌ Ignored EVAL-2026-04-07-A1B2

No changes applied. Full report remains at docs/sun-shade-eval/2026-04-07.md.
```

### Morning — expired

```
⏰ Expired EVAL-2026-04-07-A1B2 (no reply within 24h)

Proposed change was dropped:
  input_number.shade_forecast_max_threshold: 22.0 → 21.0

If tomorrow's analysis reaches the same conclusion, you'll get a new
proposal.
```

### Nightly — no change to propose

```
🌞 Sun Shade Evaluator — 2026-04-07

Meeting Room: peaked 23.8°C at 12:20 (below cap, ok)
Mensa: peaked 23.1°C at 13:10 (below cap, ok)

📊 Verdict: thresholds OK.

No changes proposed. Full report: docs/sun-shade-eval/2026-04-07.md
```

## File-level changes

### New files (8)

1. `homeassistant/config/blueprints/automation/custom/intelligent_sun_shade.yaml`
2. `homeassistant/config/input_numbers.yaml`
3. `homeassistant/config/input_datetimes.yaml`
4. `homeassistant/config/timers.yaml`
5. `homeassistant/config/counters.yaml`
6. `homeassistant/config/sensors.yaml` — derivative sensors only
7. `homeassistant/eval-state.json`
8. `docs/sun-shade-eval/.gitkeep`

### Modified files (4)

1. `homeassistant/config/configuration.yaml` — add `input_number: !include input_numbers.yaml`, `input_datetime: !include input_datetimes.yaml`, `timer: !include timers.yaml`, `counter: !include counters.yaml`, `sensor: !include sensors.yaml` (5 new includes; the existing `template: !include templates.yaml` is reused, not duplicated)
2. `homeassistant/config/templates.yaml` — append 2 template sensors (`Meeting Room Temp`, `Mensa Temp`) to the existing `- sensor:` list
3. `homeassistant/config/automations.yaml` — delete `mensa_sun_shade`; add 2 blueprint instantiations, the forecast populator automation, and the midnight counter reset automation. Manual override detection is handled inside the blueprint (Branch 1), not as a separate automation.
4. `homeassistant/config/dashboards/climate.yaml` — add the `Sun Shade — Thresholds & Activity` entities card under the existing Window Shades card

### Unchanged

- `cs_sun_shade` — out of scope
- All climate automations, fancoil speed control, etc.
- All ESPHome files
- All other project files

## Deployment order (critical)

Order matters: helpers must exist before anything that references them. Each numbered step is an atomic reload/restart boundary — complete and verify before moving to the next.

1. **Create helper files**: `input_numbers.yaml`, `input_datetimes.yaml`, `timers.yaml`, `counters.yaml`, `sensors.yaml`
2. **Append template sensors** (`Meeting Room Temp`, `Mensa Temp`) to the existing `homeassistant/config/templates.yaml`
3. **Update `configuration.yaml`** — add the 5 new includes (`input_number`, `input_datetime`, `timer`, `counter`, `sensor`)
4. **Run HA config check** (per CLAUDE.md)
5. **Restart HA** — helpers can't be referenced before they exist in the registry
6. **Verify in HA UI**: all 10 global `shade_*` helpers exist at their default values; all 2 per-room snapshot helpers exist; 4 `input_datetime` helpers, 2 timers, 2 counters, and the 4 sensors (2 template + 2 derivative) all appear. Derivative sensors will read `unknown` for the first 30 min of accumulated history — that's expected.
7. **Create the blueprint file** at `homeassistant/config/blueprints/automation/custom/intelligent_sun_shade.yaml`
8. **Reload Blueprints** via HA UI (Settings → Automations & Scenes → Blueprints → Reload)
9. **Add the forecast populator automation** to `automations.yaml`
10. **Add the midnight counter reset automation** to `automations.yaml`
11. **Reload Automations** via HA UI; verify both new automations appear
12. **Manually trigger the forecast populator once** via dev tools → services → `automation.trigger` so the `shade_today_outdoor_max_forecast` helper gets a non-zero starting value
13. **Delete `mensa_sun_shade`** from `automations.yaml`
14. **Add the two blueprint instantiations** (Meeting Room + Mensa) to `automations.yaml`
15. **Reload Automations** again; verify both blueprint instances appear, no errors in Logbook or `home-assistant.log`
16. **Add the dashboard panel** to `homeassistant/config/dashboards/climate.yaml` and reload the dashboard in the UI
17. **Wait 1 week** of real use on manually-tuned defaults; iterate on thresholds via the UI if needed
18. **Initialize `homeassistant/eval-state.json`** with the content `{"version": 1, "last_telegram_update_id": 0, "pending_changes": []}` and commit. This file must exist before step 19 because the nightly trigger procedure reads it unconditionally; initializing it as part of deployment avoids implicit first-run creation logic in the evaluator prompts.
19. **Create the two remote triggers** via `RemoteTrigger.create` with `enabled: false`
20. **Smoke-test the nightly trigger** manually via `RemoteTrigger.run`
21. **Smoke-test an approval cycle** — reply `apply EVAL-...` on Telegram, run the morning trigger manually, confirm YAML edit + HA state update
22. **Enable both triggers** via `RemoteTrigger.update { enabled: true }`

Each of steps 9, 10, 13, 14, and 16 is independently reloadable and independently reversible via `git revert`.

## Testing plan

### Layer 1 — Config validation (before deploy)

- HA config check passes (`ha core check` or equivalent)
- Blueprint loads without validation errors in HA UI
- Manual `Run actions` on each automation branch (using dev tools → services → `automation.trigger` with `skip_condition: false`)

### Layer 2 — Reactive override live test

- Lower `input_number.shade_room_cap` to 1°C below current Meeting Room temperature
- Wait for trigger (≤ 5 minutes for `for: 5m` debounce)
- Confirm:
  - `cover.shellypro2cover_34987a47c9b0_cover_0` moves to 30%
  - `input_datetime.meeting_room_reactive_close_at` updates to now
  - Logbook shows "Intelligent Sun Shade: Meeting Room: reactive close"
- Restore `shade_room_cap` to 25°C
- Manually open the cover via the HA UI
- Confirm:
  - `counter.meeting_room_manual_override_count` increments
  - `timer.shade_meeting_manual_grace` starts with 30:00 duration
  - Next trigger fire (e.g., `rate_high`) does NOT act while timer is running
- Wait for timer to expire (or skip ahead via `timer.finish` dev tool)
- Confirm grace-expired branch re-evaluates and closes if conditions still met

### Layer 3 — Predictive close live test

- On a sunny morning when forecast max ≥ 22°C:
- At 08:00 local (or whenever sun crosses azimuth 90° in Meeting Room, 170° in Mensa), confirm:
  - `input_number.<room>_forecast_max_at_window_start` gets a reasonable value
  - Cover closes to 30%
  - `input_datetime.<room>_predictive_close_at` updates
  - Logbook shows the predictive close event

### Layer 4 — Evaluator smoke test (after 1-week soak)

- Create both triggers with `enabled: false`
- Invoke nightly trigger manually via `RemoteTrigger.run`
- Confirm:
  - `docs/sun-shade-eval/YYYY-MM-DD.md` is committed to main
  - `eval-state.json` is committed (may have no pending entries if nothing to propose)
  - Telegram message arrives
  - `git log` shows the commit with reasoning
- If a pending entry exists: reply `apply EVAL-...` on Telegram
- Invoke morning trigger manually
- Confirm:
  - YAML edit applied to `input_numbers.yaml`
  - `GET /api/states/input_number.shade_forecast_max_threshold` shows the new value
  - Pending entry removed from state file
  - Telegram confirmation arrives
  - Commit appears in git log

### Layer 5 — Production enable

- Update both triggers to `enabled: true`
- Monitor for 1 week
- Review reports, check threshold values in HA UI are stable / sensible

## Error handling — fail-soft matrix

| Failure mode | Detection | Behavior | Recovery |
|---|---|---|---|
| HA REST API network error (5xx / timeout / connection refused) | `curl` returns non-2xx with network error | Evaluator aborts the run, sends Telegram error ("HA unreachable"), no state file changes | Next scheduled run retries automatically |
| HA token revoked or expired (401) | `curl` returns HTTP 401 | Evaluator aborts the run, sends a distinct **high-priority** Telegram error ("HA token rejected — rotate LLT and update trigger prompts"), does not retry with the same token on following runs to avoid hammering | User creates new LLT in HA UI, updates both trigger prompts via `RemoteTrigger.update`, runs morning trigger manually to confirm |
| Telegram API unreachable | `curl` to api.telegram.org fails | Report still written + committed; Telegram notification skipped; exit status logged in the committed report | Next morning run's `getUpdates` catches up; no data lost |
| GitHub push fails (remote diverged) | `git push` returns non-zero | Pull with rebase, retry push up to 3× | If still fails, abandon the run, send Telegram alert with the error output |
| Telegram reply malformed (e.g., `apply EVAL` without full token) | Regex doesn't match | Ignored silently (no auto-apply) | User re-sends cleanly |
| Token in reply doesn't match any pending entry | Not found in state file | Morning trigger sends "unknown token" reply via Telegram | User retries with correct token; pending entry unchanged |
| HA restarts between YAML edit and `set_value` call | Not detectable from evaluator | YAML edit persists to disk; HA picks it up on next full restart | No action needed; state converges on next reload |
| HA cold-start mid-day (after `window_start` azimuth crossing already happened) | Not detectable without a startup trigger | Branch 7 (startup re-evaluation) fires on `homeassistant.start` and re-runs the close decision if conditions are met | Automatic; no action needed |
| Manual override counter race at midnight | Counter reset trigger fires at 00:00:01 local, potentially overlapping with a manual override at 23:59:59 | At most one override event may be lost | Tolerable — override signal is aggregate across multiple days |
| Blueprint template error at runtime | HA logs error in `home-assistant.log` | Automation skips the affected branch; other branches continue | Check log; fix template in blueprint |
| Rate sensor `unknown` (fresh boot, < 30 min of data) | `sensor.<room>_temp_rate` state is `unknown` | `numeric_state` trigger with numeric `above:` won't fire on `unknown`; `for: "00:05:00"` debounce adds further protection | Self-heals after 30 min of data accumulation |
| `weather.forecast_home` `forecast` attribute empty or absent | Forecast populator's `weather.get_forecasts` response has empty `forecast` list | Populator writes `0` to `shade_today_outdoor_max_forecast`; predictive close won't fire (0 is below any reasonable threshold); reactive override still protects the room | Check weather integration; manually set helper if weather is persistently broken |
| Evaluator proposes change outside bounds | `input_number.set_value` rejected by HA | Morning trigger logs error, leaves pending entry in place, sends Telegram alert | Evaluator's guardrail prevents this; if it slips through, user fixes manually |
| Two pending entries for same `input_number` | Prevented by nightly's "supersede in place" guardrail | N/A | N/A |
| Concurrent runs (nightly + morning overlap) | `mode: single` on blueprint prevents HA-side races; triggers run in distinct cloud sessions but both push to the same repo | Last push wins; rebase-retry loop resolves | No special handling needed |
| Clock drift between cron and HA local time | UTC cron doesn't follow DST | 1-hour shift in local time between CEST and CET is expected and documented | User tolerates; 22:00 vs 23:00 local is acceptable for both summer and winter |

## Rollback plan

Each rollback is a single reversible action. None require manual data recovery.

| Scenario | Rollback |
|---|---|
| Blueprint logic broken | `git revert` the automation.yaml change; restore `mensa_sun_shade` from git history if needed |
| Evaluator making bad decisions | `RemoteTrigger.update { enabled: false }` on both triggers; no code revert needed |
| Threshold drifted badly | Manually set all 9 `input_number.shade_*` values via HA UI, commit updated `input_numbers.yaml` |
| Emergency disarm | Flip `input_select.climate_season` to `winter` — both automations stop instantly |
| Wipe evaluator state | Delete `eval-state.json` content back to `{"version": 1, "last_telegram_update_id": 0, "pending_changes": []}`, commit |
| Remote triggers compromised | Revoke HA LLT in UI, rotate Telegram bot token, update prompts in trigger configs |

The hardest-to-rollback change is removing helper entities once automations reference them. Mitigation: the deployment order creates helpers before automations, and rollback reverses that order (disable automations first, then remove helpers).

## Observability

- **HA Logbook** — every cover action, timer start/expire, and manual override writes a human-readable entry via `logbook.log` service calls inside the blueprint
- **HA Dashboard panel** — the new panel shows current threshold values + override counters + last close timestamps, for at-a-glance verification
- **Git log** — `git log --oneline docs/sun-shade-eval/ homeassistant/eval-state.json homeassistant/config/input_numbers.yaml` shows every evaluator commit with reasoning
- **Telegram chat history** — append-only decision log of every proposal, approval, ignore, and expiry
- **HA state history** — standard recorder captures all entity state changes for retrospective analysis

## Out of scope

- Migrating `cs_sun_shade` to the new blueprint (future follow-up, 5-minute change once blueprint is proven)
- Per-room threshold overrides (YAGNI; revisit if evaluator data shows divergent needs)
- Automating `cover.shellypro2cover_34987a47c9b0_cover_1` (CS, not touched)
- Adding additional rooms beyond Meeting Room + Mensa
- Auto-tuning without human approval (Pattern iii / fully autonomous mode)
- Any HA-side AI/conversation agent integration
- Creating a Telegram MCP connector in claude.ai (Bot API via curl is sufficient)

## Future work (not part of this spec)

- Migrate `cs_sun_shade` to use the same blueprint (same inputs pattern, different azimuth range)
- Split thresholds per-room if evaluator data shows Meeting Room and Mensa have different optimal values
- Extend the blueprint to support time-based windows (for rooms without clean azimuth gating, e.g., east-facing rooms where the sun transit is too fast for azimuth alone)
- Add a weekly summary Telegram message aggregating 7 days of verdicts
- Cross-reference with `sensor.outdoor_temperature` history to adjust the forecast-vs-actual calibration (weight the evaluator's trust in forecast accuracy)

## Open questions

None. All design decisions locked during brainstorming on 2026-04-07.

## Glossary — every entity introduced by this spec

One place, alphabetical, to cross-check that everything referenced exists exactly once.

### Covers (pre-existing, not introduced — listed for reference)

- `cover.shellypro2cover_34987a47c9b0_cover_0` — Meeting Room shade
- `cover.shellypro2cover_2cbcbbb1ff9c_cover_0` — Mensa shade

### Climate (pre-existing, not introduced)

- `climate.meeting_room_climate`
- `climate.mensa_climate`

### Input numbers (new — `input_numbers.yaml`)

- `input_number.mensa_forecast_max_at_window_start`
- `input_number.meeting_room_forecast_max_at_window_start`
- `input_number.shade_closed_position`
- `input_number.shade_clouds_close_threshold`
- `input_number.shade_clouds_open_threshold`
- `input_number.shade_forecast_max_threshold`
- `input_number.shade_grace_minutes`
- `input_number.shade_open_position`
- `input_number.shade_rate_threshold`
- `input_number.shade_room_cap`
- `input_number.shade_room_reopen`
- `input_number.shade_today_outdoor_max_forecast` *(populator-owned, not tunable by evaluator)*

### Input datetimes (new — `input_datetimes.yaml`)

- `input_datetime.meeting_room_predictive_close_at`
- `input_datetime.meeting_room_reactive_close_at`
- `input_datetime.mensa_predictive_close_at`
- `input_datetime.mensa_reactive_close_at`

### Timers (new — `timers.yaml`)

- `timer.shade_meeting_manual_grace`
- `timer.shade_mensa_manual_grace`

### Counters (new — `counters.yaml`)

- `counter.meeting_room_manual_override_count`
- `counter.mensa_manual_override_count`

### Template sensors (new — append to `templates.yaml`)

- `sensor.meeting_room_temp`
- `sensor.mensa_temp`

### Derivative sensors (new — `sensors.yaml`)

- `sensor.meeting_room_temp_rate`
- `sensor.mensa_temp_rate`

### Automations (new — `automations.yaml`)

- `sun_shade_forecast_populator` — populates `input_number.shade_today_outdoor_max_forecast`
- `sun_shade_midnight_reset` — resets manual-override counters at 00:00:01
- `sun_shade_meeting_room` — blueprint instantiation for Meeting Room
- `sun_shade_mensa` — blueprint instantiation for Mensa

### Automations (removed — `automations.yaml`)

- `mensa_sun_shade` — replaced by `sun_shade_mensa`

### Automations (unchanged — `automations.yaml`)

- `cs_sun_shade` — out of scope, possible future migration

### Blueprints (new)

- `blueprints/automation/custom/intelligent_sun_shade.yaml`

### Remote triggers (new — created via `RemoteTrigger`)

- `sun-shade-evaluator-nightly` (cron `0 21 * * *`)
- `sun-shade-evaluator-morning` (cron `0 5 * * *`)

### Files (new — evaluator outputs)

- `homeassistant/eval-state.json` (initialized at deployment step 18, updated by both triggers)
- `docs/sun-shade-eval/YYYY-MM-DD.md` (written daily by the nightly trigger)
- `docs/sun-shade-eval/applied.log` (appended by the morning trigger on each `apply`)
- `docs/sun-shade-eval/ignored.log` (appended by the morning trigger on each `ignore` or `expired`)
