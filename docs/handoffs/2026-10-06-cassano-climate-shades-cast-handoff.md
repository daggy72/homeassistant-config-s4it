# Handoff — Cassano HA: shades, fancoils, Cast, Shellys on IoT, weekly updates (updated 2026-10-26)

Session "HA-CM1 10.1" (Claude). Clean stop: nothing running, nothing half-built. Last commit `ee58203` (local main; GitHub not synced, see below).
Earlier record: `docs/handoffs/2026-09-22-climate-watch-handoff.md`, Obsidian `dagmars-desk/dev-journal/sessions/2026-09-26-…-sun-shade-glare-fix.md` and `2026-10-06-…-cast-popups-triage.md`.

## Needs Dagmar

1. **B2820 HA backup to NAS (it-helpdesk).** Since ~2026-10-23 the backup agent `synology_dsm.2050SBR8V3TQ4` is unavailable (reload did not help). Dagmar must change DSM (Claude may not; browser to DSM is blocked and user-rights changes are off limits): Control Panel > User & Group > `homeassistant` > Applications: File Station = Allow; Permissions: `backup` = Read/Write. After his "done": reload synology_dsm entry `01JT86K7NCDD5Z72HWV8HFMX53`, check `backup/agents/info` lists the agent, check repairs clear, resolve B2820. Local + cloud backups still OK daily.
2. **Meeting room target 24 °C (manual, 2026-10-26 13:50)** because Dagmar works there while builders are in his office; the sensor reads higher than it feels. Evening schedule resets it. Fancoil Dagmar is OFF today; Morning VT Alignment turns it back on Tue 07:00 unless he says the works continue.
3. **Projects 2 wall display.** Not installed yet. Then: point the Projects 2 VT at the new display's sensor (today the Mensa display), put it on `ff4.iot` with a UniFi reservation.
4. **Optional, not asked yet:** weekly update also for ESPHome fancoil firmware and HACS (VT)?
5. **it-cx smart plugs brief** (`/Users/dagmar/DEV-SHARED/docs/handoffs/2026-10-19-it-cx-cassano-smartplugs.md`): relay not confirmed.

## Open bugs

- **B2810** Meeting fancoil_05 stayed at 33 % while VT asked 0 % (room 26.7 vs 18). Manual `number.fancoil_meeting` = 0 fixed it. Suspect: template state (avg of two fans) never matches what VT wrote. Check other dual-fan zones.
- **B2770** silent update rollback: fix committed by another session (871b69c); see `docs/handoffs/2026-10-26-b2770-update-notify-handoff.md`. 2026-10-25 run rolled back 2026.10.4 again (loaded 83→82).

## Winter heat-up (2026-10-26)

Season set to winter 07:59. Result in `docs/investigations/2026-10-26-winter-heatup-log.md` (e7b4c4f): rooms react in 6–19 min, warm 1–2 °C/h, reach target in 14 min – 2 h 11 (sunny morning, outdoor 7.6→13.5, best case). Re-run anytime: `python3 scripts/heatup_report.py [ISO start]`. Entrance heat presets were 30/30/30 at runtime, set to 19/20/22 (Dagmar OK). Mensa display reports only on change, so VT Mensa / Projects 2 drop into `safety` after 60 min without change.

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
- Decision: Entrance heat presets follow OpenSpace (19/20/22), not 30 (Dagmar 2026-10-26).
- Decision: HA + ESPHome containers update weekly by themselves; HA x.y.0 skipped; automatic rollback on a failed check.
- Decision: leave the foreign uncommitted `CLAUDE.md` / `README.md` edits alone; sync only own commits.

## State

- Season `off`, chiller off. 8 ESPHome fancoil boards `unavailable` = unpowered on purpose (masters off).
- Git: local `main` ahead of `origin/main` (incl. `ee58203`), 1 behind. Not pushed. Foreign uncommitted edits still in the checkout.
- A subagent printed a UniFi switch auth key once in its own transcript (not in any file). Rotations belong to P1061; no new ticket.

## Suggested skills

- `pickup` (start here), `devportal-cli` (B/F/P refs), `superpowers:systematic-debugging` if a Shelly or update misbehaves, `session-end` at close.

Facts verified against: HA REST API with the new token (2026-10-13 12:56), Shelly RPC, UniFi Cassano API, `~/Library/Logs/cassano-ha-updates.log`.
