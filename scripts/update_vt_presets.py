#!/usr/bin/env python3
"""
Update Versatile Thermostat cool-mode preset temperatures in HA storage.

Run on the NAS as root (the docker-mounted .storage is owned by the HA
container UID, so sudo is required):

    cd /volume1/docker/PRODUCTION/homeassistant
    docker compose stop homeassistant
    sudo python3 scripts/update_vt_presets.py
    docker compose start homeassistant

The script writes a timestamped .bak alongside the original file before
patching, and refuses to run if HA is still up (lock file present).

Target preset values (after 2026-05-27 simplification):

    Offices (Dagmar, Tania, CS, Meeting, Projects 1, Projects 2, Reception):
        comfort_ac_temp = 25.5
        eco_ac_temp     = 29.0
        boost_ac_temp   = 24.0
        frost_ac_temp   = 30.0

    Common  (OpenSpace, Entrance):
        comfort_ac_temp = 27.0
        eco_ac_temp     = 29.0
        boost_ac_temp   = 25.0
        frost_ac_temp   = 30.0

    Mensa (common but lunch-boost specific):
        comfort_ac_temp = 27.0
        eco_ac_temp     = 29.0
        boost_ac_temp   = 24.5
        frost_ac_temp   = 30.0

The Summer Dynamic Temperature Adjustment automation is disabled separately
in automations.yaml so these fixed values stick.
"""
from __future__ import annotations

import datetime
import json
import shutil
import sys
from pathlib import Path

STORAGE_PATH = Path("homeassistant/data/.storage/core.config_entries")

# Map climate VT title (as it appears in the config_entry title field) to the
# target preset values. The titles below match what Versatile Thermostat sets
# at config-flow time; if the user has renamed any in HA UI, the lookup will
# miss and the script prints a warning.
OFFICE = dict(comfort_ac_temp=25.5, eco_ac_temp=29.0, boost_ac_temp=24.0, frost_ac_temp=30.0)
COMMON = dict(comfort_ac_temp=27.0, eco_ac_temp=29.0, boost_ac_temp=25.0, frost_ac_temp=30.0)
MENSA = dict(comfort_ac_temp=27.0, eco_ac_temp=29.0, boost_ac_temp=24.5, frost_ac_temp=30.0)

ZONE_PRESETS = {
    "Fancoil Dagmar": OFFICE,
    "Fancoil Tania": OFFICE,
    "Projects 1": OFFICE,
    "Projects 2": OFFICE,
    "Fancoil CS": OFFICE,
    "Fancoil Meeting": OFFICE,
    "Fancoil Reception": OFFICE,
    "Fancoil OpenSpace": COMMON,
    "Fancoil Entrance": COMMON,
    "Climate Mensa": MENSA,
}


def main() -> int:
    if not STORAGE_PATH.exists():
        print(f"ERROR: {STORAGE_PATH} not found. Run from repo root.", file=sys.stderr)
        return 2

    raw = STORAGE_PATH.read_text()
    data = json.loads(raw)

    backup = STORAGE_PATH.with_suffix(
        f".{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"
    )
    shutil.copy2(STORAGE_PATH, backup)
    print(f"Backup: {backup}")

    entries = data["data"]["entries"]
    matched: list[str] = []
    missing = set(ZONE_PRESETS)

    for entry in entries:
        if entry.get("domain") != "versatile_thermostat":
            continue
        title = entry.get("title", "")
        if title not in ZONE_PRESETS:
            continue
        targets = ZONE_PRESETS[title]
        data_block = entry.setdefault("data", {})
        for key, value in targets.items():
            data_block[key] = value
        matched.append(title)
        missing.discard(title)

    if missing:
        print(f"WARNING: VT entries not found for: {sorted(missing)}", file=sys.stderr)
        print("Has any of them been renamed in the HA UI?", file=sys.stderr)

    print(f"Patched {len(matched)} VT entries: {sorted(matched)}")
    STORAGE_PATH.write_text(json.dumps(data, indent=2))
    print(f"Wrote {STORAGE_PATH}. Restart HA to pick up the new preset values.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
