# Home Assistant InfluxDB/Grafana Telemetry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a deployable InfluxDB/Grafana telemetry stack around the existing Home Assistant Docker deployment.

**Architecture:** Home Assistant exports selected state changes to InfluxDB 2.x. Internal Grafana reads all telemetry. Customer Grafana reads only the WH1 customer bucket.

---

### Task 1: Add Docker Services

**Files:**
- Modify: `docker-compose.yaml`

- [ ] Add `influxdb` using `influxdb:2.7`.
- [ ] Bind InfluxDB to host loopback port `8086` so Home Assistant host networking can write locally.
- [ ] Add `grafana-internal` on loopback port `3000`.
- [ ] Add `grafana-wh1` on loopback port `3001`.
- [ ] Store runtime data under `${DOCKER_BASE}` and keep dashboards/provisioning in the repo.

### Task 2: Add Home Assistant Export Config

**Files:**
- Modify: `homeassistant/config/configuration.yaml`
- Add: `homeassistant/config/influxdb.yaml`
- Modify: `homeassistant/config/templates.yaml`

- [ ] Include `influxdb.yaml`.
- [ ] Configure InfluxDB 2.x with the HA write token from secrets.
- [ ] Use an explicit include allowlist for WH1, climate, fancoil, chiller, outside temperature, forecast, and helper entities.
- [ ] Add an `Outdoor Cloud Coverage` template sensor.

### Task 3: Add Grafana Provisioning And Dashboards

**Files:**
- Add files under `grafana/internal/`.
- Add files under `grafana/customer/`.

- [ ] Provision internal Grafana with the `ha_longterm` datasource.
- [ ] Provision customer Grafana with the `wh1_customer` datasource.
- [ ] Add an internal building telemetry dashboard.
- [ ] Add a WH1 customer dashboard.

### Task 4: Add Bucket/Token Bootstrap

**Files:**
- Add: `scripts/telemetry/bootstrap-influx.sh`
- Add: `influxdb/tasks/copy_wh1_customer.flux`

- [ ] Create/verify the WH1 customer bucket.
- [ ] Create scoped tokens for HA write, internal Grafana read, and customer Grafana read.
- [ ] Document where to place the generated tokens.
- [ ] Add a Flux task that copies WH1-only points into `wh1_customer`.

### Task 5: Verify And Deploy

- [ ] Run `git diff --check`.
- [ ] Validate YAML/JSON syntax locally.
- [ ] Run `docker compose config`.
- [ ] Deploy InfluxDB first, run the bootstrap script, then deploy Grafana and restart Home Assistant.
- [ ] Confirm InfluxDB receives WH1 data.
- [ ] Confirm Grafana dashboards render.
