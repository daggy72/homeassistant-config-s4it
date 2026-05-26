# Warehouse Cell Watchdog Design

## Goal

For the next 48 to 72 hours, Home Assistant should actively watch the PEGO NECTOR warehouse cell configuration, temperatures, and key output states so unexpected drift or failed profile writes are visible without constantly checking the dashboard.

## Scope

This is a Home Assistant configuration-only change. The `nector200` custom integration remains unchanged.

## Behavior

- Add an operator-controlled watchdog enable helper.
- Add an expiry helper initialized to `2026-05-29 23:59:00`, roughly 72 hours from the evening deployment on `2026-05-26`.
- Every 15 minutes, and after Home Assistant start, evaluate:
  - S1 ambient temperature against the configured min/max helpers.
  - Whether the NECTOR profile is a known guard profile.
  - Whether the last profile write reports an active error.
  - Whether compressor cooling and hot resistance heating are active together.
  - Whether manual hold is active.
- Create or update a persistent notification when a warning or critical condition exists.
- Dismiss the watchdog alert notification when the system returns to normal.
- Twice daily, create a heartbeat persistent notification with the current temperatures, profile, limits, and output states.
- Write a compact status string to an input text helper so the climate dashboard shows the last watchdog evaluation.

## Thresholds

- High warning: S1 is above `max + 0.8 C`.
- High critical: S1 is above `max + 1.5 C`.
- Low warning: S1 is below `min - 0.3 C`.
- Low critical: S1 is below `min - 0.5 C`.
- Profile warning: active profile is not `cooling_guard` or `heating_guard` while manual hold is off.
- Error warning: `sensor.wh1_last_profile_error` contains a real value other than `unknown`, `unavailable`, `none`, or blank.
- Output warning: compressor and hot resistance are both on.

## Verification

- Run a YAML/config syntax check with Home Assistant after deployment.
- Reload helpers and automations.
- Trigger the watchdog automation once manually.
- Confirm no NECTOR integration errors are produced and the watchdog status helper updates.
