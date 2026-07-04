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

Target preset values (2026-06-20 redesign). "frost" = BOIL/overheat protection
in cool mode (VT cools the room down to this target if exceeded):

    OFFICE (Dagmar, Tania, CS, Meeting, Projects 1, Projects 2, Reception, Mensa):
        comfort_ac_temp = 25.0
        eco_ac_temp     = 27.0
        boost_ac_temp   = 24.0
        frost_ac_temp   = 30.0   (boil)

    COMMON (OpenSpace, Entrance):
        comfort_ac_temp = 27.0
        eco_ac_temp     = 29.0
        boost_ac_temp   = 25.0
        frost_ac_temp   = 31.0   (boil)

NOTE (2026-06-25): the EFFECTIVE live presets are VT's runtime number entities
(number.<zone>_preset_*_ac_temp), adjusted via the device UI — NOT this config
entry `data`. This script only rewrites the stale `data` baseline (applied on a
fresh entry setup/reset). For live tuning, set the number entities / VT UI.

Motion override DISABLED 2026-06-20 (use_motion_feature=False on Meeting/CS/
Reception) — superseded by the deterministic schedule + manual-override model.

The Summer Dynamic Temperature Adjustment automation is disabled separately
in automations.yaml so these fixed values stick.
"""
from __future__ import annotations

import datetime
import json
import shutil
import sys
from pathlib import Path

STORAGE_PATH = Path("homeassistant/config/.storage/core.config_entries")

# Map climate VT title (as it appears in the config_entry title field) to the
# target preset values. The titles below match what Versatile Thermostat sets
# at config-flow time; if the user has renamed any in HA UI, the lookup will
# miss and the script prints a warning.
# 2026-06-20 preset scheme (Dagmar's full redesign). "frost" preset is reused
# in cool mode as BOIL / overheat protection — VT actively cools a room down to
# this target if it exceeds it (offices 30, common 31).
#   OFFICE group: comfort 25, eco 27, boost 24, boil(frost) 30
#   COMMON group: comfort 27, eco 29, boost 25, boil(frost) 31
# use_presets_central_config=False on every zone so each VT uses ITS OWN
# per-group preset values below — not the single shared "Central configuration"
# (which can only hold one set, and was overriding OpenSpace/Entrance to
# comfort 26 / eco 28 / boost 23 / frost 30 — the "eco OpenSpace = 26" bug).
OFFICE = dict(comfort_ac_temp=25.0, eco_ac_temp=27.0, boost_ac_temp=24.0,
              frost_ac_temp=30.0, use_presets_central_config=False)
COMMON = dict(comfort_ac_temp=27.0, eco_ac_temp=29.0, boost_ac_temp=25.0,
              frost_ac_temp=31.0, use_presets_central_config=False)

ZONE_PRESETS = {
    "Fancoil Dagmar": OFFICE,
    "Fancoil Tania": OFFICE,
    "Projects 1": OFFICE,
    "Fancoil Reception": OFFICE,
    "Fancoil CS": OFFICE,
    "Fancoil Meeting": OFFICE,
    # Projects 2 now in the OFFICE group (eco-default like CS/Meeting). It was
    # previously COMMON while treated as unoccupied; re-staffed under the 2026-06-20
    # scheme. Its VT may still need a one-time Options-flow reconfigure to un-wedge.
    "Projects 2": OFFICE,
    # Mensa folded into OFFICE group (comfort 25 / eco 27 / boost 24); lunch boost
    # 12:00-14:00 uses the boost preset (= 24).
    "Climate Mensa": OFFICE,
    "Fancoil OpenSpace": COMMON,
    "Fancoil Entrance": COMMON,
}

# Motion-override DISABLED 2026-06-20. The deterministic schedule + manual
# override model (CS holds all day, Meeting 1h revert, Reception comfort-default)
# supersedes motion-based auto-switching, which would otherwise fight it (e.g.
# drop comfort-default Reception to eco when empty, or undo CS's all-day hold).
MOTION_OVERRIDE = {
    "Fancoil Meeting": {"use_motion_feature": False},
    "Fancoil CS": {"use_motion_feature": False},
    "Fancoil Reception": {"use_motion_feature": False},
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
