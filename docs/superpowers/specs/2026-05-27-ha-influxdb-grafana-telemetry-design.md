# Home Assistant Long-Term Telemetry Design

## Goal

Record multi-year climate and warehouse-cell telemetry outside Home Assistant's recorder so the building behavior can be analyzed over seasons and used for future heat-pump automation.

## Direction

Use Home Assistant's InfluxDB integration to export an allowlisted set of state changes to InfluxDB 2.x. Use Grafana for dashboards and customer views.

Home Assistant remains the control plane. InfluxDB is only the time-series store. Grafana is only the visualization and reporting layer.

## Buckets

- `ha_longterm`: internal building telemetry from Home Assistant.
- `wh1_customer`: WH1-only customer-safe telemetry copied from `ha_longterm`.

The WH1 customer bucket prevents customer dashboards from querying unrelated room, fancoil, weather, or building-control data.

## Collected Data

Warehouse cell:

- S1 ambient temperature.
- S3 probe temperature.
- NECTOR setpoint.
- NECTOR profile/write/error states.
- Compressor, fan, hot resistance, defrost, alarm, auxiliary, and light outputs.
- Operator min/max helpers and manual hold.

Building climate:

- Versatile Thermostat climate entities.
- EMA temperature, temperature slope, power percent, valve open percent, on/off time, mean power cycle, and energy sensors.
- Fancoil target output numbers and fan entities.
- Safety, bypass, presence, and motion state where relevant to HVAC behavior.
- Chiller switch and power/energy.

Weather and solar context:

- Outdoor temperature.
- Forecast max helper.
- Cloud coverage template sensor.
- Weather entities for later query refinement.

## Customer Access

Run a separate Grafana instance for the customer view. Its data source should use a read token scoped only to `wh1_customer`. This gives a stronger isolation boundary than hiding panels in a shared Grafana instance.

The customer Grafana should be exposed through the existing Cloudflare/reverse-proxy path only after local data flow is verified.

## Retention

Phase 1 keeps raw data indefinitely. If disk growth becomes meaningful, add downsampled buckets later:

- 1-minute raw for 90 days.
- 15-minute aggregates for multi-year trend analysis.

## Verification

- Home Assistant config check passes.
- InfluxDB health endpoint returns ready.
- Home Assistant writes at least one WH1 temperature point.
- Grafana data source health checks pass.
- Internal and customer dashboards render data.
