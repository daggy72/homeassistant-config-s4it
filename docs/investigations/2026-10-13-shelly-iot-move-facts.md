# Shelly Default LAN to UniFi IoT move: facts (Cassano), 2026-10-13

Read-only investigation. Nothing was changed: only UniFi GETs, Shelly `GET /rpc/...` reads, HA `.storage` reads, and `curl`/`ping` from the HA container.

## 1. Inventory (14 HA Shelly entries = 14 physical devices, all Gen2, all fw 2.0.1 or 2.7.4, all DHCP)

No device has a static IP in firmware (`Eth.ipv4mode` / `Wifi.sta.ipv4mode` = `dhcp` everywhere). Only 3 devices have UniFi DHCP reservations, all on Default: `.41`, `.42`, `.51`. No auth on any device (`auth_en=false`).
Pro devices have two MACs: base MAC = Wi-Fi, base+3 = Ethernet. UniFi lists them as two clients.

| Device (HA title) | Model | MAC (base) | HA host | Actual link(s) now | Switch/port or SSID | Controls |
|---|---|---|---|---|---|---|
| Pro 4PM ea3fc4 | SPSW-104PE16EU | ECE334EA3FC4 | 10.0.11.41 (reserved) | Ethernet only, Default; Wi-Fi off | UDM Pro Max port 5 (100M, no PoE) | switch_3 "Fancoils Tania"; others unnamed (not mapped) |
| Pro 4PM eaf568 | SPSW-104PE16EU | ECE334EAF568 | 10.0.11.42 (reserved) | Ethernet only, Default; Wi-Fi off | USW 24 PoE (Rack Top) port 19, native Default, PoE off | CRITICAL: switch_2 = Chiller; also "Fancoils CS" master (SPOF per reference.md) |
| Pro 2PM Cover 34987a | SPSH-002PE16EU | 34987A47C9B0 | 10.0.11.51 (reserved) | Ethernet 10.0.11.51 (Default) AND Wi-Fi ff4.iot 10.0.20.59 (dual-homed) | Rack Top port 23, native Default; Wi-Fi AP P1-OFF U7 Pro | Tenda meeting, Tenda CS (shades); 1 local Schedule |
| Pro 4PM 963420 | SPSW-204PE16EU | 841FE8963420 | 10.0.11.83 | Ethernet 10.0.11.83 AND Wi-Fi ff4.iot 10.0.20.70 (dual-homed) | USW Enterprise 48 port 2; Wi-Fi AP U6 LR | fancoil master "OS & Meeting" (per reference.md; mapping uncertain) |
| Pro 4PM 971434 | SPSW-204PE16EU | 841FE8971434 | 10.0.11.220 | Ethernet 10.0.11.220 AND Wi-Fi ff4.iot 10.0.20.175 (dual-homed) | USW Enterprise 48 port 2; Wi-Fi AP U6 LR | not mapped (uncertain) |
| Pro 4PM e52f40 | SPSW-204PE16EU | ECE334E52F40 | 10.0.20.194 | Wi-Fi ff4.iot only (eth enabled, no link) | AP P1-OFF U7 Pro | not mapped |
| Pro 2PM Cover 2cbcbb | SPSH-002PE16EU | 2CBCBBB1FF9C | 10.0.11.77 | Ethernet only, Default; Wi-Fi off | USW Enterprise 48 port 2 | Tende Mensa shades |
| Pro 0-10V PM 8813bfd9525c | SPCC-001PE10EU | 8813BFD9525C | 10.0.11.62 | Ethernet only, Default | USW Ent 48 port 2 | stepless fancoils, Office Dagmar |
| Pro 0-10V PM 8813bfd95330 | SPCC-001PE10EU | 8813BFD95330 | 10.0.11.224 | Ethernet only, Default | USW Ent 48 port 2 | fancoils Projects 1 |
| Pro 0-10V PM 8813bfe0e42c | SPCC-001PE10EU | 8813BFE0E42C | 10.0.11.74 | Ethernet only, Default | USW Ent 48 port 2 | fancoils Projects 2 |
| Pro 0-10V PM 8813bfe0fc18 | SPCC-001PE10EU | 8813BFE0FC18 | 10.0.11.142 | Ethernet only, Default | USW Ent 48 port 2 | fancoils Mensa |
| Wall Display Mensa | SAWD-2A1XX10EU1 | 00A90B53F68A | 10.0.11.33 | Wi-Fi ff4.wifi (Default), AP U6 LR | n/a | Mensa temperature sensor for VT (feeds Mensa AND Projects 2 regulation) + a switch |
| Wall Display Projects1 | SAWD-0A1XX10EU1 | 000822D01C79 | 10.0.20.246 | Wi-Fi ff4.iot (IoT already) | AP U6 LR | Projects 1 temperature sensor; known to hang, power-cycle fix |
| Wall Display MT | SAWD-3A1XE10EU2 | 00A90B9D04EE | 10.0.20.9 | Wi-Fi ff4.iot (IoT already) | AP CC U6 Mesh | switch + sensor |

All are mains powered (none battery/sleeping: `sleep_period` = 0 in every entry). Totals: 5 Pro 4PM, 2 Pro 2PM Cover, 4 Pro 0-10V PM, 3 Wall Displays.

Link summary:
- Wired Ethernet on Default, primary: 10 devices (ea3fc4, eaf568, 34987a, 963420, 971434, 2cbcbb, 4x 0-10V).
- Of those, 3 are dual-homed (Wi-Fi ff4.iot already joined and active): 34987a, 963420, 971434. Their Wi-Fi leg is already on IoT.
- Wi-Fi only: 4 devices; 3 already on IoT (e52f40, Projects1, MT); 1 still on Default Wi-Fi (Mensa Wall Display).
- Real work to move to IoT: 10 wired devices + 1 Wi-Fi display.
- The 7 devices on USW Enterprise 48 port 2 are the only clients on that port (UniFi shows no other clients). The port is 100M, 0 W PoE, so a small downstream switch most likely sits behind it (inferred, not verified). One port VLAN change moves all 7 at once.
- Rack Top ports 19 and 23 and UDM port 5 each hold exactly one Shelly.
- HA host of the 3 dual-homed devices is the wired IP; HA entries for e52f40, Projects1, MT already use 10.0.20.x and HA is connected to them today (HA log 2026-10-13 11:50: `aioshelly.rpc_device.wsrpc Connected to 10.0.20.246`).

Per-device RPC results (read live from the Mac Mini on Default):
- `Ws.GetConfig`/`Shelly.GetConfig.ws`: outbound websocket `enable=false` on all 14.
- `mqtt.enable=false` on all.
- Cloud: `cloud.enable=true` and connected on all 14.
- `Script.List`: 0 scripts everywhere. `Webhook.List`: 0 everywhere. `Schedule.List`: 0 except 34987a (1 job, local).
- No Gen1 devices exist, so no CoIoT (UDP 5683) peers and no `/settings`.
- Firmware: Pro 2.0.1, Wall Display 2.7.4.

## 2. Network and firewall (UniFi Cassano, read-only GET)

| Network | VLAN | Subnet | DHCP range | Internet | Isolation | mDNS | Zone |
|---|---|---|---|---|---|---|---|
| Default | 1 | 10.0.10.0/23 | 10.0.11.11-.254 | yes | n/a | on | Internal |
| IoT | 20 | 10.0.20.0/24 | 10.0.20.6-.254 | yes | off | on | IoT |
| NoT | 30 | 10.0.30.0/24 | 10.0.30.6-.254 | yes flag on, blocked by custom rule | off | on | NoT |
| Unifi (mgmt) | 15 | 10.0.15.0/24 | .101-.254 | yes | off | on | Internal |
| Guest | 100 | 10.0.100.0/24 | | yes | off | off | Hotspot |

SSIDs: `ff4.wifi` to Default (2.4/5/6 GHz), `ff4.iot` to IoT (2.4 GHz only), `ff4.not` to NoT (2.4 GHz only), `ff4.guest`, `S4it.uid` (Default, EAP). So the IoT SSID already exists and 8 Shelly Wi-Fi links already use it.

Switch ports: the UniFi port profile list is empty (default only). No port is configured for IoT. Ports 19 and 23 on Rack Top are explicitly native Default; the rest use the default profile (native Default). A wired move means setting the native network to IoT (or a profile) on: UDM port 5, Rack Top 19 and 23, Enterprise 48 port 2.

Zone policies (custom plus predefined, all enabled):
- Internal to IoT: `Allow LAN > IoT` (custom, allow all, 1,814,899 hits). The predefined `Block All Traffic` Internal to IoT sits below it. Result: HA (Internal) can initiate to any IoT host on any port.
- IoT to Internal: predefined `Block All Traffic` BLOCK. Exceptions only: return traffic (RESPOND_ONLY) for LAN-initiated flows, `Allow Bonjour/mDNS IoT > LAN` (port 5353), AirPlay TCP/UDP groups. There is no allow for IoT to the NAS/HA (no 8123, no UDP 5683, no 80/443). So any IoT-initiated connection to HA is blocked.
- IoT to External: `Allow All Traffic` (default allow). Only `Block Invalid` and `Block Non-Permitted Networks Out ULTE` (LTE failover) are blocks. Shelly cloud and firmware updates therefore keep working (already proven: the 8 IoT Wi-Fi links report `cloud.connected=true`).
- IoT to Gateway: allow all plus mDNS (DHCP, DNS, NTP via the UDM work).
- IoT to NoT / NoT to IoT / IoT to IoT: block. VPN to IoT: allowed (3,097 hits). 
- Note: `Allow Bonjour/mDNS LAN > IoT` shows no hits and mDNS reflection is on for Default/IoT/NoT.

## 3. Live tests (read-only)

From inside `HA_homeassistant` (host networking) on the NAS:
- `curl http://10.0.20.194/rpc/Shelly.GetDeviceInfo` returns 200. `10.0.20.9` returns 200.
- `curl http://10.0.20.60:8008/setup/eureka_info` (Chromecast) returns 200.
- `curl http://10.0.20.134:8008/...` (TV) returned no response (000); that TV may not expose 8008 (uncertain, not a firewall finding since the Chromecast on the same VLAN answered).
- `ping 10.0.20.194`: 2/2, 0% loss, about 9 ms.
- From the Mac Mini on Default (10.0.10.110): Shelly RPC reached all 17 Shelly addresses on both subnets.

Conclusions:
- HA to IoT works today and is already in production use (3 HA entries, 10.0.20.194/.246/.9, run on IoT now).
- Nothing in the fleet depends on IoT-initiated traffic to HA: outbound WS off, MQTT off, no Gen1/CoIoT, no scripts/webhooks. Gen2 integration is HA opens the WebSocket to the device (`aioshelly wsrpc`), allowed by Internal to IoT.
- The remaining IoT-initiated path is cloud (external, allowed).

## 4. Other consumers

- Shelly Cloud: enabled and connected on all 14, so a cloud account/app controls them in parallel (who uses the app: unknown). Cloud keeps working from IoT.
- Device-local automation: 0 scripts, 0 webhooks; one local schedule on cover 34987a. Wall Display on-screen actions (they can call other Shellys or HA) are not exposed via RPC: UNVERIFIED, check on the displays' touch UI.
- HA-side consumers: climate stack (chiller `switch.shellypro4pm_ece334eaf568_switch_2`, fancoil masters, 0-10V `light.*` numbers, VT sensors from Wall Displays), shade covers, Grafana/InfluxDB (entity-based, host-agnostic).
- HA entries store the host: moving a wired device changes its IP. The Morazzone lesson says a plain reload keeps the old host; the reconfigure flow fixes it. Whether Shelly zeroconf auto-updates the host here is UNVERIFIED.

## 5. Risks and blockers found

1. Chiller + Fancoils CS master share one Shelly (eaf568, Rack Top port 19, reservation 10.0.11.42): a failed move stops cooling for two zones; respect the 10-minute chiller min-cycle.
2. DHCP reservations (.41, .42, .51) are on Default and do not carry over; new IoT reservations are needed if stable IPs matter.
3. A wired move needs a port native-VLAN change plus a link bounce (the port has no PoE, so a PoE cycle does not exist: unplug/replug or disable/enable the port). Port 2 on Enterprise 48 moves 7 devices at once; any non-Shelly device behind it would move too (UniFi shows none, but the downstream switch's other clients are not visible in this data).
4. Mensa Wall Display must be re-joined to `ff4.iot` on the device itself; the Mensa display also feeds Projects 2 regulation.
5. The 3 dual-homed Pros already carry an IoT IP over Wi-Fi: after a port move the device would have the same subnet on both interfaces (works but redundant). Wi-Fi 2.4 GHz only on `ff4.iot`; the Wi-Fi RSSI figures in UniFi (38 to 52 as reported by UniFi `rssi`, unit signal quality) look fine.
6. No firewall blocker was found. IoT to Internal being blocked affects nothing here.

Facts verified against: HA `.storage/core.config_entries` and `core.entity_registry` (read via nas-docker); UniFi Cassano local API GETs (clients, devices, networkconf, wlanconf, rest/user, zones, firewall-policies, firewallgroup) on 2026-10-13; live Shelly RPC reads from the Mac Mini (Shelly.GetDeviceInfo/GetConfig/GetStatus, Script/Webhook/Schedule.List); live curl/ping from the HA container; HA log grep; `homeassistant-config-s4it/docs/climate/reference.md`; `~/.claude/shared-memory/unifi-iot-not-zone-model-all-sites.md`; `vlan-shield.py`. Uncertain (not verified): downstream switch behind Enterprise 48 port 2, what the 4PM channels beyond those named control, Wall Display on-screen actions, HA zeroconf host auto-update, TV port 8008.

## Port sharing (added 2026-10-13, UniFi stat/sta + stat/device, read-only)

All currently connected clients (sw_mac + sw_port). Every one is a Shelly Ethernet interface, wired. No non-Shelly client is on these ports.

- UDM Pro Max port 5: shellypro4pm-ece334ea3fc4, EC:E3:34:EA:3F:C7, 10.0.11.41.
- Rack Top port 19: shellypro4pm-ece334eaf568, EC:E3:34:EA:F5:6B, 10.0.11.42 (chiller).
- Rack Top port 23: shellypro2cover-34987a47c9b0, 34:98:7A:47:C9:B3, 10.0.11.51.
- USW Enterprise 48 port 2 (7 clients): 8813bfd95330 88:13:BF:D9:53:33 .224; 8813bfd9525c 88:13:BF:D9:52:5F .62; 8813bfe0fc18 88:13:BF:E0:FC:1B .142; 8813bfe0e42c 88:13:BF:E0:E4:2F .74; shellypro2cover-2cbcbbb1ff9c 2C:BC:BB:B1:FF:9F .77; shellypro4pm-841fe8963420 84:1F:E8:96:34:23 .83; shellypro4pm-841fe8971434 84:1F:E8:97:14:37 .220.

Downstream of Ent48 port 2: no UniFi device has it as uplink, and the port has no LLDP and no mac_table in the API. So the 7 devices reach it either through an unmanaged switch or a hub (likely, since 7 devices share one 100 Mbps port, but not provable from UniFi) or via another path I cannot see. Historical (offline) clients: the user records carry no port number, so only currently connected clients are listed; no non-Shelly offline client was matched to Ent48 port 2.

Facts verified against: stat/sta, stat/device port_table and uplink fields, rest/user, 2026-10-13. Uncertain: the physical topology behind Ent48 port 2.
