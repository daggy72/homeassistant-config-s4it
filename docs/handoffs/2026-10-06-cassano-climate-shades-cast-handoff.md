# Handoff — Cassano HA: shades, fancoil power-cut fix, Cast pop-ups (2026-10-06)

Session "HA-CM1 10.1" (Claude). Clean stop: nothing running, nothing half-built, nothing deployed since 2026-09-24.
Earlier record: `docs/handoffs/2026-09-22-climate-watch-handoff.md` and Obsidian
`dagmars-desk/dev-journal/sessions/2026-09-26-homeassistant-config-s4it-sun-shade-glare-fix.md`.

## Needs Dagmar

1. **TV "now playing" pop-ups on staff phones.** He wants casting kept for everyone, only the announcement gone.
   Asked him to open the Google Home app → each TV → Settings → turn **"Let others control your cast media"** OFF,
   starting with the Large Meeting Room Chromecast. **Unconfirmed** whether his own Samsung The Frame
   ("TV Dagmar", 10.0.20.134) shows that switch. Waiting on his answer. Network left unchanged on purpose.
2. **Fancoil power-cut fix (old DP-1826, now a Bug ref — resolve with `dp ticket DP1826`).** Waiting on his "go".
   Fix = two Shelly RPC calls, no code/deploy/restart (via `ssh nas-docker`):
   `curl -s "http://10.0.11.41/rpc/Switch.SetConfig?id=1&config={\"in_mode\":\"detached\",\"initial_state\":\"on\"}"` and the same for `id=3`.
   Verified 2026-09-26: ea3fc4 outputs 1 and 3 are `in_mode: follow` / `initial_state: match_input`; the already-fixed eaf568 is `detached` / `on`.
3. **Projects 2 sensor (old DP-1733).** Asked: is there a wall display in Projects 2? Config shows Climate Mensa
   AND Projects 2 VTs both read `sensor.shellywalldisplay_00a90b53f68a_temperature` (the Mensa display); only two
   wall-display temp sensors exist. Projects 2 is dormant, so harmless today. His answer decides: point P2 at its own
   sensor, or record the sharing as intended. Either way `~/.claude/shared-memory/projects2-unoccupied-tracks-mensa.md`
   claims the opposite and must be corrected.
4. **GitHub out of sync.** NAS is at `4412a65`; local `main` is 3 ahead / 1 behind `origin/main` (`e4f6ae4`).
   Uncommitted `CLAUDE.md` / `README.md` edits look like another session's work — left untouched. Needs to know whose.

## Decisions

- Decision: sun shades close for glare on sunny workdays (forecast gate removed, `clear_sky` trigger wired), closed position 30 = 70% down; cloud close/open 65/85 (commit `4412a65`, live).
- Decision: keep Cast discovery across networks (UniFi mDNS mode `all`); Dagmar wants everyone able to cast — fix the announcement per device, not the network.
- Decision: winter shade behaviour unchanged ("on winterdays we will see").
- Decision: Codex builds/reviews/investigates, Claude orchestrates (Dagmar broadcasts 2026-10-02/03; Sonnet may build again since 2026-10-05).

## State

- Season `off`, all VTs off, chiller off at last check. Tenda CS automation-driven again.
- Cast facts (UniFi Cassano, read-only API 2026-10-01): staff phones on `ff4.wifi` → Default (11 phones); TVs on `ff4.iot` → IoT VLAN 20; mDNS reflection mode `all`. Script: none kept (scratchpad).
- DevPortal board `homeassistant`: 3 open — the two bugs above + F139 PV pre-conditioning (blocked, no PV panels).

## Update 2026-10-12

- 2026-10-07 network reboot: HA up, both Shelly Pro 4PM online (uptime 13 days, so no power cut). All master outputs
  off with source `WS_in` (HA turned them off; season = off), so 8 ESPHome fancoil boards show `unavailable` — expected,
  they are unpowered. Entrance + Reception boards stay online (separate supply). Nothing to fix.
- Still no answers on the four "Needs Dagmar" items above. Nothing running, nothing deployed.

## Update 2026-10-13 (Dagmar answered)

- B1826 DONE: ea3fc4 outputs 1+3 now `detached` / `on`, verified, ticket resolved.
- TV pop-ups: Dagmar switched off "Let others control your cast media". Works. Closed.
- Projects 2: Dagmar will install a wall display soon (not today). Then point the P2 VT at its sensor and correct `projects2-unoccupied-tracks-mensa.md`.
- GitHub: leave the foreign CLAUDE.md/README.md edits; sync only own commits.

## Suggested skills

- `pickup` (start from this file), `devportal-cli` (new B/F/P refs), `superpowers:systematic-debugging` if a fix misbehaves, `session-end` at close.

Facts verified against: live Shelly RPC and HA `.storage` reads (2026-09-26), UniFi Cassano API (2026-10-01), HA MCP live context.
