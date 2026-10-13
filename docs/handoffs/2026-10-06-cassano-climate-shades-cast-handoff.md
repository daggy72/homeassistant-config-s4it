# Handoff — Cassano HA: shades, fancoils, Cast, Shellys on IoT, weekly updates (updated 2026-10-13)

Session "HA-CM1 10.1" (Claude). Clean stop: nothing running, nothing half-built. Last commit `ee58203` (local main; GitHub not synced, see below).
Earlier record: `docs/handoffs/2026-09-22-climate-watch-handoff.md`, Obsidian `dagmars-desk/dev-journal/sessions/2026-09-26-…-sun-shade-glare-fix.md` and `2026-10-06-…-cast-popups-triage.md`.

## Needs Dagmar

1. **Projects 2 wall display.** He installs it "soon, not today". Then: point the Projects 2 VT at the new display's temperature sensor (today it reads the Mensa display `sensor.shellywalldisplay_00a90b53f68a_temperature`). Put the new display on `ff4.iot` with a UniFi reservation.
2. **Optional, not asked yet:** should the weekly update also cover the 10 ESPHome fancoil boards' firmware and HACS (Versatile Thermostat)? Today it does only the HA and ESPHome containers.

## Done since 2026-10-06

- B1826 resolved: ea3fc4 outputs 1+3 `detached` / `on`.
- TV pop-ups: Dagmar turned off "Let others control your cast media". Works. Closed.
- All 14 Shellys moved to IoT VLAN 20 (plan http://10.0.10.110:8080/plan/cassano-shelly-iot-move, accepted). IPs = 10.0.20.<old last octet>, Mensa display 10.0.20.33. Facts/runbook/log/snapshots: `docs/investigations/2026-10-13-shelly-iot-move-*`, `docs/plans/2026-10-13-shelly-iot-move-*`. HA 14/14 loaded, 0 unavailable Shelly entities.
- Weekly container updates: `scripts/update_containers.py`, launchd `com.dagmar.cassano-ha-updates` (Sun 06:00), log `~/Library/Logs/cassano-ha-updates.log`. First run: HA 2026.9.3 → 2026.10.1, ESPHome 2026.9.0 → 2026.9.1.
- HA API token now at `~/.claude/credentials/ha-claude.json` (token "ClaudeCodeHA-CM1"; never print).

## Decisions

- Decision: sun shades close for glare on sunny workdays, closed position 30 = 70% down; cloud close/open 65/85 (commit `4412a65`).
- Decision: keep Cast discovery across networks (mDNS `all`); the announcement is switched off per TV.
- Decision: winter shade behaviour unchanged ("on winterdays we will see").
- Decision: all Shellys live on IoT VLAN 20 with UniFi reservations; wired dual-homed Shellys have Wi-Fi off.
- Decision: HA + ESPHome containers update weekly by themselves; HA x.y.0 skipped; automatic rollback on a failed check.
- Decision: leave the foreign uncommitted `CLAUDE.md` / `README.md` edits alone; sync only own commits.

## State

- Season `off`, chiller off. 8 ESPHome fancoil boards `unavailable` = unpowered on purpose (masters off).
- Git: local `main` ahead of `origin/main` (incl. `ee58203`), 1 behind. Not pushed. Foreign uncommitted edits still in the checkout.
- A subagent printed a UniFi switch auth key once in its own transcript (not in any file). Rotations belong to P1061; no new ticket.

## Suggested skills

- `pickup` (start here), `devportal-cli` (B/F/P refs), `superpowers:systematic-debugging` if a Shelly or update misbehaves, `session-end` at close.

Facts verified against: HA REST API with the new token (2026-10-13 12:56), Shelly RPC, UniFi Cassano API, `~/Library/Logs/cassano-ha-updates.log`.
