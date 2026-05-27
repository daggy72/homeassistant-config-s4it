# Climate Telemetry Stack

## Purpose

The telemetry stack records long-term Home Assistant climate data in InfluxDB and exposes dashboards in Grafana.

Use it for:

- WH1 temperature-controlled storage history and customer monitoring.
- Building heat/cool behavior analysis.
- Fancoil demand, cycling, and room response analysis.
- Weather and cloud-cover correlation before future heat-pump automation.

## Services

| Service | Container | Local URL | Purpose |
| --- | --- | --- | --- |
| InfluxDB | `HA_influxdb` | `http://127.0.0.1:8086` | Time-series storage |
| Grafana internal | `HA_grafana_internal` | `http://127.0.0.1:13000` | Internal building dashboards |
| Grafana WH1 | `HA_grafana_wh1` | `http://10.0.10.10:13001` | Customer-safe WH1 dashboard |

The internal Grafana port is bound to loopback. WH1 Grafana is bound on host port `13001` so Cloudflare Tunnel can expose only that customer-safe Grafana instance.

## Buckets

| Bucket | Contents | Access |
| --- | --- | --- |
| `ha_longterm` | Full allowlisted Home Assistant telemetry | Internal only |
| `wh1_customer` | WH1-only copied telemetry | Customer Grafana read-only |

## Required Secrets

`/volume1/docker/homeassistant/.env` must contain:

```bash
INFLUXDB_ORG=sales4it
INFLUXDB_BUCKET=ha_longterm
INFLUXDB_CUSTOMER_BUCKET=wh1_customer
INFLUXDB_ADMIN_USER=admin
INFLUXDB_ADMIN_PASSWORD=...
INFLUXDB_ADMIN_TOKEN=...
GRAFANA_ADMIN_PASSWORD=...
GRAFANA_WH1_ADMIN_PASSWORD=...
INFLUXDB_GRAFANA_READ_TOKEN=...
INFLUXDB_WH1_READ_TOKEN=...
```

`/volume1/docker/homeassistant/homeassistant/config/secrets.yaml` must contain:

```yaml
influxdb_ha_write_token: ...
```

## First Deploy

1. Add the initial admin and Grafana passwords/tokens to `.env`.
2. Start InfluxDB:

   ```bash
   cd /volume1/docker/homeassistant
   docker compose up -d influxdb
   ```

3. Create scoped tokens and the WH1 copy task:

   ```bash
   set -a
   . ./.env
   set +a
   ./scripts/telemetry/bootstrap-influx.sh
   ```

4. Add the generated Grafana tokens to `.env` and the generated HA write token to `secrets.yaml`.
5. Start Grafana:

   ```bash
   docker compose up -d grafana-internal grafana-wh1
   ```

6. Restart Home Assistant so the `influxdb:` integration is loaded:

   ```bash
   docker exec HA_homeassistant python -m homeassistant --script check_config --config /config
   docker restart HA_homeassistant
   ```

## Verification

Check InfluxDB health:

```bash
curl -fsS http://127.0.0.1:8086/health
```

Check that WH1 data is arriving:

```bash
docker exec HA_influxdb influx query \
  --org sales4it \
  --token "$INFLUXDB_ADMIN_TOKEN" \
  'from(bucket:"ha_longterm") |> range(start:-15m) |> filter(fn:(r) => r.entity_id == "wh1_temperature") |> last()'
```

Then open the internal and WH1 Grafana dashboards through the local port or the configured reverse-proxy path.

## Recorder Backfill

Use `scripts/telemetry/backfill-ha-recorder.py` to import retained Home Assistant recorder history into InfluxDB. Run it inside the Home Assistant container so SQLite reads `/config/home-assistant_v2.db` locally.

The backfill preserves raw measurements. Known data-quality periods, such as the WH1 S1/S3 sensor-positioning and NECTOR control-oscillation period from 24-27 May 2026, are represented with `telemetry_quality` marker points and dashboard notes rather than edited temperature values.

## Customer Route

Cloudflare Tunnel routes are managed in the Cloudflare dashboard, not this repo. Add a public hostname such as `wh1.sales4.it` with:

- Type: `HTTP`
- URL: `10.0.10.10:13001`

Give customers a Viewer account in `HA_grafana_wh1`, not the admin account.
