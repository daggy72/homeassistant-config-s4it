# Runbook — move Cassano Shellys to IoT (APPROVED by Dagmar in Review Hub 2026-10-13, plan cassano-shelly-iot-move, final)

Facts: docs/investigations/2026-10-13-shelly-iot-move-facts.md (read it first).

## Rules
- Never touch herdr workspace `wS` / any NAS SSH pane. Use only `ssh nas-docker` (passwordless only `sudo /usr/local/bin/docker`, HA container `HA_homeassistant`).
- Never print credentials. UniFi site creds: ~/.claude/credentials/unifi.json `sites.cassano`; reuse the login/session code pattern of ~/DEV-SHARED/IT/scripts/vlan-shield.py. HA token: find one under ~/.claude/credentials/ (load without printing); if none, report and stop at HA steps.
- Snapshot before every UniFi write: save the GET body of each object you change to docs/investigations/unifi-snapshots/2026-10-13-<object>.json (no secrets in these objects; if one has a secret field, drop it).
- Read-modify-write: change ONLY the named fields (port_overrides entry for the one port; client fixed-IP fields).
- Chiller min-cycle 10 min. Season must be `off` and switch eaf568 switch_2 (chiller) off >= 10 min before wave 4. Check `input_select.climate_season` first; if not `off`, STOP.
- STOP and report on any failed verify after one rollback. Never continue to the next wave after a failure.
- Keep tool output short. Log every action with time to docs/investigations/2026-10-13-shelly-iot-move-log.md.

## IP plan (IoT 10.0.20.0/24, DHCP range .6-.254)
Mirror the old last octet where free: 34987a .51, ea3fc4 .41, eaf568 .42, 963420 .83, 971434 .220, 2cbcbb .77, 0-10V: d9525c .62, d95330 .224, e0e42c .74, e0fc18 .142. First check none is in use on IoT (UniFi clients + fixed IPs); on conflict pick a free one in .40-.58 and log it.
Reservation = the existing UniFi client object for the device's ETHERNET MAC: use_fixedip true, network_id = IoT networkconf id, fixed_ip = new IP. (Old Default reservation goes away by that.)

## Per wired wave
1. Reservation(s) as above.
2. `Shelly.Reboot?delay_ms=90000` to every Shelly on that port (via current IP from nas-docker).
3. Immediately set the switch port's native network to IoT (port_overrides native_networkconf_id; keep other fields). Confirm the device provisioned (state back to connected) within the window.
4. Wait ~3 min. Verify: device answers on its new IoT IP (`curl Shelly.GetDeviceInfo` from nas-docker), UniFi shows it on IoT with the reserved IP.
5. HA: check the config entry host. Shelly zeroconf may update it by itself; wait up to 10 min. If still old: reconfigure flow (`POST /api/config/config_entries/flow` {handler: shelly, entry_id...} or the entry's reconfigure step, submit new host). A plain reload does NOT help. Verify all entities of that device are not `unavailable`.
6. If a device kept its old lease (answers nowhere): set the port back to Default, wait until reachable at old IP, retry once with delay_ms 120000. Second failure: roll back (port Default, reservation back to Default old IP, reboot) and STOP.

## Waves
- Wave 2: Cover 34987a — Rack Top USW 24 PoE port 23. After eth verified on IoT, disable its Wi-Fi: `Wifi.SetConfig` sta.enable false (and sta1 if set); check HA host is the eth IP.
- Wave 3: USW Enterprise 48 port 2 (unmanaged switch behind it, 7 Shellys: 4x 0-10V, Cover 2cbcbb, 4PM 963420, 4PM 971434). Reboot all 7 with delay, then the port. 963420/971434: disable Wi-Fi only after eth verified on IoT.
- Wave 4a: Pro 4PM ea3fc4 — UDM Pro Max port 5. Note: its outputs 1 and 3 boot ON (initial_state on); afterwards make sure they are off again (season off) — HA should do it; if not within 2 min, turn them off via HA.
- Wave 4b: Pro 4PM eaf568 — Rack Top port 19. Precondition chiller off >= 10 min. switch_2 boots match_input (stays off). Output 1 boots ON; same check as 4a.
- Wave 1 (Mensa wall display, Wi-Fi) is NOT yours: a person picks ff4.iot on the screen. Prepare only: report its Wi-Fi MAC; the orchestrator handles it.

## Final verify
All 13 wired/IoT Shellys: on IoT with reserved IP, HA entries on new host, zero `unavailable` Shelly entities. No toggle tests (unnamed outputs may drive unknown loads). Report table: device | old IP | new IP | HA ok.
