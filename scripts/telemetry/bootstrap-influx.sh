#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${INFLUXDB_CONTAINER:-HA_influxdb}"
HOST="${INFLUX_HOST:-http://127.0.0.1:8086}"
ORG="${INFLUXDB_ORG:-sales4it}"
MAIN_BUCKET="${INFLUXDB_BUCKET:-ha_longterm}"
CUSTOMER_BUCKET="${INFLUXDB_CUSTOMER_BUCKET:-wh1_customer}"
TASK_FILE="${INFLUXDB_TASK_FILE:-/opt/influxdb/tasks/copy_wh1_customer.flux}"
read -r -a DOCKER_CMD <<< "${DOCKER:-docker}"

if [[ -z "${INFLUXDB_ADMIN_TOKEN:-}" ]]; then
  echo "INFLUXDB_ADMIN_TOKEN is required in the environment." >&2
  exit 1
fi

docker_exec() {
  "${DOCKER_CMD[@]}" exec "$CONTAINER" "$@"
}

influx_cmd() {
  docker_exec influx "$@" --host "$HOST" --org "$ORG" --token "$INFLUXDB_ADMIN_TOKEN"
}

bucket_id() {
  local bucket="$1"
  influx_cmd bucket list --name "$bucket" --hide-headers | awk 'NR==1 {print $1}'
}

ensure_bucket() {
  local bucket="$1"
  if [[ -n "$(bucket_id "$bucket")" ]]; then
    echo "Bucket exists: $bucket" >&2
    return
  fi
  influx_cmd bucket create --name "$bucket" --retention 0 >/dev/null
  echo "Created bucket: $bucket" >&2
}

create_token() {
  local description="$1"
  shift
  influx_cmd auth create --description "$description" --json "$@"
}

token_from_json() {
  sed -n 's/.*"token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p'
}

ensure_bucket "$MAIN_BUCKET"
ensure_bucket "$CUSTOMER_BUCKET"

MAIN_BUCKET_ID="$(bucket_id "$MAIN_BUCKET")"
CUSTOMER_BUCKET_ID="$(bucket_id "$CUSTOMER_BUCKET")"

if [[ -z "$MAIN_BUCKET_ID" || -z "$CUSTOMER_BUCKET_ID" ]]; then
  echo "Could not resolve bucket IDs." >&2
  exit 1
fi

HA_WRITE_TOKEN="$(create_token homeassistant-write-ha-longterm --write-bucket "$MAIN_BUCKET_ID" | token_from_json)"
GRAFANA_READ_TOKEN="$(create_token grafana-read-ha-longterm --read-bucket "$MAIN_BUCKET_ID" | token_from_json)"
WH1_READ_TOKEN="$(create_token grafana-read-wh1-customer --read-bucket "$CUSTOMER_BUCKET_ID" | token_from_json)"

echo
echo "# Add these lines to /volume1/docker/homeassistant/.env"
echo "INFLUXDB_GRAFANA_READ_TOKEN=$GRAFANA_READ_TOKEN"
echo "INFLUXDB_WH1_READ_TOKEN=$WH1_READ_TOKEN"
echo
echo "# Add this line to /volume1/docker/homeassistant/homeassistant/config/secrets.yaml"
echo "influxdb_ha_write_token: $HA_WRITE_TOKEN"
echo

if docker_exec test -f "$TASK_FILE"; then
  if influx_cmd task list --hide-headers | awk '{print $2}' | grep -qx "copy_wh1_customer"; then
    echo "Task exists: copy_wh1_customer" >&2
  else
    influx_cmd task create --file "$TASK_FILE" >/dev/null
    echo "Created task: copy_wh1_customer" >&2
  fi
else
  echo "Task file not found in container: $TASK_FILE" >&2
fi
