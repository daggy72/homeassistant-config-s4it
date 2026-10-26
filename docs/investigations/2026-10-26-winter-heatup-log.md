# Winter heat-up log — 2026-10-26

Season switched to winter 07:59 Rome. Report every 30 min from `scripts/heatup_report.py` (read-only, HA recorder history).
"reacts" = time from the switch until the room is 0.3 °C warmer than at the start. "C/h" = warm-up rate after it reacts.

Notes:
- 08:15 Entrance heat presets were 30/30/30 at runtime (config layer `update_vt_presets.py` says COMMON = OpenSpace). Set to 19/20/22 with Dagmar's OK. Entrance and OpenSpace share `sensor.up_sense_temperature_3`.
- Mensa is in VT `safety` mode: the Mensa wall display only reports on change (last value 06:47), so VT sees a stale sensor after 60 min and runs at 10 %. Projects 2 uses the same sensor. Mensa and Projects 2 numbers are therefore slower than real.
- Chiller is not used for heating (season automation turns it off in winter).

```
Season switch: 2026-10-26 07:59  now: 08:37  elapsed 0h38
Outdoor: 7.6 -> 8.5 C (min 7.6, max 8.5)
Chiller (not used for heating): 07:59 off

room                       preset   target  start    now    +C  reacts   C/h at target
climate_mensa              eco        19.0   16.9   18.8  +1.9    0h19     -         -
fancoil_cs                 eco        18.0   17.0   19.4  +2.4    0h14     -      0h24
fancoil_entrance           comfort    20.0   16.9   19.2  +2.3    0h15     -         -
fancoil_meeting            comfort    21.0   16.9   21.6  +4.7    0h14     -      0h24
fancoil_openspace          comfort    20.0   16.9   19.2  +2.3    0h15     -         -
fancoil_reception          comfort    21.0   15.8   20.0  +4.2    0h06  7.40         -
fancoil_tania              comfort    21.0   16.4   22.1  +5.7    0h14     -      0h29
projects_1                 comfort    21.0   16.7   19.7  +3.0    0h10     -         -
projects_2                 eco        18.0   16.9   18.8  +1.9    0h19     -      0h23
```

```
Season switch: 2026-10-26 07:59  now: 09:07  elapsed 1h08
Outdoor: 7.6 -> 8.5 C (min 7.6, max 8.5)
Chiller (not used for heating): 07:59 off

room                       preset   target  start    now    +C  reacts   C/h at target
climate_mensa              eco        19.0   16.9   19.1  +2.2    0h19  2.32      0h43
fancoil_cs                 eco        18.0   17.0   19.5  +2.5    0h14  2.45      0h24
fancoil_entrance           comfort    20.0   16.9   19.9  +3.0    0h15  3.06      0h45
fancoil_meeting            eco        18.0   16.9   21.3  +4.4    0h14  4.57      0h14
fancoil_openspace          comfort    20.0   16.9   19.9  +3.0    0h15  3.06      0h45
fancoil_reception          comfort    21.0   15.8   21.1  +5.3    0h06  4.87      1h06
fancoil_tania              comfort    21.0   16.4   21.4  +5.0    0h14  5.24      0h29
projects_1                 comfort    21.0   16.7   20.0  +3.3    0h10  3.12         -
projects_2                 eco        18.0   16.9   19.1  +2.2    0h19  2.32      0h23
```

```
Season switch: 2026-10-26 07:59  now: 09:37  elapsed 1h38
Outdoor: 7.6 -> 11.6 C (min 7.6, max 11.6)
Chiller (not used for heating): 07:59 off

room                       preset   target  start    now    +C  reacts   C/h at target
climate_mensa              eco        19.0   16.9   19.3  +2.4    0h19  1.59      0h43
fancoil_cs                 eco        18.0   17.0   19.9  +2.9    0h14  1.86      0h24
fancoil_entrance           comfort    20.0   16.9   20.1  +3.2    0h15  2.10      0h45
fancoil_meeting            eco        18.0   16.9   22.9  +6.0    0h14  4.08      0h14
fancoil_openspace          comfort    20.0   16.9   20.1  +3.2    0h15  2.10      0h45
fancoil_reception          comfort    21.0   15.8   21.1  +5.3    0h06  3.27      1h06
fancoil_tania              comfort    21.0   16.4   20.8  +4.4    0h14  2.93      0h29
projects_1                 comfort    21.0   16.7   20.1  +3.4    0h10  2.12         -
projects_2                 eco        18.0   16.9   19.3  +2.4    0h19  1.59      0h23
```

```
Season switch: 2026-10-26 07:59  now: 10:07  elapsed 2h08
Outdoor: 7.6 -> 11.6 C (min 7.6, max 11.6)
Chiller (not used for heating): 07:59 off

room                       preset   target  start    now    +C  reacts   C/h at target
climate_mensa              eco        19.0   16.9   19.5  +2.6    0h19  1.26      0h43
fancoil_cs                 eco        18.0   17.0   20.2  +3.2    0h14  1.53      0h24
fancoil_entrance           comfort    20.0   16.9   20.2  +3.3    0h15  1.59      0h45
fancoil_meeting            eco        18.0   16.9   25.4  +8.5    0h14  4.32      0h14
fancoil_openspace          comfort    20.0   16.9   20.2  +3.3    0h15  1.59      0h45
fancoil_reception          comfort    21.0   15.8   21.1  +5.3    0h06  2.47      1h06
fancoil_tania              comfort    21.0   16.4   21.1  +4.7    0h14  2.32      0h29
projects_1                 comfort    21.0   16.7   20.9  +4.2    0h10  1.99         -
projects_2                 eco        18.0   16.9   19.5  +2.6    0h19  1.26      0h23
```

```
Season switch: 2026-10-26 07:59  now: 10:37  elapsed 2h38
Outdoor: 7.6 -> 13.5 C (min 7.6, max 13.5)
Chiller (not used for heating): 07:59 off

room                       preset   target  start    now    +C  reacts   C/h at target
climate_mensa              eco        19.0   16.9   19.7  +2.8    0h19  1.08      0h43
fancoil_cs                 eco        18.0   17.0   20.5  +3.5    0h14  1.33      0h24
fancoil_entrance           comfort    20.0   16.9   20.1  +3.2    0h15  1.22      0h45
fancoil_meeting            eco        18.0   16.9   26.2  +9.3    0h14  3.75      0h14
fancoil_openspace          comfort    20.0   16.9   20.1  +3.2    0h15  1.22      0h45
fancoil_reception          comfort    21.0   15.8   21.1  +5.3    0h06  1.98      1h06
fancoil_tania              comfort    21.0   16.4   21.4  +5.0    0h14  1.96      0h29
projects_1                 comfort    21.0   16.7   20.7  +4.0    0h10  1.50      2h11
projects_2                 eco        18.0   16.9   19.7  +2.8    0h19  1.08      0h23
```

```
Season switch: 2026-10-26 07:59  now: 11:07  elapsed 3h08
Outdoor: 7.6 -> 13.5 C (min 7.6, max 13.5)
Chiller (not used for heating): 07:59 off

room                       preset   target  start    now    +C  reacts   C/h at target
climate_mensa              eco        19.0   16.9   20.0  +3.1    0h19  0.99      0h43
fancoil_cs                 eco        18.0   17.0   20.8  +3.8    0h14  1.21      0h24
fancoil_entrance           comfort    20.0   16.9   20.1  +3.2    0h15  1.01      0h45
fancoil_meeting            eco        18.0   16.9   26.7  +9.8    0h14  3.28      0h14
fancoil_openspace          comfort    20.0   16.9   20.1  +3.2    0h15  1.01      0h45
fancoil_reception          comfort    21.0   15.8   21.5  +5.7    0h06  1.78      1h06
fancoil_tania              comfort    21.0   16.4   22.4  +6.0    0h14  1.97      0h29
projects_1                 comfort    21.0   16.7   20.8  +4.1    0h10  1.28      2h11
projects_2                 eco        18.0   16.9   20.0  +3.1    0h19  0.99      0h23
```

## Result after 3 h (11:07)

- Every room reacted (+0.3 °C) 6–19 min after the switch. Reception first (6 min), Mensa / Projects 2 last (19 min; same stale-sensor display).
- Warm-up rate after reacting: about 1.0–2.0 °C/h. Slowest: Mensa, Projects 2, OpenSpace, Entrance (~1.0). Fastest normal room: Tania (~2.0).
- Time to target: 14 min – 2 h 11. Projects 1 was slowest (2 h 11 to 21 °C).
- Caveat: outdoor rose 7.6 → 13.5 °C during the test (sunny morning), so these numbers are a best case. A cold, grey morning will be slower.
- Fancoil Dagmar switched off at ~08:40 (works in the office), so it is not in the result.
- 11:10 Meeting overshoot: 26.7 °C with target 18. VT asked 0 %, but fancoil_05 stayed on at 33 % since 09:17. Setting `number.fancoil_meeting` to 0 stopped both fans. Root cause not proven (the template number showed 16 = average of 33 and 0, so VT may not have re-sent 0). `automation.fancoil_speed_control*` show `unavailable` but are orphan registry entries; speed control lives in the template numbers in templates.yaml.
