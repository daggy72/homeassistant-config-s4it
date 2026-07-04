# Adaptive / learning software thermostats for Home Assistant — research & recommendation

> **Date:** 2026-06-25 · **Author:** Claude Code (research session) · **Status:** research deliverable, no config changed.
> **Scope:** Replace or properly re-tune Versatile Thermostat (VT) for the Cassano office fancoils.
> **Method:** `deep-research` workflow (fan-out web search → fetch → 3-vote adversarial verification → synthesis), grounded in our actual `templates.yaml` / session note. **Full run: 23 sources, 108 claims extracted, 21 confirmed / 4 refuted.** A first (rate-limited) pass hallucinated VT valve-clamp params; the full re-run **refuted** them — corrections folded in below.

---

## ✅ APPLIED 2026-06-25 (Track 1, analog rooms)

Done via the HA UI (VT options-flow, as admin; zero downtime) — VT config lives in `.storage/core.config_entries`, **not** in this repo, so there's no YAML diff. Verified in storage.

**Change:** on the 4 analog 0-10V rooms, set a **per-zone TPI override** (`use_tpi_central_config: false`) and lowered **`tpi_coef_int` 0.6 → 0.3** (`tpi_coef_ext` left 0.01):

| Room | use_tpi_central_config | tpi_coef_int |
|---|---|---|
| Fancoil Dagmar | false | **0.3** |
| Projects 1 | false | **0.3** |
| Projects 2 | false | **0.3** |
| Climate Mensa | false | **0.3** |
| 6× three-speed rooms (CS, Meeting, OpenSpace, Entrance, Reception, Tania) | true | inherits 0.6 (untouched) |
| Central configuration | — | 0.6 (unchanged) |

Post-change all 4 analog climate entities were healthy (not wedged) and already modulating mid-values (e.g. Dagmar `power_percent` 23, P1 65) rather than slamming 0/100.

**Kept:** the external 15-70% `set_value` clamp in `templates.yaml` — VT has **no native maintain-floor** (the v10 "TPI parameters" step has no floor field; only `tpi_threshold_low/high` deadband, both 0). Do not remove the clamp.

**To revert a room:** VT → device → gear → *TPI parameters* → re-check "Use central TPI configuration" → Submit → All done (or set `tpi_coef_int` back to 0.6).

**Watch (next days, cool mode):** does 0.3 hold a smooth mid value without sagging off setpoint? If it now under-shoots (too little gain), nudge toward 0.4; if still bouncing, go 0.2. Note VT v10.0.2 also exposes an **"Enable Auto TPI Learning"** toggle (manual sessions, read docs) — a possible future step, left off for now.

---

## TL;DR — recommendation

**Stay on VT and re-tune it. The bang-bang is a TUNING problem, not a tool limit — but keep your external maintain-floor clamp, because VT has no native floor setting.**

Three concrete fixes, cheapest first:

1. **Lower `coef_int`** (TPI internal gain) from its default **`0.6`** toward **~0.3** on the fast 0-10V rooms. This is *the* lever: VT computes `on_percent = coef_int·(target−current) + coef_ext·(target−outdoor)` clamped 0–1, and `0.6` is aggressive for a room that warms 0.5 °C in 5 min → it drives `on_percent` to the 0/1 rails. Lower gain = smoother mid values. (`coef_ext` default `0.01`.)
2. **Enable `auto_regulation`** (start **Medium**, escalate to **Expert** with reduced `kp` if it still saturates). You're almost certainly on plain TPI today. ⚠ Expert is a **single global block** shared by all Expert VTherms and needs a full restart/integration reload.
3. **Keep the external 15-70% clamp.** VT has **no native maintain-floor parameter** (the earlier "minimum_opening_degrees" idea was hallucinated and is refuted). Your template `set_value` clamp stays — or tune gain so `on_percent` rarely drops below the floor.

**Fallback (only if VT keeps wedging on restart or still can't hold a mid value):** offload the four 0-10V loops to **ESPHome `pid` climate** at the edge — continuous float output (via a DAC like GP8403/DFR0971 or PWM-to-0-10V), built-in Ziegler-Nichols relay autotune, and the loop **survives HA restarts**. Keep the six Athom 3-speed units + chiller in VT/HA.

**Avoid:** Better Thermostat (TRV calibration wrapper — no 0-10V output, weak cooling), SAT (OpenTherm-boiler-only). **Reset expectations:** *no* surveyed HA tool genuinely learns room heat-gain rate — "smart" here means one-shot autotune, not adaptive ML. A well-tuned PID + maintain floor is the honest best answer.

---

## The real diagnosis (corrected)

VT's valve control is **proportional in principle** — for `over_valve` devices the computed `on_percent` is converted to 0–100 % and directly sets valve opening. So the 0/100 slamming is **not** "VT is bang-bang by design"; it's **TPI saturation from too much gain / too large an error**. The fix is reducing gain (`coef_int`) and/or switching to the smoother `auto_regulation` controller — not replacing the tool.

Two things the full verification **refuted** (don't rely on them):
- ❌ VT does **not** expose `minimum_opening_degrees` / `max_opening_degrees` / `opening_threshold` / `max_closing_degree`. **No native maintain-floor exists.** Keep the external clamp.
- ❌ "VT regulation is inherently smooth, never bang-bang" — overstated. Under bad tuning it absolutely saturates to 0/100, which is precisely the observed symptom.

What's confirmed about `auto_regulation` (a PI + feedforward controller, **no `kd`**, **not a learner**):

| Mode | kp | ki | k_ext | offset_max | accum_err_thresh |
|---|---|---|---|---|---|
| Light | 0.2 | 0.05 | 0.05 | 1.5 | 10 |
| Medium | 0.3 | 0.05 | 0.10 | 2 | 20 |
| **Strong** | **0.4** | **0.08** | **0.0** | **5** | **50** |
| Slow | 0.2 | 0.8/288 | 1.0/25 | 2.0 | 2.0×288 |

`kp` = factor on gross error; `ki` = factor on accumulated error; `k_ext` = indoor-outdoor feedforward; `offset_max` = max correction. For a high-gain fast room, **start lower than Strong** — Medium, or Expert with `kp≈0.2`.

---

## Comparison: candidates × criteria

Legend: ✅ strong · 🟡 partial / caveats · ❌ weak/absent · — n/a

| Candidate | Smooth 0-10V | Adapt / auto-tune | Maintain-floor + anti-cycle | 3-speed discrete | Multi-zone + chiller | Presets / sched | Maturity + restart | Migration effort |
|---|---|---|---|---|---|---|---|---|
| **VT (today, plain TPI, coef_int 0.6)** | 🟡 saturates 0/100 (too much gain) | ❌ static | 🟡 external clamp only | ✅ | ✅ | ✅ | 🟡 mature, wedges on restart | — incumbent |
| **VT + lowered `coef_int` (~0.3)** | ✅ smoother mid values | ❌ | 🟡 external clamp (no native floor) | ✅ | ✅ | ✅ | 🟡 same restart risk | ✅ trivial (config) |
| **VT + `auto_regulation` (Medium→Expert)** | ✅ PI + feedforward smoothing | 🟡 static-gain PI, no learning | 🟡 external clamp | ✅ | ✅ | ✅ | 🟡 Expert=global block + restart | ✅ config only |
| **ESPHome `pid` (edge)** | ✅ true continuous float (DAC/PWM) | ✅ Z-N relay autotune (one-shot) | ✅ output-min floor + deadband | 🟡 continuous; 3-speed needs quantize | 🟡 chiller stays in HA | 🟡 presets stay in HA | ✅ survives HA restart | 🟡 per-room ESP + HA glue |
| **ScratMan/HASmartThermostat (HA PID)** | ✅ `pwm:0` → number/light/valve | 🟡 multi-rule autotune (one-shot, "not always working") | ✅ `output_min`/`output_max`; needs external floor logic | 🟡 quantize | 🟡 chiller in HA | 🟡 in HA | 🟡 runs in HA → no restart gain | 🟡 per-room swap |
| **soloam/ha-pid-controller** | ✅ PID sensor → number (0-100) | ❌ manual tune only | 🟡 min/max output; no anti-cycle | 🟡 | 🟡 | ❌ no preset/sched | 🟡 HA-side | 🟡 building block |
| **hacker-cb/smart-thermostat** | ✅ number/input_number PID (0-100, cool-inverted) | ❌ manual only | 🟡 output bounds | 🟡 | 🟡 | 🟡 | 🟡 HA-side | 🟡 building block |
| **Better Thermostat** | ❌ TRV valve-position only | 🟡 PID/MPC beta but TRV-scoped | ❌ | ❌ | ❌ | 🟡 presets | ✅ mature | ❌ wrong tool |
| **SAT (Alexwijn)** | ❌ OpenTherm boiler only | ✅ adaptive gain-sched | — | ❌ | ❌ | 🟡 | ✅ | ❌ wrong hardware |
| **AppDaemon / pyscript PID/MPC** | ✅* | 🟡* | ✅* | ✅* | ✅* | 🟡* | ❌ DIY, you own bugs | ❌ high build |
| **ML / MPC learning add-ons** | — | ❌ none verified production-grade | — | — | — | — | ❌ | — |
| **Adaptive Cover (shades)** | — | 🟡 sun-driven | — | — | 🟡 cuts solar load upstream | — | ✅ HACS | ✅ additive |

`*` = "if you build it." Adaptive Cover internals + AppDaemon/MPC remain lightly verified (see gaps).

---

## Per-candidate notes

### 1 · Versatile Thermostat — is it config, not the tool? → **Yes.**
- **The lever you're missing:** `coef_int` (default `0.6`) is the TPI internal gain. For a fast-warming room it's too high → `on_percent` saturates to 0/1. Lower it (~0.3) for smooth mid values. `coef_ext` default `0.01`.
- **Then layer `auto_regulation`** (Medium first; Expert with custom `kp/ki/k_ext` if needed). PI + feedforward, no `kd`, no learning. Expert = one **global** `auto_regulation_expert:` block for *all* Expert VTherms; needs full restart.
- **Keep the external floor:** ⚠ VT has **no** native maintain-floor/clamp parameter (refuted 0-3). Your 15-70% template clamp stays, or tune so `on_percent` stays above the floor.

### 2 · Better Thermostat — wrong tool. v1.8.0 added AI/MPC/PID/TPI algorithms, **but** they act on **TRV valve-position/calibration**, not a 0-10V `number`; cooling support reported weak. Exclude for the 0-10V priority.

### 3 · HA standalone PID components
- **ScratMan/HASmartThermostat** — strongest HA-side: `pwm:0` → direct value to `number`/light/valve, `output_min`/`output_max` scaling for 0-10V, multi-rule autotune (ziegler-nichols, tyreus-luyben, ciancone-marlin, …). Autotune is one-shot and "not always working." Runs in HA → no restart-robustness gain. Still needs an external floor.
- **soloam/ha-pid-controller** — clean PID→`number`, bounded output, but **manual tune only** (documented 4-phase Z-N by hand), no autotune.
- **hacker-cb/hassio-component-smart-thermostat** — Number+Switch PID mode, 0-100 % output (Kp/Ki/Kd auto-inverted for cool), **manual only**. (A web result falsely gave it autotune — that's ScratMan's, not this repo's.)

### 4 · ESPHome `pid` climate (edge) — strongest fallback for the 0-10V loop
Requires a **continuous float output** (LEDC PWM, I²C DAC GP8403/DFR0971, or PWM→0-10V converter) — ideal for the Shelly-class 0-10V signal. Built-in **Ziegler-Nichols relay autotune** (Åström & Hägglund) emits copy-paste `kp/ki/kd`. **Decisive:** the loop runs on the ESP32 → keeps modulating **through HA restarts** (kills the wedge). Cons: control loop off-HA → harder chiller/multi-zone coordination; autotune is one-shot; the Athom board is 3-speed *discrete* so edge-PID best suits a node driving the **0-10V** output, not the relay units.

### 5-6 · AppDaemon/pyscript MPC & ML offset-learners — **no verified production-grade component** for HA cooling fancoils. EcoEdge-AI surfaced but unverified. Not worth the DIY/own-the-bugs cost here.

### 7 · Honest verdict — **a well-tuned PID + maintain floor beats the "smart" options.** No tool learns heat-gain rate; "smart" = one-shot autotune (ScratMan/ESPHome) or outdoor gain-scheduling (SAT). The `0.5 °C-in-5-min` need is solved by **a set floor + integral action**, not ML.

### 8 · Adaptive Cover (basbruss/adaptive-cover) — sun-position shade automation that cuts solar gain before it hits the fancoil loop; additive, not a thermostat. *Source found but no surviving verified claim — confirm before relying.*

---

## The "0.5 °C in 5 min" maintain need

Don't learn the floor — **set** it, and combine with reduced gain so the controller holds a smooth value above it:
- **VT:** keep external clamp at the floor (~33 % for Tania-class) **and** lower `coef_int` so `on_percent` settles above it instead of bouncing.
- **ESPHome:** `min_power` / output-min on the analog output ≈ floor; PID trims above it.
- **ScratMan:** `output_min` ≈ floor.

---

## Migration sketch (only if the fallback is needed)

| Fancoil type | Today | Re-tune VT (primary) | ESPHome edge-PID (fallback) |
|---|---|---|---|
| **0-10V analog** (Dagmar, P1, P2, Mensa) | VT over_valve → template number → Shelly light | Lower `coef_int`; enable auto_regulation; keep clamp | ESP node runs `pid` climate → 0-10V (DAC); HA sets target via API; VT stops driving these |
| **3-speed Athom** (CS, Meeting, OpenSpace, Entrance, Reception, Tania) | VT over_valve → template step-map → ESP relays | Unchanged | Unchanged — keep in VT/HA (edge-PID buys little for 3 steps) |
| **Chiller** (Shelly Pro 4PM) | demand-driven from VT `hvac_action` | Unchanged | Aggregate demand from ESP outputs **+** remaining VT zones |

**Risk:** if control moves to ESP edge nodes you lose HA-side chiller min-cycle/pre-charge orchestration — demand aggregation must include the ESP rooms or the chiller idles while a room calls. Expert mode being global may force a mix (Medium per-device for fast rooms + clamp). **Rollback:** re-tune is pure config (revert values); ESP path is per-room & additive — the Shelly still accepts the old VT→template path, so fail back one room by repointing its template number + re-enabling its VT entity. **Canary on Dagmar first.**

**Order:** (1) lower `coef_int` + enable auto_regulation on the four 0-10V rooms, observe a week in cool mode; (2) if still saturating/wedging → ESPHome canary on Dagmar → autotune → verify restart-survival → roll out; (3) adopt Adaptive Cover regardless.

---

## What wasn't fully verified
- **Adaptive Cover** — repo found, no surviving verified claim. Confirm separately.
- **ESPHome autotune AUTO-mode constraint** — a claim that autotune needs heat/cool AUTO mode was itself **refuted (1-2)**; treat the constraint as uncertain, test on-device.
- **Exact Expert values for Tania-class fast rooms** — docs give presets, not high-gain tuning; needs empirical on-site tuning from `kp≈0.2` + lowered `coef_int`.
- **AppDaemon/pyscript MPC, ML learners** — no production-grade candidate verified.

## Open questions for Dagmar
- Is the felt problem "slams 0/100" (→ lower `coef_int` + auto_regulation likely fixes it) or "wedges on restart" (→ ESPHome edge-PID)?
- Are you OK with the external clamp staying permanently (VT has no native floor), or is removing the workaround a hard requirement (→ pushes toward ESPHome where output-min is native)?
- Does Expert mode being a single global block conflict with per-room needs (fast rooms vs slow)?

## Sources (23 fetched; primary/high-signal subset)
- VT algorithms — https://github.com/jmcollin78/versatile_thermostat/blob/main/documentation/en/algorithms.md
- VT self-regulation — https://github.com/jmcollin78/versatile_thermostat/blob/main/documentation/en/self-regulation.md
- VT discussions #1668, #459 — auto-regulation config in practice
- ESPHome PID climate — https://esphome.io/components/climate/pid/ · issue #2476
- ScratMan/HASmartThermostat — https://github.com/ScratMan/HASmartThermostat
- soloam/ha-pid-controller — https://github.com/soloam/ha-pid-controller
- hacker-cb/hassio-component-smart-thermostat — https://github.com/hacker-cb/hassio-component-smart-thermostat
- Better Thermostat — repo + better-thermostat.org/working-devices/compatibility + /optimal-settings/algorithm-selection
- SAT — https://github.com/Alexwijn/SAT
- Adaptive Cover — https://github.com/basbruss/adaptive-cover
- HA forums: fan-control-0-10v (276033), esphome fan PID (389227), multizone-thermostat (308898), heatpump+fancoils (732743), PID in AppDaemon (251712), EcoEdge-AI (998485)
</content>
