# ESPHome Fancoil Project — Knowledge Base & Status

**Last updated:** March 2026
**Project:** Replace legacy mechanical slider controls on 10 office fancoil units with a smart,
connected system integrated into Home Assistant, controlled by Versatile Thermostat with Auto-TPI.

---

## 1. Architecture Overview

```
Versatile Thermostat (HA)
  └─ on_percent (0–100%)
       └─ Automation: fancoil_speed_control
            ├─ Dual rooms  → 6-step symmetric cascade (window fan first)
            └─ Single rooms → 3-step proportional control
                  └─ ESPHome fan entity (speed_count: 3)
                        └─ Relay 1/2/3 → Fan motor speeds
                        └─ Relay 4     → Valve (open/close)
```

The VT's `on_percent` attribute is passed directly to ESPHome fan entities via a HA automation.
No intermediate switch or valve entity is needed — the automation is the only bridge.

---

## 2. Hardware

**Device:** Athom 4CH ESP32 Relay Board
- ESP32, 4 × 10A relays, AC 90–250V
- Pre-flashed with ESPHome
- Purchased ×10 units

**GPIO mapping (per device):**

| Pin | Function |
|-----|---------|
| GPIO27 | Relay 1 — Fan Speed 1 (Low) |
| GPIO14 | Relay 2 — Fan Speed 2 (Medium) |
| GPIO12 | Relay 3 — Fan Speed 3 (High) |
| GPIO13 | Relay 4 — Valve (on/off) |
| GPIO36 | Button 1 — Speed 1 (hold 4s = factory reset) |
| GPIO39 | Button 2 — Speed 2 |
| GPIO34 | Button 3 — Speed 3 |
| GPIO35 | Button 4 — Toggle on/off |
| GPIO15 | Status LED |

> GPIO12 and GPIO15 are ESP32 strapping pins — warnings are cosmetic, safe to ignore on this board.

---

## 3. Network

| VLAN | SSID | Subnet | Purpose |
|------|------|--------|---------|
| Default | — | 10.0.10.0/23 | Management |
| IoT | ff4.iot | 10.0.20.0/24 | IoT devices (internet allowed) |
| **NoT** | **ff4.not** | **10.0.30.0/24** | **Fancoils live here (no internet)** |

All 10 fancoil devices are on the **NoT VLAN** with **fixed IPs 10.0.30.41–10.0.30.50**.

> Because the NoT VLAN has no internet, ESPHome uses `platform: homeassistant` for time sync
> instead of SNTP. The devices get time from HA over the local network.

**Cross-VLAN note:** mDNS does not cross VLANs. OTA updates are done via the ESPHome dashboard
using the fixed IP directly (no mDNS discovery needed).

---

## 4. Device Inventory

| Device | IP | Room | Window fan? | Interior fan? |
|--------|-----|------|------------|---------------|
| fancoil-01 | 10.0.30.41 | OpenSpace | ✓ (Fan A) | |
| fancoil-02 | 10.0.30.42 | OpenSpace | | ✓ (Fan B) |
| fancoil-03 | 10.0.30.43 | Entrance | single | |
| fancoil-04 | 10.0.30.44 | Reception | single | |
| fancoil-05 | 10.0.30.45 | Meeting | | ✓ (Fan B) |
| fancoil-06 | 10.0.30.46 | Meeting | ✓ (Fan A) | |
| fancoil-07 | 10.0.30.47 | CS | | ✓ (Fan B) |
| fancoil-08 | 10.0.30.48 | CS | ✓ (Fan A) | |
| fancoil-09 | 10.0.30.49 | Tania | | ✓ (Fan B) |
| fancoil-10 | 10.0.30.50 | Tania | ✓ (Fan A) | |

---

## 5. ESPHome Configuration

### GitHub Repository
**URL:** https://github.com/daggy72/esphome-fancoil
**Branch:** main
**File:** `fancoil-base.yaml`
**Local copy (iCloud):** `~/Library/Mobile Documents/com~apple~CloudDocs/DevProjects/ESPHome-Fancoil/`

### Base Config (`fancoil-base.yaml`)
- Shared template for all 10 devices — **never flash this file directly**
- Current version: **1.1.0** (exposed as `sensor.fancoilXX_config_version` in HA)
- Contains: relays, fan component (speed_count: 3), buttons, break-before-make interlocking,
  diagnostics, time sync from HA

### Device YAMLs (`fancoil-01.yaml` … `fancoil-10.yaml`)
- Stored on NAS: `/volume1/docker/homeassistant/esphome/config/`
- Each file is ~10 lines: sets `name`, `friendly_name`, `room` and pulls base from GitHub

```yaml
substitutions:
  name: "fancoil-01"
  friendly_name: "Fancoil 01"
  room: "OpenSpace"

packages:
  base:
    url: https://github.com/daggy72/esphome-fancoil
    ref: main
    file: fancoil-base.yaml
    refresh: 1d
```

### Secrets (`secrets.yaml` on NAS)
```yaml
wifi_ssid: "ff4.not"          # NoT VLAN — intentional, NOT a typo
wifi_password: "N0Int3rn3t.Sales4.it"
fallback_password: "2WS_RRKfLXJrcTPb"
api_encryption_key: "9NEbuEc3+P4UBCPHEi07qs5+qwWM8gQh8SSV99FD5p4="
ota_password: "c9d0Oe4w7T4XEPx8QvMwUw"
```

### Flashing Workflow
1. Edit `fancoil-base.yaml` locally → push to GitHub
2. In ESPHome dashboard (`esphome.sales4.it`):
   - **"Clean Build Files"** (not "Clean All Files") on the device → clears cached binary
   - **Install → Wirelessly** → ESPHome fetches fresh from GitHub, compiles, OTA uploads
3. For new/offline devices: use device web interface at `http://10.0.30.4X` to upload `.bin` manually

> **"Clean All Files"** wipes the entire toolchain cache → first build takes 5–10 min.
> **"Clean Build Files"** only clears the device's binary → rebuild takes ~30 seconds.

---

## 6. Home Assistant Setup

**HA URL:** https://hacm1.sales4.it
**HA config dir (NAS):** `/volume1/docker/homeassistant/homeassistant/config/`
**Docker compose:** `/volume1/docker/homeassistant/docker-compose.yaml`

All services use `network_mode: host` — required for mDNS to work correctly.

### Versatile Thermostat Instances

| VT Entity | Room | Temperature Sensor | Fancoils |
|-----------|------|-------------------|---------|
| `climate.fancoil_tania` | Tania | `sensor.up_sense_temperature` | 09 (B), 10 (A) |
| `climate.fancoil_cs` | CS | `sensor.cc_up_sense_temperature` | 07 (B), 08 (A) |
| `climate.fancoil_meeting` | Meeting | `sensor.mt_meeting_room_up_sense_temperature` | 05 (B), 06 (A) |
| `climate.fancoil_openspace` | OpenSpace | `sensor.up_sense_temperature_3` | 01 (A), 02 (B) |
| `climate.fancoil_reception` | Reception | `sensor.reception_temperature` | 04 |
| `climate.fancoil_entrance` | Entrance | `sensor.up_sense_temperature_3` ⚠️ shared | 03 |

**Outdoor sensor (all rooms):** `sensor.outdoor_temperature`
**TPI settings (all fancoil VTs):** `coef_int = 0.3`, `coef_ext = 0.01`, Auto-TPI disabled
**Central config:** NOT used for TPI — each fancoil VT has its own TPI settings

> ⚠️ Entrance is temporarily using the OpenSpace sensor. Install a dedicated sensor and update
> the VT configuration for `climate.fancoil_entrance` when ready.

### TPI Demand Reference

| Indoor deficit | on_percent | Fan behaviour (dual room) |
|----------------|-----------|--------------------------|
| 0.5°C | 15% | Window fan, speed 1 |
| 1.0°C | 30% | Both fans, speed 1 |
| 2.0°C | 60% | Both fans, speed 2 |
| 2.7°C | 81% | A=speed 3, B=speed 2 |
| 3.3°C+ | 100% | Both fans, speed 3 |

### Dummy Switches (for VT `over_switch` mode)
Added to `configuration.yaml` under `input_boolean`:
```
input_boolean.fancoil_tania
input_boolean.fancoil_cs
input_boolean.fancoil_meeting
input_boolean.fancoil_openspace
input_boolean.fancoil_reception
input_boolean.fancoil_entrance
```
These are placeholders only — VT needs a heater entity but the automation does the actual fan control.

### Automation (`automations.yaml`)
File: `fancoil_speed_control.yaml` (paste contents into `automations.yaml`)

**Logic:**
- Triggers on `on_percent` change of any of the 6 VT climate entities
- Dual rooms (4 rooms): 6-step symmetric cascade — window fan (A) leads, interior fan (B) follows
- Single rooms (2 rooms): 3-step proportional control

**Speed lookup tables:**
```
Fan A: [0, 33, 33, 67, 67, 100, 100]   ← window fan
Fan B: [0,  0, 33, 33, 67,  67, 100]   ← interior fan
       step: 0   1   2   3   4    5   6
```
Percentages 33/67/100 map cleanly to ESPHome speed_count:3 buckets (Spd1/Spd2/Spd3).

### Demand Sensors (`templates.yaml`)
Template sensors exposing `on_percent` as proper HA sensor entities:
```
sensor.fancoil_demand_tania
sensor.fancoil_demand_cs
sensor.fancoil_demand_meeting
sensor.fancoil_demand_openspace
sensor.fancoil_demand_reception
sensor.fancoil_demand_entrance
```
Unit: `%` | Icon: `mdi:fan` | Use these in gauge cards on the climate dashboard.

### ESPHome in HA Sidebar
Already configured in `configuration.yaml`:
```yaml
panel_iframe:
  esphome:
    title: "ESPHome"
    url: "https://esphome.sales4.it"
    icon: mdi:chip
    require_admin: true
```

---

## 7. Infrastructure

**Synology NAS:** cassano-dc1 (10.0.10.10)
**Reverse proxy:** Synology DSM → Application Portal
- `esphome.sales4.it` → port 6052 — **requires WebSocket header `Upgrade` (not `Update`)**
- `hacm1.sales4.it` → Home Assistant port 8123

**Docker services** (all `network_mode: host`):
- Home Assistant
- ESPHome
- Matter Server

---

## 8. Current Status (March 2026)

### ESPHome Firmware
| Device | Status | Firmware |
|--------|--------|---------|
| fancoil-01 | ⚠️ OFFLINE | Unknown — not yet installed/powered |
| fancoil-02 | ⚠️ OFFLINE | Unknown — not yet installed/powered |
| fancoil-03 | ✅ Online | Needs reflash with v1.1.0 |
| fancoil-04 | ✅ Online | Needs reflash with v1.1.0 |
| fancoil-05 | ⚠️ OFFLINE | Unknown — not yet installed/powered |
| fancoil-06 | ⚠️ OFFLINE | Unknown — not yet installed/powered |
| fancoil-07 | ✅ Online | Needs reflash with v1.1.0 |
| fancoil-08 | ✅ Online | Needs reflash with v1.1.0 |
| fancoil-09 | ✅ Online | ✅ v1.1.0 flashed |
| fancoil-10 | ✅ Online | ✅ v1.1.0 flashed |

### Home Assistant
- ✅ 6 VT instances created and active
- ✅ TPI coefficients set (coef_int=0.3, independent from central config)
- ✅ Automation `fancoil_speed_control` deployed
- ✅ Demand sensors in `templates.yaml`
- ✅ ESPHome sidebar link configured

---

## 9. Pending Tasks

- [ ] Flash fancoil-03, 04, 07, 08 with firmware v1.1.0 (Clean Build Files → Install Wirelessly)
- [ ] Physically install and power fancoil-01, 02, 05, 06 — then flash with v1.1.0
- [ ] Install dedicated temperature sensor for Entrance room and update `climate.fancoil_entrance`
- [ ] Set target temperatures for each VT room thermostat (currently defaulted to 15°C)
- [ ] Add demand gauge cards to the climate dashboard (`climate.yaml`)
- [ ] Push latest `fancoil-base.yaml` (v1.1.0) to GitHub if not yet done
- [ ] Remove `climate.cs_climate` (old CS thermostat) once `climate.fancoil_cs` is confirmed working
- [ ] Confirm OpenSpace window/interior fan assignment (fancoil-01=window assumed)
- [ ] Monitor TPI behaviour over first few days — adjust `coef_int` if too aggressive or too slow

---

## 10. Key File Locations

| File | Location |
|------|---------|
| `fancoil-base.yaml` | GitHub: github.com/daggy72/esphome-fancoil |
| `fancoil-base.yaml` (local) | iCloud: `~/Library/Mobile Documents/com~apple~CloudDocs/DevProjects/ESPHome-Fancoil/` |
| `fancoil_speed_control.yaml` | iCloud: same folder — paste into HA `automations.yaml` |
| `fancoil-01.yaml` … `fancoil-10.yaml` | NAS: `/volume1/docker/homeassistant/esphome/config/` |
| `configuration.yaml` | NAS: `/volume1/docker/homeassistant/homeassistant/config/` |
| `automations.yaml` | NAS: `/volume1/docker/homeassistant/homeassistant/config/` |
| `templates.yaml` | NAS: `/volume1/docker/homeassistant/homeassistant/config/` |
| `docker-compose.yaml` | NAS: `/volume1/docker/homeassistant/` |

---

## 11. Useful Links

- ESPHome dashboard: https://esphome.sales4.it
- Home Assistant: https://hacm1.sales4.it
- GitHub repo: https://github.com/daggy72/esphome-fancoil
- Athom board product page: https://www.athom.tech/blank-1/esphome-4ch-relay
- Versatile Thermostat docs: https://github.com/jmcollin78/versatile_thermostat
- ESPHome fan component: https://esphome.io/components/fan/template.html
