#!/usr/bin/env python3
"""Read-only heat-up report: how fast each room warms after the season switched to winter.

Reads HA recorder history (no writes). Per VT room: temperature at the switch, now,
first rise of >= 0.3 C (= lag before the room reacts), warm-up rate, time to target.
Usage: heatup_report.py [ISO start, default = last change of input_select.climate_season]
"""
import json, sys, urllib.request, urllib.parse
from datetime import datetime, timezone

CRED = json.load(open("/Users/dagmar/.claude/credentials/ha-claude.json"))
RISE = 0.3  # C above the start temperature = "the room reacts"


def ha(path):
    req = urllib.request.Request(CRED["base_url"] + path, headers={"Authorization": "Bearer " + CRED["token"]})
    return json.load(urllib.request.urlopen(req, timeout=60))


def ts(s):
    return datetime.fromisoformat(s)


def hm(minutes):
    return "-" if minutes is None else f"{int(minutes // 60)}h{int(minutes % 60):02d}"


start = sys.argv[1] if len(sys.argv) > 1 else ha("/api/states/input_select.climate_season")["last_changed"]
t0 = ts(start)
now = datetime.now(timezone.utc)
rooms = sorted(e["entity_id"] for e in ha("/api/states")
               if e["entity_id"].startswith("climate.") and e["state"] == "heat")
ids = ",".join(rooms + ["sensor.outdoor_temperature", "switch.shellypro4pm_ece334eaf568_switch_2"])
hist = ha(f"/api/history/period/{urllib.parse.quote(start)}?filter_entity_id={ids}")
by_id = {h[0]["entity_id"]: h for h in hist if h}

print(f"Season switch: {t0.astimezone():%Y-%m-%d %H:%M}  now: {now.astimezone():%H:%M}  "
      f"elapsed {hm((now - t0).total_seconds() / 60)}")
out = [float(s["state"]) for s in by_id.get("sensor.outdoor_temperature", []) if s["state"] not in ("unknown", "unavailable")]
if out:
    print(f"Outdoor: {out[0]:.1f} -> {out[-1]:.1f} C (min {min(out):.1f}, max {max(out):.1f})")
chiller = [(ts(s["last_changed"]).astimezone().strftime("%H:%M"), s["state"]) for s in by_id.get("switch.shellypro4pm_ece334eaf568_switch_2", [])]
print("Chiller (not used for heating):", ", ".join(f"{t} {st}" for t, st in chiller) or "no data")
print()
print(f"{'room':26} {'preset':8} {'target':>6} {'start':>6} {'now':>6} {'+C':>5} {'reacts':>7} {'C/h':>5} {'at target':>9}")
for r in rooms:
    pts = [(ts(s.get("last_updated") or s["last_changed"]), s["attributes"].get("current_temperature"), s["attributes"].get("temperature"),
            s["attributes"].get("preset_mode")) for s in by_id.get(r, [])]
    pts = [p for p in pts if p[1] is not None]
    if not pts:
        print(f"{r:26} no history"); continue
    t_start, temp0 = pts[0][0], pts[0][1]
    _, temp_now, target, preset = pts[-1]
    react = next((p[0] for p in pts if p[1] >= temp0 + RISE), None)
    reached = next((p[0] for p in pts if target and p[1] >= target), None)
    mins = lambda t: None if t is None else (t - t0).total_seconds() / 60
    # rate after the room reacts, so the dead time does not dilute it
    rate = None
    if react and (now - react).total_seconds() > 1800:
        rate = (temp_now - temp0 - RISE) / ((now - react).total_seconds() / 3600)
    print(f"{r.removeprefix('climate.'):26} {str(preset):8} {target:>6} {temp0:>6} {temp_now:>6} "
          f"{temp_now - temp0:>+5.1f} {hm(mins(react)):>7} {'-' if rate is None else f'{rate:.2f}':>5} {hm(mins(reached)):>9}")
