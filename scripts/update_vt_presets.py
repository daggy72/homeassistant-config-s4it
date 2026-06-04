#!/usr/bin/env python3
"""
Update Versatile Thermostat cool-mode preset temperatures + motion config
in HA storage.

Run on the NAS as root (the docker-mounted .storage is owned by the HA
container UID, so sudo is required):

    cd /volume1/docker/homeassistant
    docker compose stop homeassistant
    sudo python3 scripts/update_vt_presets.py
    docker compose start homeassistant

The script writes a timestamped .bak alongside the original file before
patching, and refuses to run if HA is still up (lock file present).

Target preset values (after 2026-05-27 simplification):

    Offices (Dagmar, Tania, CS, Meeting, Projects 1, Reception):
        comfort_ac_temp = 25.5
        eco_ac_temp     = 29.0
        boost_ac_temp   = 24.0
        frost_ac_temp   = 30.0

    Common  (OpenSpace, Entrance, Projects 2):
        comfort_ac_temp = 27.0
        eco_ac_temp     = 29.0
        boost_ac_temp   = 25.0
        frost_ac_temp   = 30.0

    Mensa (common but lunch-boost specific):
        comfort_ac_temp = 27.0
        eco_ac_temp     = 29.0
        boost_ac_temp   = 24.5
        frost_ac_temp   = 30.0

Motion-override config (added 2026-06-04) for Meeting / CS / Reception:
    use_motion_feature=True, motion_preset=comfort, no_motion_preset=eco,
    motion_delay=30s on, motion_off_delay=300s (5 min) off.
    activity_ac_temp set to match comfort so the manual activity preset
    also pulls cooling.

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
    # Projects 2 is unoccupied and shares the Mensa sensor, so use the common-room
    # preset (comfort 27 / eco 29) rather than office (25.5 / 29). Flip back to
    # OFFICE if/when occupancy returns. See memory: projects2-unoccupied-tracks-mensa.
    "Projects 2": COMMON,
    "Fancoil CS": OFFICE,
    "Fancoil Meeting": OFFICE,
    "Fancoil Reception": OFFICE,
    "Fancoil OpenSpace": COMMON,
    "Fancoil Entrance": COMMON,
    "Climate Mensa": MENSA,
}

# Motion-override config: when motion fires, VT swaps preset to motion_preset
# (comfort); when motion clears for motion_off_delay seconds, VT swaps to
# no_motion_preset (eco). Applied per-VT (use_motion_central_config=False).
# Also sets activity_ac_temp so the manual `activity` preset pulls cooling.
MOTION_OVERRIDE = {
    "Fancoil Meeting": {
        "use_motion_feature": True,
        "use_motion_central_config": False,
        "motion_sensor_entity_id": "binary_sensor.mt_meeting_room_up_sense_motion",
        "motion_delay": 30,
        "motion_off_delay": 300,
        "motion_preset": "comfort",
        "no_motion_preset": "eco",
        "activity_ac_temp": 25.5,
    },
    "Fancoil CS": {
        "use_motion_feature": True,
        "use_motion_central_config": False,
        "motion_sensor_entity_id": "binary_sensor.cc_up_sense_motion",
        "motion_delay": 30,
        "motion_off_delay": 300,
        "motion_preset": "comfort",
        "no_motion_preset": "eco",
        "activity_ac_temp": 25.5,
    },
    "Fancoil Reception": {
        "use_motion_feature": True,
        "use_motion_central_config": False,
        "motion_sensor_entity_id": "binary_sensor.reception_up_sense_motion",
        "motion_delay": 30,
        "motion_off_delay": 300,
        "motion_preset": "comfort",
        "no_motion_preset": "eco",
        "activity_ac_temp": 25.5,
    },
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
    motion_matched: list[str] = []
    motion_missing = set(MOTION_OVERRIDE)

    for entry in entries:
        if entry.get("domain") != "versatile_thermostat":
            continue
        title = entry.get("title", "")
        data_block = entry.setdefault("data", {})
        if title in ZONE_PRESETS:
            for key, value in ZONE_PRESETS[title].items():
                data_block[key] = value
            matched.append(title)
            missing.discard(title)
        if title in MOTION_OVERRIDE:
            for key, value in MOTION_OVERRIDE[title].items():
                data_block[key] = value
            motion_matched.append(title)
            motion_missing.discard(title)

    if missing:
        print(f"WARNING: VT entries not found for presets: {sorted(missing)}", file=sys.stderr)
        print("Has any of them been renamed in the HA UI?", file=sys.stderr)
    if motion_missing:
        print(f"WARNING: VT entries not found for motion: {sorted(motion_missing)}", file=sys.stderr)

    print(f"Patched presets on {len(matched)} VT entries: {sorted(matched)}")
    print(f"Patched motion on {len(motion_matched)} VT entries: {sorted(motion_matched)}")
    STORAGE_PATH.write_text(json.dumps(data, indent=2))
    print(f"Wrote {STORAGE_PATH}. Restart HA to pick up the new values.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
