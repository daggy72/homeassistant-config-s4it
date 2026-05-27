option task = {name: "copy_wh1_customer", every: 1m, offset: 20s}

sourceBucket = "ha_longterm"
targetBucket = "wh1_customer"
org = "sales4it"

wh1EntityIds = [
  "warehouse_cell_min_temperature",
  "warehouse_cell_max_temperature",
  "warehouse_cell_manual_hold",
  "warehouse_cell_last_requested_profile",
  "warehouse_cell_last_requested_command",
  "wh1_temperature",
  "wh1_probe_s3_temperature",
  "wh1_setpoint",
  "wh1_alarm",
  "wh1_recording",
  "wh1_last_applied_profile",
  "wh1_last_profile_write",
  "wh1_last_profile_error",
]

wh1Measurements = [
  "climate.wh1_temperature_control",
  "binary_sensor.wh1_compressor",
  "binary_sensor.wh1_defrost_output",
  "binary_sensor.wh1_fan",
  "binary_sensor.wh1_light_output",
  "binary_sensor.wh1_alarm_relay",
  "binary_sensor.wh1_auxiliary_relay",
  "binary_sensor.wh1_hot_resistance",
  "switch.wh1_light",
  "switch.wh1_defrost",
]

sensorData =
  from(bucket: sourceBucket)
    |> range(start: -2m)
    |> filter(fn: (r) => exists r.entity_id and contains(value: r.entity_id, set: wh1EntityIds))

outputData =
  from(bucket: sourceBucket)
    |> range(start: -2m)
    |> filter(fn: (r) => contains(value: r._measurement, set: wh1Measurements))

union(tables: [sensorData, outputData])
  |> to(bucket: targetBucket, org: org)
