# Research handoff: best adaptive software thermostats for Home Assistant

> **Pure research session.** No code changes, no config edits. Produce a written
> comparison + recommendation + migration sketch. Render the final report as
> styled HTML in the browser for review (per Dagmar's preference) with the
> markdown as fallback.

## The question
We run **Versatile Thermostat (VT)** to control office fancoils in Home Assistant
and are **disappointed with its control quality** — it does not adapt fast/well
enough to our rooms' thermal behaviour. **Research and compare the best adaptive /
learning software thermostat options for Home Assistant** (and adjacent
approaches), and recommend whether to switch, and to what.

## Our setup (context the recommendation must fit)
- Site: Sales4Italy office, Cassano Magnago. Repo: `~/DEV-DOMOTICA/homeassistant-config-s4it`. HA in Docker on a Synology NAS.
- **Mixed fancoil hardware, both driven by one thermostat abstraction today:**
  - **0-10 V analog fancoils** (Dagmar, Projects 1, Projects 2, Mensa): Shelly Pro 0-10V PM → a *modulating* valve/fan (0-100%). These are the priority — they SHOULD modulate smoothly.
  - **3-speed fancoils** (CS, Meeting, OpenSpace, Entrance, Reception, Tania): ESP32 Athom 4CH relay boards → Low/Med/High (33/66/100) relays, dual-fan rooms cascade to 6 effective steps.
- A shared **chiller** (Shelly Pro 4PM) provides cold water; it's now demand-driven (on when any zone cools, off after sustained no-demand). Whatever thermostat we pick must coexist with chiller coordination.
- Room sensors: UP Sense / Shelly WallDisplay temperature per zone. Outdoor temp + forecast available.
- Motorised sun-shades on some west/east façades (separate concern, but thermal-coupled).

## What's gone wrong with VT (requirements for the replacement)
1. **Bang-bang on the analog valves.** VT's TPI drives the 0-10 V valve toward 0 or 100 rather than holding a smooth mid value. We had to bolt on a manual "maintain band" clamp (15-70%) in template `set_value` to stop the 0%/100% slamming and noise.
2. **No real adaptation.** It doesn't learn the room's heat-gain/loss rate. Observed: **Tania rose 0.5 °C within 5 minutes** of its fancoil going low/off — so the maintain minimum is ~**33% (both fancoils on low)**, not something VT discovers. The controller should learn/auto-tune this.
3. **Anti-short-cycle / maintain-minimum.** Must avoid the no-speed → high-speed → no-speed oscillation; should hold a continuous low maintenance output that actually holds setpoint.
4. **Startup fragility.** VT is slow to re-drive valves after a restart and can wedge ("startup not done"), ignoring commands.
5. **Preset/scheduling needs:** comfort/eco/boost + an overheat/"boil" cap (keep ≤30 °C off-hours), workday schedule, manual overrides with revert, early-morning pre-cool.

## Candidates to evaluate (not exhaustive — find others)
- **Versatile Thermostat** — but properly assessing its features we may NOT be using: `auto-regulation` modes (light/medium/strong/expert/PID-like), `over_valve` proportional regulation, self-regulation dtemp/period. Is our problem config, not the tool?
- **Better Thermostat** — calibration/eco; mostly for TRVs — does it suit fancoils/0-10V?
- **HA "Smart Thermostat" / PID thermostat** custom components (PID control, e.g. ScratchyMcMurmur-style) — proportional output to a `number`/0-10V; auto-tune?
- **PID via ESPHome `climate` running on the Athom ESP32 / a node controlling the 0-10V** — push control to the edge device; pros/cons vs HA-side.
- **AppDaemon / pyscript custom PID or MPC** controllers.
- **Model-predictive / learning** options (any HA-integrated MPC, or HVAC "learning" addons).
- **Adaptive Cover** (for the shades — secondary, but note if relevant).
- Honest take on whether a **simple well-tuned PID with a maintain floor** beats all the "smart" options for our hardware.

## Evaluation criteria (score each)
- Smooth **modulation of a 0-10 V analog output** (the key failing today).
- **Adaptation / auto-tuning** to room thermal response (heat-gain rate, lag).
- **Maintain-minimum + anti-short-cycle** behaviour.
- **3-speed fancoil** support (discrete steps) alongside analog.
- **Multi-zone** with a **shared chiller** (coordination / demand aggregation).
- **Presets + scheduling + overheat cap + pre-cool**.
- HA integration maturity, maintenance/community health, restart robustness.
- **Migration effort** from VT (entities, automations, history).

## Deliverable
1. Comparison table (candidates × criteria).
2. Clear recommendation: stay-and-retune-VT vs switch (to what), with the 1-2 line "why".
3. If "retune VT": the specific settings to try (auto-regulation/PID mode, coefficients) to get smooth analog modulation + maintain-floor without our manual clamp.
4. If "switch": a migration sketch (what changes per fancoil type, risk, rollback).
5. Note any approach that solves the **0.5 °C-in-5-min fast-warming** maintenance need elegantly.

## Pointers for the researcher
- Current climate design + gotchas: this repo's `automations.yaml` / `templates.yaml`, and the session note `dagmars-desk/dev-journal/sessions/2026-06-24-domotica-climate-redesign.md`.
- Key constraints already learned: VTs expose no selectable `frost` preset; VT setpoint max_temp caps at 30; the 0-10V path is template-number → Shelly light brightness.
- Sources to mine: HA community forum, HACS, VT docs (jmcollin78/versatile_thermostat), ESPHome climate/PID docs, GitHub for HA PID thermostats.
