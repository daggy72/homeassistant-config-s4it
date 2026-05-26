# Warehouse Cell Watchdogs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add temporary Home Assistant watchdog monitoring for the NECTOR warehouse cell over the next 48 to 72 hours.

**Architecture:** Use YAML helpers and automations in the existing HA config repo. The watchdog reads existing NECTOR sensors and helper settings, creates persistent notifications only for actionable conditions, and stores a compact dashboard status helper.

**Tech Stack:** Home Assistant YAML automations, input helpers, Lovelace YAML dashboard, persistent notifications, logbook.

---

### Task 1: Add Watchdog Helpers

**Files:**
- Modify: `homeassistant/config/input_booleans.yaml`
- Modify: `homeassistant/config/input_datetimes.yaml`
- Modify: `homeassistant/config/input_texts.yaml`

- [ ] Add `warehouse_cell_watchdog_enabled` with initial state on.
- [ ] Add `warehouse_cell_watchdog_until` with date and time, initialized to `2026-05-29 23:59:00`.
- [ ] Add `warehouse_cell_watchdog_last_status` with max length 255.
- [ ] Verify helper names match the automation exactly using `rg -n "warehouse_cell_watchdog" homeassistant/config`.

### Task 2: Add Watchdog Automations

**Files:**
- Modify: `homeassistant/config/automations.yaml`

- [ ] Add `warehouse_cell_watchdog_monitor` after `warehouse_cell_profile_guard`.
- [ ] Trigger it on HA start, every 15 minutes, temperature changes, profile/error changes, output changes, helper changes, and manual-hold changes.
- [ ] Gate it behind `input_boolean.warehouse_cell_watchdog_enabled` and `input_datetime.warehouse_cell_watchdog_until`.
- [ ] Compute warning and critical messages from the current min/max, S1, S3, active profile, last profile error, manual hold, compressor, fan, and hot resistance.
- [ ] Update `input_text.warehouse_cell_watchdog_last_status` on every run.
- [ ] Create/update persistent notification `warehouse_cell_watchdog` when messages exist, otherwise dismiss it.
- [ ] Add `warehouse_cell_watchdog_heartbeat` at `08:00:00` and `20:00:00`, using persistent notification id `warehouse_cell_watchdog_heartbeat`.

### Task 3: Expose Watchdog State On The Climate Dashboard

**Files:**
- Modify: `homeassistant/config/dashboards/climate.yaml`

- [ ] Add a Watchdog section in the Warehouse Cell card.
- [ ] Show enabled, expiry, and last status helpers.

### Task 4: Verify, Commit, Deploy

**Files:**
- All changed files.

- [ ] Run `git diff --check`.
- [ ] Pull the branch into the NAS config or merge to main and deploy.
- [ ] Run `docker exec HA_homeassistant python -m homeassistant --script check_config --config /config`.
- [ ] Reload input helpers and automations, or restart HA if helper reload is unavailable.
- [ ] Trigger `automation.warehouse_cell_watchdog_monitor` once.
- [ ] Verify watchdog status helper updates and HA logs do not show NECTOR or automation template errors.
- [ ] Commit and push the changes.
