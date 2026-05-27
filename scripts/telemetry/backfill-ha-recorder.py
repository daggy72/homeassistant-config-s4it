#!/usr/bin/env python3
"""Backfill Home Assistant recorder history into InfluxDB 2.

Run this inside the Home Assistant container so `/config/home-assistant_v2.db`
is local SQLite storage, not an SMB-mounted file.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import math
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


BOOL_STATES = {
    "on": 1.0,
    "off": 0.0,
    "open": 1.0,
    "closed": 0.0,
    "true": 1.0,
    "false": 0.0,
    "home": 1.0,
    "not_home": 0.0,
}

SKIP_STATES = {"unknown", "unavailable", "none", ""}

NUMERIC_ATTRIBUTE_ALLOWLIST = {
    "current_temperature",
    "temperature",
    "target_temperature",
    "target_temp_low",
    "target_temp_high",
    "valve_open_percent",
    "power_percent",
    "current_power",
    "percentage",
    "brightness",
    "min_temp",
    "max_temp",
    "humidity",
}


@dataclass(frozen=True)
class IncludeConfig:
    entities: set[str]
    globs: list[str]

    def matches(self, entity_id: str) -> bool:
        return entity_id in self.entities or any(
            fnmatch.fnmatch(entity_id, pattern) for pattern in self.globs
        )


def parse_iso(value: str | None) -> float | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).timestamp()


def parse_include_config(path: Path) -> IncludeConfig:
    entities: set[str] = set()
    globs: list[str] = []
    mode: str | None = None

    for raw_line in path.read_text().splitlines():
        stripped = raw_line.strip()
        if stripped == "entities:":
            mode = "entities"
            continue
        if stripped == "entity_globs:":
            mode = "globs"
            continue
        if mode and re.match(r"^[A-Za-z_][A-Za-z0-9_]*:", stripped) and not stripped.startswith("- "):
            mode = None
        if not mode or not stripped.startswith("- "):
            continue
        value = stripped[2:].strip().strip("'\"")
        if mode == "entities":
            entities.add(value)
        else:
            globs.append(value)

    return IncludeConfig(entities=entities, globs=globs)


def escape_key(value: str) -> str:
    return value.replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,")


def escape_tag(value: str) -> str:
    return escape_key(value).replace("=", "\\=")


def escape_string_field(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def field_value(value: object) -> str | None:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value}i"
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return repr(value)
    if isinstance(value, str):
        return escape_string_field(value)
    return None


def to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def object_id(entity_id: str) -> str:
    return entity_id.split(".", 1)[1] if "." in entity_id else entity_id


def domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else "unknown"


def measurement_for(entity_id: str, attrs: dict[str, object] | None) -> str:
    attrs = attrs or {}
    unit = attrs.get("unit_of_measurement")
    if domain(entity_id) == "sensor" and isinstance(unit, str) and unit:
        return unit
    return entity_id


def line_protocol(
    measurement: str,
    tags: dict[str, str],
    fields: dict[str, object],
    timestamp_s: float,
) -> str | None:
    encoded_fields = []
    for key, value in fields.items():
        encoded = field_value(value)
        if encoded is not None:
            encoded_fields.append(f"{escape_key(key)}={encoded}")
    if not encoded_fields:
        return None

    encoded_tags = "".join(
        f",{escape_key(key)}={escape_tag(value)}"
        for key, value in sorted(tags.items())
        if value != ""
    )
    return (
        f"{escape_key(measurement)}{encoded_tags} "
        f"{','.join(encoded_fields)} {int(timestamp_s)}"
    )


def read_attrs(shared_attrs: str | None) -> dict[str, object]:
    if not shared_attrs:
        return {}
    try:
        attrs = json.loads(shared_attrs)
    except json.JSONDecodeError:
        return {}
    return attrs if isinstance(attrs, dict) else {}


def state_fields(state: str, attrs: dict[str, object]) -> dict[str, object]:
    lowered = state.lower()
    if lowered in SKIP_STATES:
        return {}

    fields: dict[str, object] = {}
    numeric_state = to_float(state)
    if numeric_state is not None:
        fields["value"] = numeric_state
    elif lowered in BOOL_STATES:
        fields["value"] = BOOL_STATES[lowered]
        fields["state"] = state
    else:
        fields["state"] = state

    for key in NUMERIC_ATTRIBUTE_ALLOWLIST:
        if key in attrs:
            value = to_float(attrs[key])
            if value is not None:
                fields[key] = value

    return fields


def selected_metadata(
    con: sqlite3.Connection, table: str, id_col: str, entity_col: str, include: IncludeConfig
) -> dict[int, str]:
    rows = con.execute(f"select {id_col}, {entity_col} from {table}").fetchall()
    return {int(row[0]): str(row[1]) for row in rows if include.matches(str(row[1]))}


def batched(items: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def write_lines(
    influx_url: str,
    org: str,
    bucket: str,
    token: str,
    lines: list[str],
    dry_run: bool,
) -> None:
    if dry_run or not lines:
        return
    query = urllib.parse.urlencode({"org": org, "bucket": bucket, "precision": "s"})
    url = f"{influx_url.rstrip('/')}/api/v2/write?{query}"
    request = urllib.request.Request(
        url,
        data=("\n".join(lines) + "\n").encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "text/plain; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"Influx write failed for {bucket}: {exc.code} {body}") from exc


def is_wh1_entity(entity_id: str) -> bool:
    return (
        entity_id.startswith("sensor.wh1_")
        or entity_id.startswith("binary_sensor.wh1_")
        or entity_id.startswith("switch.wh1_")
        or entity_id == "climate.wh1_temperature_control"
        or entity_id.startswith("input_number.warehouse_cell_")
        or entity_id.startswith("input_boolean.warehouse_cell_")
        or entity_id.startswith("input_text.warehouse_cell_")
    )


def entity_tags(entity_id: str, attrs: dict[str, object], kind: str) -> dict[str, str]:
    tags = {
        "domain": domain(entity_id),
        "entity_id": object_id(entity_id),
        "backfill": kind,
        "source": "homeassistant",
        "site": "cassano",
    }
    friendly_name = attrs.get("friendly_name")
    if isinstance(friendly_name, str) and friendly_name:
        tags["friendly_name"] = friendly_name
    return tags


def backfill_states(
    con: sqlite3.Connection,
    metadata: dict[int, str],
    args: argparse.Namespace,
) -> tuple[int, int]:
    if not metadata:
        return 0, 0

    metadata_ids = list(metadata)
    start = parse_iso(args.states_start)
    end = parse_iso(args.states_end)
    filters = [f"s.metadata_id in ({','.join('?' for _ in metadata_ids)})"]
    params: list[object] = metadata_ids[:]
    if start is not None:
        filters.append("s.last_updated_ts >= ?")
        params.append(start)
    if end is not None:
        filters.append("s.last_updated_ts < ?")
        params.append(end)

    query = f"""
        select s.last_updated_ts, m.entity_id, s.state, a.shared_attrs
        from states s
        join states_meta m on m.metadata_id = s.metadata_id
        left join state_attributes a on a.attributes_id = s.attributes_id
        where {' and '.join(filters)}
        order by s.last_updated_ts
    """

    total = 0
    customer_total = 0
    lines: list[str] = []
    customer_lines: list[str] = []
    for timestamp_s, entity_id, state, shared_attrs in con.execute(query, params):
        attrs = read_attrs(shared_attrs)
        fields = state_fields(str(state), attrs)
        line = line_protocol(
            measurement_for(str(entity_id), attrs),
            entity_tags(str(entity_id), attrs, "recorder_raw"),
            fields,
            float(timestamp_s),
        )
        if not line:
            continue
        lines.append(line)
        total += 1
        if args.customer_bucket and is_wh1_entity(str(entity_id)):
            customer_lines.append(line)
            customer_total += 1
        if len(lines) >= args.batch_size:
            write_lines(args.influx_url, args.org, args.bucket, args.token, lines, args.dry_run)
            write_lines(
                args.influx_url,
                args.org,
                args.customer_bucket,
                args.token,
                customer_lines,
                args.dry_run,
            )
            lines.clear()
            customer_lines.clear()

    write_lines(args.influx_url, args.org, args.bucket, args.token, lines, args.dry_run)
    write_lines(
        args.influx_url,
        args.org,
        args.customer_bucket,
        args.token,
        customer_lines,
        args.dry_run,
    )
    return total, customer_total


def backfill_statistics(
    con: sqlite3.Connection,
    metadata: dict[int, str],
    args: argparse.Namespace,
) -> tuple[int, int]:
    if not metadata:
        return 0, 0

    metadata_ids = list(metadata)
    start = parse_iso(args.stats_start)
    end = parse_iso(args.stats_end)
    filters = [f"s.metadata_id in ({','.join('?' for _ in metadata_ids)})"]
    params: list[object] = metadata_ids[:]
    if start is not None:
        filters.append("s.start_ts >= ?")
        params.append(start)
    if end is not None:
        filters.append("s.start_ts < ?")
        params.append(end)

    query = f"""
        select s.start_ts, m.statistic_id, m.unit_of_measurement,
               s.mean, s.min, s.max, s.state, s.sum
        from statistics s
        join statistics_meta m on m.id = s.metadata_id
        where {' and '.join(filters)}
        order by s.start_ts
    """

    total = 0
    customer_total = 0
    lines: list[str] = []
    customer_lines: list[str] = []
    for timestamp_s, entity_id, unit, mean, minimum, maximum, state, total_sum in con.execute(query, params):
        value = mean if mean is not None else state
        fields = {
            "value": to_float(value),
            "mean": to_float(mean),
            "min": to_float(minimum),
            "max": to_float(maximum),
            "state": to_float(state),
            "sum": to_float(total_sum),
        }
        fields = {key: val for key, val in fields.items() if val is not None}
        attrs = {"unit_of_measurement": unit} if unit else {}
        line = line_protocol(
            measurement_for(str(entity_id), attrs),
            entity_tags(str(entity_id), attrs, "recorder_statistics"),
            fields,
            float(timestamp_s),
        )
        if not line:
            continue
        lines.append(line)
        total += 1
        if args.customer_bucket and is_wh1_entity(str(entity_id)):
            customer_lines.append(line)
            customer_total += 1
        if len(lines) >= args.batch_size:
            write_lines(args.influx_url, args.org, args.bucket, args.token, lines, args.dry_run)
            write_lines(
                args.influx_url,
                args.org,
                args.customer_bucket,
                args.token,
                customer_lines,
                args.dry_run,
            )
            lines.clear()
            customer_lines.clear()

    write_lines(args.influx_url, args.org, args.bucket, args.token, lines, args.dry_run)
    write_lines(
        args.influx_url,
        args.org,
        args.customer_bucket,
        args.token,
        customer_lines,
        args.dry_run,
    )
    return total, customer_total


def quality_lines(start: str | None, end: str | None) -> list[str]:
    if not start or not end:
        return []
    start_ts = parse_iso(start)
    end_ts = parse_iso(end)
    if start_ts is None or end_ts is None:
        return []
    tags = {
        "scope": "wh1",
        "entity_id": "wh1_temperature",
        "issue": "sensor_positioning_control_oscillation",
        "source": "homeassistant",
        "site": "cassano",
    }
    return [
        line_protocol(
            "telemetry_quality",
            tags,
            {
                "value": 1,
                "note": "Known WH1 S1/S3 sensor-positioning and NECTOR control-oscillation period; raw measurements preserved.",
            },
            start_ts,
        ),
        line_protocol(
            "telemetry_quality",
            tags,
            {
                "value": 0,
                "note": "WH1 S1/S3 sensors repositioned; raw measurements preserved.",
            },
            end_ts,
        ),
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="/config/home-assistant_v2.db")
    parser.add_argument("--config", default="/config/influxdb.yaml")
    parser.add_argument("--influx-url", default=os.getenv("INFLUX_URL", "http://127.0.0.1:8086"))
    parser.add_argument("--org", default=os.getenv("INFLUXDB_ORG", "sales4it"))
    parser.add_argument("--bucket", default=os.getenv("INFLUXDB_BUCKET", "ha_longterm"))
    parser.add_argument("--customer-bucket", default=os.getenv("INFLUXDB_CUSTOMER_BUCKET", "wh1_customer"))
    parser.add_argument("--token", default=os.getenv("INFLUX_TOKEN") or os.getenv("INFLUXDB_ADMIN_TOKEN"))
    parser.add_argument("--states-start")
    parser.add_argument("--states-end")
    parser.add_argument("--stats-start")
    parser.add_argument("--stats-end")
    parser.add_argument("--quality-start")
    parser.add_argument("--quality-end")
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.dry_run and not args.token:
        print("INFLUX_TOKEN or INFLUXDB_ADMIN_TOKEN is required unless --dry-run is used.", file=sys.stderr)
        return 2

    include = parse_include_config(Path(args.config))
    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    state_metadata = selected_metadata(con, "states_meta", "metadata_id", "entity_id", include)
    stat_metadata = selected_metadata(con, "statistics_meta", "id", "statistic_id", include)

    print(f"selected_state_entities={len(state_metadata)}")
    print(f"selected_statistic_entities={len(stat_metadata)}")

    stats_total, stats_customer = backfill_statistics(con, stat_metadata, args)
    states_total, states_customer = backfill_states(con, state_metadata, args)
    quality = [line for line in quality_lines(args.quality_start, args.quality_end) if line]
    if quality:
        write_lines(args.influx_url, args.org, args.bucket, args.token, quality, args.dry_run)
        write_lines(args.influx_url, args.org, args.customer_bucket, args.token, quality, args.dry_run)

    print(f"statistics_points={stats_total}")
    print(f"statistics_customer_points={stats_customer}")
    print(f"state_points={states_total}")
    print(f"state_customer_points={states_customer}")
    print(f"quality_points={len(quality)}")
    print(f"dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
