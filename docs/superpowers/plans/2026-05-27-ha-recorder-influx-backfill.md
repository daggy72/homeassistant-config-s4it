# HA Recorder Influx Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backfill retained Home Assistant recorder history into InfluxDB/Grafana without altering raw measured temperatures.

**Architecture:** Add one focused Python script that runs inside the Home Assistant container, reads `/config/home-assistant_v2.db` read-only, and writes selected historical recorder points to InfluxDB with original timestamps. Raw recorder values are preserved; the chaotic WH1 period is represented by explicit quality marker points and a dashboard note, not by modifying measurements.

**Tech Stack:** Python standard library, Home Assistant SQLite recorder DB, InfluxDB 2 HTTP write API, existing Grafana JSON dashboards.

---

### Task 1: Backfill Script

**Files:**
- Create: `scripts/telemetry/backfill-ha-recorder.py`
- Create: `tests/test_backfill_ha_recorder.py`

- [ ] **Step 1: Add unit tests for line protocol escaping and field conversion**

Run: `python3 -m unittest tests/test_backfill_ha_recorder.py`

Expected before implementation: import/function errors.

- [ ] **Step 2: Implement script**

The script must:

- Parse `homeassistant/config/influxdb.yaml` include entities and globs.
- Select matching `states_meta` and `statistics_meta` rows.
- Write raw recorder states for retained detailed history.
- Write older long-term statistics as hourly `value=mean` points.
- Map sensor measurements to unit measurements such as `°C` and `%`, matching Home Assistant's Influx style.
- Map binary/fan/switch states to `value=1/0`.
- Write WH1 quality marker points to `ha_longterm` and `wh1_customer`.
- Support `--dry-run`, `--states-start`, `--states-end`, `--stats-start`, `--stats-end`, `--quality-start`, and `--quality-end`.

- [ ] **Step 3: Run tests**

Run: `python3 -m unittest tests/test_backfill_ha_recorder.py`

Expected: all tests pass.

### Task 2: Dashboard Transparency

**Files:**
- Modify: `grafana/customer/dashboards/wh1-customer.json`
- Modify: `grafana/internal/dashboards/building-telemetry.json`
- Modify: `docs/climate/telemetry.md`

- [ ] **Step 1: Add a visible WH1 data quality note**

Add a text panel that states raw values are preserved and that 2026-05-24 through 2026-05-27 contains a known S1/S3 sensor-positioning/control-oscillation period.

- [ ] **Step 2: Validate JSON**

Run:

```bash
python3 -m json.tool grafana/customer/dashboards/wh1-customer.json >/tmp/wh1.json
python3 -m json.tool grafana/internal/dashboards/building-telemetry.json >/tmp/internal.json
```

Expected: both commands exit 0.

### Task 3: Execute Backfill

**Files:**
- No committed config changes after script/docs.

- [ ] **Step 1: Dry-run on NAS**

Run the script inside `HA_homeassistant` with `--dry-run` and confirm selected row counts are plausible.

- [ ] **Step 2: Execute on NAS**

Run the script with `INFLUX_TOKEN=$INFLUXDB_ADMIN_TOKEN` and the chosen quality period:

```bash
--quality-start 2026-05-24T00:00:00+02:00
--quality-end 2026-05-27T10:45:00+02:00
```

- [ ] **Step 3: Verify Influx**

Query `ha_longterm` and `wh1_customer` for pre-live WH1 points and `telemetry_quality` points.

### Task 4: Commit, Push, Deploy

**Files:**
- Commit all script/docs/dashboard changes.

- [ ] **Step 1: Commit and push**

Commit message: `Add HA recorder backfill tooling`

- [ ] **Step 2: Pull on NAS and restart Grafana**

Restart Grafana containers to pick up dashboard JSON changes.

- [ ] **Step 3: Final verification**

Verify:

- HA config still passes.
- Backfilled WH1 points exist before live Influx start.
- WH1 customer bucket has backfilled WH1 data.
- Customer dashboard still loads.
