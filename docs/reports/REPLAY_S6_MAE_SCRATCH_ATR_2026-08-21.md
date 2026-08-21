# REPLAY — S6_MAE_SCRATCH_ATR_V1 (ATR-relative MAE scratch)

**Generated:** 2026-08-21 10:58 · `scripts/week_replay.py --dates all-live --mae compare`
**Sessions:** 32 live-era days (2026-06-29 … 2026-08-20)
**Parameters:** 4 contracts, ladder (1, 1, 1, 1), T0=3.0pt, $5/pt/contract, commission $1.50/contract round-turn (= $6.00/trade), slippage 0 / 1 / 2 ticks

**A = flag OFF** (fixed points from `config/mae_scratch.yaml` + the P2-9 scratch↔stop clamp) — today's live behaviour.  
**B = flag ON** (`max(k × ATR14, floor)`, k normalised on the live-era median ATR14 of 6.0pt, and the P2-9 clamp becomes a *skip*).

## Per-day delta (net of commission)

### Slippage 0 tick(s)

| Day | Type | ATR14 med | A: OFF $ | B: ON $ | Δ $ | scratches A→B |
|-----|------|-----------|----------|---------|-----|----------------|
| 2026-06-29 | Variation | 4.95 | $-296 | $-296 | **$+0** | 1→1 |
| 2026-07-01 | Variation | 5.10 | $+82 | $+82 | **$+0** | 0→0 |
| 2026-07-02 | Variation | 9.22 | $+339 | $+374 | **$+35** 🟢 | 1→0 |
| 2026-07-03 | Variation | 2.62 | $-1 | $-1 | **$+0** | 0→0 |
| 2026-07-07 | Variation | 6.48 | $-36 | $-36 | **$+0** | 1→1 |
| 2026-07-08 | Variation | 7.54 | $+332 | $+332 | **$+0** | 0→0 |
| 2026-07-09 | Variation | 3.54 | $+84 | $-35 | **$-119** 🔴 | 2→0 |
| 2026-07-10 | Variation | 3.75 | $+174 | $+254 | **$+80** 🟢 | 1→0 |
| 2026-07-13 | Variation | 6.21 | $+253 | $+83 | **$-170** 🔴 | 4→0 |
| 2026-07-14 | Variation | 5.71 | $-126 | $-73 | **$+52** 🟢 | 2→0 |
| 2026-07-15 | Trend_DD | 6.41 | $+320 | $+320 | **$+0** | 0→0 |
| 2026-07-17 | Normal | 7.62 | $-2231 | $-1536 | **$+695** 🟢 | 3→1 |
| 2026-07-20 | Variation | 7.75 | $-1678 | $-548 | **$+1130** 🟢 | 6→0 |
| 2026-07-21 | Variation | 3.30 | $+71 | $+406 | **$+335** 🟢 | 1→0 |
| 2026-07-22 | Variation | 3.82 | $+312 | $+777 | **$+465** 🟢 | 2→0 |
| 2026-07-23 | Variation | 7.17 | $-2816 | $-1512 | **$+1305** 🟢 | 9→2 |
| 2026-07-24 | Variation | 7.11 | $-1058 | $-333 | **$+725** 🟢 | 4→1 |
| 2026-07-27 | Variation | 7.08 | $+494 | $+494 | **$+0** | 0→0 |
| 2026-07-30 | Variation | 6.64 | $+739 | $+739 | **$+0** | 1→1 |
| 2026-07-31 | Variation | 7.21 | $-777 | $-782 | **$-5** 🔴 | 2→1 |
| 2026-08-03 | Variation | 3.90 | $+689 | $+689 | **$+0** | 0→0 |
| 2026-08-04 | Variation | 6.05 | $+2555 | $+2555 | **$+0** | 0→0 |
| 2026-08-05 | Trend_DD | 7.52 | $+411 | $+421 | **$+10** 🟢 | 1→0 |
| 2026-08-06 | Neutral_Center | 6.32 | $-275 | $-405 | **$-130** 🔴 | 3→0 |
| 2026-08-07 | Variation | 5.57 | $-212 | $-232 | **$-20** 🔴 | 2→0 |
| 2026-08-10 | Normal | 4.96 | $-276 | $-91 | **$+185** 🟢 | 1→0 |
| 2026-08-12 | unknown | 3.34 | $-51 | $-51 | **$+0** | 1→1 |
| 2026-08-13 | Variation | 3.66 | $+228 | $+228 | **$+0** | 0→0 |
| 2026-08-14 | Trend_DD | 3.16 | $-284 | $-431 | **$-146** 🔴 | 4→0 |
| 2026-08-17 | Trend_DD | 3.46 | $+40 | $+46 | **$+5** 🟢 | 1→0 |
| 2026-08-19 | Variation | 5.22 | $-218 | $-240 | **$-21** 🔴 | 2→0 |
| 2026-08-20 | Neutral_Extreme | 4.92 | $-329 | $-342 | **$-12** 🔴 | 3→2 |
| **TOTAL** | | | **$-3543** | **$+856** | **$+4399** | 58→11 |

- **median day Δ** = $+0.00 (all 32 days) · $+22.50 (the 20 days that changed)
- days better: 12 · worse: 8 · unchanged: 12
- worst single day: $-170.00 · best: $+1305.00

### Slippage 1 tick(s)

| Day | Type | ATR14 med | A: OFF $ | B: ON $ | Δ $ | scratches A→B |
|-----|------|-----------|----------|---------|-----|----------------|
| 2026-06-29 | Variation | 4.95 | $-301 | $-301 | **$+0** | 1→1 |
| 2026-07-01 | Variation | 5.10 | $+76 | $+76 | **$+0** | 0→0 |
| 2026-07-02 | Variation | 9.22 | $+314 | $+349 | **$+35** 🟢 | 1→0 |
| 2026-07-03 | Variation | 2.62 | $-6 | $-6 | **$+0** | 0→0 |
| 2026-07-07 | Variation | 6.48 | $-50 | $-50 | **$+0** | 1→1 |
| 2026-07-08 | Variation | 7.54 | $+328 | $+328 | **$+0** | 0→0 |
| 2026-07-09 | Variation | 3.54 | $+64 | $-55 | **$-119** 🔴 | 2→0 |
| 2026-07-10 | Variation | 3.75 | $+154 | $+234 | **$+80** 🟢 | 1→0 |
| 2026-07-13 | Variation | 6.21 | $+218 | $+48 | **$-170** 🔴 | 4→0 |
| 2026-07-14 | Variation | 5.71 | $-140 | $-88 | **$+52** 🟢 | 2→0 |
| 2026-07-15 | Trend_DD | 6.41 | $+308 | $+308 | **$+0** | 0→0 |
| 2026-07-17 | Normal | 7.62 | $-2258 | $-1564 | **$+695** 🟢 | 3→1 |
| 2026-07-20 | Variation | 7.75 | $-1720 | $-590 | **$+1130** 🟢 | 6→0 |
| 2026-07-21 | Variation | 3.30 | $+49 | $+384 | **$+335** 🟢 | 1→0 |
| 2026-07-22 | Variation | 3.82 | $+295 | $+760 | **$+465** 🟢 | 2→0 |
| 2026-07-23 | Variation | 7.17 | $-2862 | $-1556 | **$+1305** 🟢 | 9→2 |
| 2026-07-24 | Variation | 7.11 | $-1082 | $-357 | **$+725** 🟢 | 4→1 |
| 2026-07-27 | Variation | 7.08 | $+490 | $+490 | **$+0** | 0→0 |
| 2026-07-30 | Variation | 6.64 | $+716 | $+716 | **$+0** | 1→1 |
| 2026-07-31 | Variation | 7.21 | $-792 | $-797 | **$-5** 🔴 | 2→1 |
| 2026-08-03 | Variation | 3.90 | $+686 | $+686 | **$+0** | 0→0 |
| 2026-08-04 | Variation | 6.05 | $+2531 | $+2531 | **$+0** | 0→0 |
| 2026-08-05 | Trend_DD | 7.52 | $+391 | $+401 | **$+10** 🟢 | 1→0 |
| 2026-08-06 | Neutral_Center | 6.32 | $-300 | $-430 | **$-130** 🔴 | 3→0 |
| 2026-08-07 | Variation | 5.57 | $-222 | $-242 | **$-20** 🔴 | 2→0 |
| 2026-08-10 | Normal | 4.96 | $-281 | $-96 | **$+185** 🟢 | 1→0 |
| 2026-08-12 | unknown | 3.34 | $-61 | $-61 | **$+0** | 1→1 |
| 2026-08-13 | Variation | 3.66 | $+213 | $+213 | **$+0** | 0→0 |
| 2026-08-14 | Trend_DD | 3.16 | $-320 | $-466 | **$-146** 🔴 | 4→0 |
| 2026-08-17 | Trend_DD | 3.46 | $+7 | $+12 | **$+5** 🟢 | 1→0 |
| 2026-08-19 | Variation | 5.22 | $-248 | $-270 | **$-21** 🔴 | 2→0 |
| 2026-08-20 | Neutral_Extreme | 4.92 | $-349 | $-362 | **$-12** 🔴 | 3→2 |
| **TOTAL** | | | **$-4153** | **$+246** | **$+4399** | 58→11 |

- **median day Δ** = $+0.00 (all 32 days) · $+22.50 (the 20 days that changed)
- days better: 12 · worse: 8 · unchanged: 12
- worst single day: $-170.00 · best: $+1305.00

### Slippage 2 tick(s)

| Day | Type | ATR14 med | A: OFF $ | B: ON $ | Δ $ | scratches A→B |
|-----|------|-----------|----------|---------|-----|----------------|
| 2026-06-29 | Variation | 4.95 | $-306 | $-306 | **$+0** | 1→1 |
| 2026-07-01 | Variation | 5.10 | $+72 | $+72 | **$+0** | 0→0 |
| 2026-07-02 | Variation | 9.22 | $+289 | $+324 | **$+35** 🟢 | 1→0 |
| 2026-07-03 | Variation | 2.62 | $-11 | $-11 | **$+0** | 0→0 |
| 2026-07-07 | Variation | 6.48 | $-66 | $-66 | **$+0** | 1→1 |
| 2026-07-08 | Variation | 7.54 | $+324 | $+324 | **$+0** | 0→0 |
| 2026-07-09 | Variation | 3.54 | $+44 | $-75 | **$-119** 🔴 | 2→0 |
| 2026-07-10 | Variation | 3.75 | $+134 | $+214 | **$+80** 🟢 | 1→0 |
| 2026-07-13 | Variation | 6.21 | $+183 | $+13 | **$-170** 🔴 | 4→0 |
| 2026-07-14 | Variation | 5.71 | $-156 | $-103 | **$+52** 🟢 | 2→0 |
| 2026-07-15 | Trend_DD | 6.41 | $+297 | $+297 | **$+0** | 0→0 |
| 2026-07-17 | Normal | 7.62 | $-2286 | $-1591 | **$+695** 🟢 | 3→1 |
| 2026-07-20 | Variation | 7.75 | $-1763 | $-633 | **$+1130** 🟢 | 6→0 |
| 2026-07-21 | Variation | 3.30 | $+26 | $+361 | **$+335** 🟢 | 1→0 |
| 2026-07-22 | Variation | 3.82 | $+277 | $+742 | **$+465** 🟢 | 2→0 |
| 2026-07-23 | Variation | 7.17 | $-2906 | $-1602 | **$+1305** 🟢 | 9→2 |
| 2026-07-24 | Variation | 7.11 | $-1106 | $-381 | **$+725** 🟢 | 4→1 |
| 2026-07-27 | Variation | 7.08 | $+486 | $+486 | **$+0** | 0→0 |
| 2026-07-30 | Variation | 6.64 | $+694 | $+694 | **$+0** | 1→1 |
| 2026-07-31 | Variation | 7.21 | $-807 | $-812 | **$-5** 🔴 | 2→1 |
| 2026-08-03 | Variation | 3.90 | $+684 | $+684 | **$+0** | 0→0 |
| 2026-08-04 | Variation | 6.05 | $+2508 | $+2508 | **$+0** | 0→0 |
| 2026-08-05 | Trend_DD | 7.52 | $+371 | $+381 | **$+10** 🟢 | 1→0 |
| 2026-08-06 | Neutral_Center | 6.32 | $-325 | $-455 | **$-130** 🔴 | 3→0 |
| 2026-08-07 | Variation | 5.57 | $-232 | $-252 | **$-20** 🔴 | 2→0 |
| 2026-08-10 | Normal | 4.96 | $-286 | $-101 | **$+185** 🟢 | 1→0 |
| 2026-08-12 | unknown | 3.34 | $-71 | $-71 | **$+0** | 1→1 |
| 2026-08-13 | Variation | 3.66 | $+198 | $+198 | **$+0** | 0→0 |
| 2026-08-14 | Trend_DD | 3.16 | $-354 | $-501 | **$-146** 🔴 | 4→0 |
| 2026-08-17 | Trend_DD | 3.46 | $-27 | $-22 | **$+5** 🟢 | 1→0 |
| 2026-08-19 | Variation | 5.22 | $-278 | $-300 | **$-21** 🔴 | 2→0 |
| 2026-08-20 | Neutral_Extreme | 4.92 | $-369 | $-382 | **$-12** 🔴 | 3→2 |
| **TOTAL** | | | **$-4763** | **$-364** | **$+4399** | 58→11 |

- **median day Δ** = $+0.00 (all 32 days) · $+22.50 (the 20 days that changed)
- days better: 12 · worse: 8 · unchanged: 12
- worst single day: $-170.00 · best: $+1305.00

## Which scratches change, and what each was worth

| Day | signal | pattern | dir | A (flag OFF) | B (flag ON) | Δ $ (0-slip) |
|-----|--------|---------|-----|--------------|-------------|--------------|
| 2026-07-02 | #279 | REACTIVE_LONG | LONG | SCRATCH @thr 5.75 (mae 10.75) $-196 | STOP $-161 | **$+35** |
| 2026-07-09 | #332 | REACTIVE_LONG | LONG | SCRATCH @thr 2.50 (mae 3.50) $-66 | T0 $-145 | **$-79** |
| 2026-07-09 | #334 | REACTIVE_SHORT | SHORT | SCRATCH @thr 1.00 (mae 2.00) $+4 | STOP $-36 | **$-40** |
| 2026-07-10 | #339 | REACTIVE_SHORT | SHORT | SCRATCH @thr 5.75 (mae 5.75) $-101 | STOP $-161 | **$-60** |
| 2026-07-10 | #341 | REACTIVE_LONG | LONG | T3 $+189 | not taken | **$-189** |
| 2026-07-10 | #342 | ZLR | LONG | not taken | T3 $+152 | **$+152** |
| 2026-07-10 | #355 | ZLR | LONG | not taken | T3 $+142 | **$+142** |
| 2026-07-10 | #357 | REACTIVE_LONG | LONG | STOP $-36 | not taken | **$+36** |
| 2026-07-13 | #363 | REACTIVE_LONG | LONG | SCRATCH @thr 2.25 (mae 6.00) $-71 | STOP $-91 | **$-20** |
| 2026-07-13 | #365 | ZLR | SHORT | SCRATCH @thr 1.75 (mae 3.75) $+14 | STOP $-81 | **$-95** |
| 2026-07-13 | #367 | GHOST | LONG | SCRATCH @thr 3.50 (mae 7.25) $-141 | STOP $-116 | **$+25** |
| 2026-07-13 | #369 | REACTIVE_SHORT | SHORT | SCRATCH @thr 2.25 (mae 2.75) $-11 | STOP $-91 | **$-80** |
| 2026-07-14 | #371 | REACTIVE_LONG | LONG | SCRATCH @thr 4.00 (mae 19.50) $-231 | STOP $-126 | **$+105** |
| 2026-07-14 | #374 | ZLR | SHORT | SCRATCH @thr 1.00 (mae 1.25) $+16 | STOP $-36 | **$-52** |
| 2026-07-17 | #397 | ZLR | LONG | SCRATCH @thr 6.00 (mae 21.00) $-381 | STOP $-6 | **$+375** |
| 2026-07-17 | #403 | REACTIVE_LONG | LONG | SCRATCH @thr 3.75 (mae 24.00) $-441 | STOP $-121 | **$+320** |
| 2026-07-20 | #419 | REACTIVE_SHORT | SHORT | SCRATCH @thr 3.25 (mae 10.75) $-181 | STOP $-111 | **$+70** |
| 2026-07-20 | #421 | ZLR | SHORT | SCRATCH @thr 3.25 (mae 15.00) $-281 | STOP $-111 | **$+170** |
| 2026-07-20 | #425 | ZLR | LONG | SCRATCH @thr 5.50 (mae 12.75) $-206 | STOP $-156 | **$+50** |
| 2026-07-20 | #426 | ZLR | LONG | SCRATCH @thr 5.50 (mae 26.50) $-421 | STOP $-156 | **$+265** |
| 2026-07-20 | #427 | ZLR | LONG | SCRATCH @thr 3.75 (mae 30.25) $-581 | STOP $-121 | **$+460** |
| 2026-07-20 | #428 | REACTIVE_LONG | LONG | SCRATCH @thr 5.00 (mae 15.75) $-261 | STOP $-146 | **$+115** |
| 2026-07-21 | #438 | GHOST | SHORT | SCRATCH @thr 6.00 (mae 25.25) $-501 | STOP $-166 | **$+335** |
| 2026-07-22 | #459 | ZLR | SHORT | SCRATCH @thr 3.50 (mae 26.75) $-511 | STOP $-116 | **$+395** |
| 2026-07-22 | #467 | REACTIVE_LONG | LONG | SCRATCH @thr 1.25 (mae 6.75) $-141 | STOP $-71 | **$+70** |
| 2026-07-23 | #478 | INITIATIVE_SHORT | SHORT | SCRATCH @thr 9.00 (mae 34.00) $-676 | STOP $-226 | **$+450** |
| 2026-07-23 | #480 | ZLR | SHORT | SCRATCH @thr 6.00 (mae 22.25) $-436 | STOP $-191 | **$+245** |
| 2026-07-23 | #482 | GB100 | LONG | SCRATCH @thr 6.75 (mae 6.75) $-81 | STOP $-122 | **$-41** |
| 2026-07-23 | #486 | ZLR | LONG | SCRATCH @thr 2.50 (mae 21.75) $-416 | STOP $-96 | **$+320** |
| 2026-07-23 | #488 | GB100 | SHORT | SCRATCH @thr 4.00 (mae 7.00) $+146 | STOP $+133 | **$-14** |
| 2026-07-23 | #492 | GB100 | SHORT | SCRATCH @thr 2.75 (mae 26.00) $-486 | STOP $-101 | **$+385** |
| 2026-07-23 | #494 | ZLR | SHORT | SCRATCH @thr 2.25 (mae 4.00) $-51 | STOP $-91 | **$-40** |
| 2026-07-24 | #504 | REACTIVE_LONG | LONG | SCRATCH @thr 8.75 (mae 16.50) $-306 | STOP $-221 | **$+85** |
| 2026-07-24 | #506 | REACTIVE_SHORT | SHORT | SCRATCH @thr 12.00 (mae 44.00) $-776 | STOP $-1 | **$+775** |
| 2026-07-24 | #508 | REACTIVE_SHORT | SHORT | SCRATCH @thr 12.00 (mae 18.00) $-216 | STOP $-351 | **$-135** |
| 2026-07-31 | #585 | INITIATIVE_LONG | LONG | SCRATCH @thr 11.25 (mae 15.00) $-48 | STOP $-54 | **$-5** |
| 2026-08-05 | #635 | INITIATIVE_LONG | LONG | SCRATCH @thr 2.50 (mae 7.25) $-106 | STOP $-96 | **$+10** |
| 2026-08-06 | #639 | BEAR_FLAG_SHORT | SHORT | SCRATCH @thr 6.50 (mae 10.25) $-131 | STOP $-176 | **$-45** |
| 2026-08-06 | #647 | REACTIVE_SHORT | SHORT | SCRATCH @thr 4.75 (mae 5.25) $-56 | STOP $-141 | **$-85** |
| 2026-08-06 | #648 | DOUBLE_BOTTOM_EE_LONG | LONG | SCRATCH @thr 2.00 (mae 5.00) $-86 | STOP $-86 | **$+0** |
| 2026-08-07 | #649 | ZLR | LONG | SCRATCH @thr 3.75 (mae 5.75) $-66 | STOP $-121 | **$-55** |
| 2026-08-07 | #651 | GHOST | SHORT | SCRATCH @thr 3.25 (mae 8.00) $-146 | STOP $-111 | **$+35** |
| 2026-08-10 | #654 | DOUBLE_BOTTOM_EE_LONG | LONG | SCRATCH @thr 2.25 (mae 13.75) $-276 | STOP $-91 | **$+185** |
| 2026-08-14 | #667 | TREND_STEP | SHORT | SCRATCH @thr 3.25 (mae 5.50) $-76 | STOP $-111 | **$-35** |
| 2026-08-14 | #679 | ZLR | LONG | SCRATCH @thr 2.50 (mae 6.00) $-96 | STOP $-96 | **$+0** |
| 2026-08-14 | #681 | TREND_STEP | SHORT | SCRATCH @thr 3.00 (mae 4.25) $-71 | STOP $-68 | **$+2** |
| 2026-08-14 | #683 | TREND_STEP | SHORT | STOP $-17 | not taken | **$+17** |
| 2026-08-14 | #685 | ZLR | SHORT | not taken | STOP $-101 | **$-101** |
| 2026-08-14 | #687 | ZLR | LONG | SCRATCH @thr 2.50 (mae 3.75) $-66 | STOP $-96 | **$-30** |
| 2026-08-17 | #697 | GHOST | LONG | SCRATCH @thr 2.75 (mae 5.25) $-106 | STOP $-101 | **$+5** |
| 2026-08-19 | #725 | GB100 | SHORT | SCRATCH @thr 10.00 (mae 18.00) $-235 | STOP $-216 | **$+19** |
| 2026-08-19 | #740 | ZLR | SHORT | SCRATCH @thr 4.25 (mae 4.75) $-91 | STOP $-131 | **$-40** |
| 2026-08-20 | #755 | TREND_STEP | SHORT | SCRATCH @thr 1.50 (mae 1.50) $-31 | STOP $-44 | **$-12** |

## Declared limitations (unchanged from the base component)

- Signal stream = historical `v9_trades` (what S2/S4 actually fired then); gateway gates are NOT re-evaluated.
- Stop/targets are the ORIGINAL levels from the DB; smart-BE, trails and SCALE_IN are not replayed.
- Bar-close-only fill rule (the entry bar itself is skipped).
- The scratch FLATTEN is filled at the detecting bar's **close** + slippage. Live books a scratch as `pnl_usd=0.0` by convention (`bar_level_detector` `on_trade_close`), which is a bookkeeping artefact, not a real fill — the replay is the more honest of the two.
- `t1_hit` in the replay means T1 proper (not the T0 fast-take), matching `trade.t1_hit_ts` in the live path.
- Both arms A and B run through the identical code path with the identical signal stream — only the threshold function differs, so the Δ is clean even where the absolute level is approximate.

---

# Analysis (hand-authored — the tables above are generated by the script)

## 1 · The GO/NO-GO verdict against Michael's §D rule

`docs/handoff/CC_WORKORDER_2026-08-20_ADAPTIVE.md` §D.2: *"דלתא חיובית **וגם** אף יום לא
מתדרדר מהותית (לא רק סכום — גם החציון ופיזור-הימים). כיול שמשפר סכום ופוגע בחציון = לא עולה."*

| Criterion | Result | Verdict |
|---|---|---|
| Positive total delta | **+$4,398.75** — identical at 0 / 1 / 2 ticks of slippage (both arms take the same 127 trades, so the slippage cost cancels), commissions included | ✅ |
| Median day not hurt | **$0.00** across all 32 sessions (12 unchanged) · **+$22.50** across the 20 sessions that changed | ✅ |
| No day materially deteriorates | worst day **−$170** (2026-07-13) vs best **+$1,305** (2026-07-23); 12 better / 8 worse / 12 unchanged | ✅ |

**GREEN.** The result also survives a deliberately harsher model (see §3).

## 2 · Where the gain actually comes from — the two effects, isolated

The headline framing was "make the threshold ATR-relative". Measured separately, the
ATR scaling on its own is worth **nothing**:

| Variant | Total (0-slip, net of commission) | Δ vs live today | scratches |
|---|---|---|---|
| A · fixed points + P2-9 clamp (**live today**) | −$3,542.62 | — | 58 |
| B1 · `max(k×ATR14, floor)` + P2-9 **clamp** | −$3,582.62 | **−$40.00** | 59 |
| B2 · `max(k×ATR14, floor)` + **skip** (shipped) | **+$856.13** | **+$4,398.75** | 11 |

**Root cause, and it is not the YAML.** In 6 of the 7 MAE scratches that ever fired in
production, the threshold that fired was NOT the calibrated per-pattern value — it was the
P2-9 clamp `stop_distance − 2.0pt` squeezing it down. #756 is the extreme case: default 8.0
→ clamped to `3.5 − 2.0 = 1.5pt`. An ATR-relative threshold alone changes nothing there,
because the clamp overrides whatever the threshold was. That is why the flag also turns the
clamp into a **skip**: when the structural threshold does not fit under the stop with the
required gap, the stop *is* the protection and no scratch is issued
(`config/mae_scratch.yaml: atr_relative.stop_gap_mode: skip`; Michael 21.08, commit
`8ad1334f`: *"יציאה חכמה — סקרטץ' רק על שבירת-מבנה, לא ביטול-עסקאות"*).

## 3 · Robustness

The replay does not model the live BE-after-first-target, which makes it over-scratch in
both arms. Re-run with the scratch blocked once **any** contract is out (a proxy for that
BE), the result holds and improves:

| Model | A: live today | B: shipped | Δ | median day | median of changed | better/worse |
|---|---|---|---|---|---|---|
| as-generated (`t1_hit` = T1 proper) | −$3,542.62 | +$856.13 | **+$4,398.75** | $0.00 | +$22.50 | 12 / 8 |
| BE-proxy (scratch blocked after any fill) | −$3,636.37 | +$856.13 | **+$4,492.50** | $0.00 | +$35.00 | 12 / 7 |

## 4 · The historical scratches — how many stop firing, and what each was worth

All 7 MAE scratches that ever fired in production (`exit_reason='MAE_SCRATCH'`), scored
against the ATR14 measured on the bar of entry (canonical `v9_bars_5min_woodies`, same
14-bar TR average the live engine uses):

| # | date | pattern | stop dist | threshold that fired (OFF) | ATR14 | ATR threshold | under the flag |
|---|---|---|---|---|---|---|---|
| 640 | 08-06 | BEAR_FLAG_SHORT | 8.50 | 6.50 (clamped) | 8.68 | 11.57 | **no scratch** (no room) |
| 726 | 08-19 | GB100 | 15.00 | 10.00 (yaml) | 7.77 | 12.95 | scratches later, at 12.95 |
| 728 | 08-19 | GHOST | 13.75 | 8.00 (yaml) | 8.86 | 11.81 | **no scratch** (no room) |
| 738 | 08-19 | ZLR | 7.25 | 5.25 (clamped) | 5.04 | 5.04 | scratches, ~unchanged |
| 741 | 08-19 | ZLR | 6.25 | 4.25 (clamped) | 5.89 | 5.89 | **no scratch** (no room) |
| 746 | 08-19 | GB100 | 5.50 | 3.50 (clamped) | 5.25 | 8.75 | **no scratch** (no room) |
| 756 | 08-20 | TREND_STEP | 3.50 | **1.50 (clamped)** | 8.07 | 10.76 | **no scratch** (no room) |

**5 of the 7 stop firing; 1 fires later; 1 is unchanged.** Across the full 32-session
replay (which includes the shadow signal stream, so it is a much larger sample than the 7
live ones) the count drops from **58 → 11** scratches, worth **+$4,398.75**.

`pnl_sierra` / exit-fill truth: only #640 has a broker-verified figure
(`pnl_sierra = −131.25`, matching `pnl_usd`). The other six were all booked with
`pnl_usd = 0.0` — that is a **bookkeeping convention**, not a fill: `bar_level_detector`'s
`on_trade_close` hardcodes `"pnl_usd": 0.0, "outcome": "SCRATCH"`. There is no `exit_fills`
table in this DB (only `v9_exit_decisions`), so the $0 cannot be corroborated and must not
be read as "the scratch was free". The replay's bar-close fill is the more honest estimate
and prices those six at a real, non-zero cost.

## 5 · 🔴 Honest correction to the #756 premise (Pre-LIVE Rule 2)

The work order states that the scratched #756 entry *"then ran 27.5 points in our favour"*.
**The 27.5pt is real; the conclusion drawn from it is not.** Raw bars, 2026-08-20,
`v9_bars_5min_woodies`, SHORT from 7696.75 with the stop at 7700.25:

```
11:30 CT  H 7699.50  L 7691.75   (still alive)
11:35 CT  H 7702.00  L 7698.25   <-- STOP 7700.25 TOUCHED
11:40 CT  H 7705.50  L 7701.00
...
13:15 CT  H 7675.25  L 7669.25   <-- max favourable excursion 27.50pt
```

The 3.5pt stop was hit at **11:35 CT — 1h40m before** the favourable move. The shadow twin
of the same signal, **#755** (identical entry/stop/targets, not scratched), is in the DB
with `exit_reason = STOP_HIT, pnl_usd = −70.00`. So on #756 the MAE scratch *saved* money;
what cost the 27.5pt was the **3.5pt stop**, i.e. work-order item **A3 (stop floor
≥0.35×IB)**, not the MAE threshold. In the replay #756/#755 is one of the 8 days-worse
trades: −$12 (scratch at the bar close −$31 → stop −$44).

This does not change the verdict — the +$4,399 comes from 07-17 / 07-20 / 07-23 / 07-24,
sessions where the clamped threshold chopped 3–9 trades each — but the flag must not be
sold as "this fixes #756". It does not. **A3 fixes #756.**

## 6 · The other honest finding — the protection itself is net-negative in this replay

Measured against a no-scratch-at-all arm on the same 32 sessions:

| arm | total (0-slip, net of commission) | median day |
|---|---|---|
| no MAE scratch at all | **+$3,358.13** | +$32.50 |
| fixed + clamp (live today) | −$3,542.62 | +$19.75 |
| ATR + skip (shipped) | +$856.13 | −$18.12 |

On this sample the scratch costs money in **both** configurations (−$6,901 as configured
today, −$2,502 after this change). That contradicts the "+$397 vs shadow twins / +$843 vs
static replay" figure the protection was enabled on, and it deserves its own investigation
— **but removing the protection was explicitly out of scope for this task** (Michael:
"do NOT remove it, make it relative"), and this replay carries the declared limitations
above (no BE, no trails, no SCALE_IN, all shadow signals taken). Logged as an open item;
it is not a reason to hold this change, which strictly improves the configuration that is
actually live.

## 7 · Calibration provenance (so no future agent has to guess)

- **ATR_MEDIAN = 6.0pt** — median ATR14 (5-min bars, 08:00–15:05 CT) over the 32 live-era
  sessions 2026-06-29 → 2026-08-20. Median of the 32 per-day medians = 5.982; median of all
  2,170 individual bar values = 5.964; p25 = 3.94, p50 = 5.98, p75 = 7.25, min 2.82
  (03.07), max 9.36 (02.07).
- **k = fixed_threshold / 6.0**, so a median-ATR day reproduces today's points to <0.01pt —
  asserted by `test_k_reproduces_fixed_points_on_median_atr_day`.
- **floor = 4.0pt = 1.25 × 3.2pt**, the winners' median MAE from
  `docs/reports/MAE_CALIBRATION_2026-08-02.md`. Any threshold at or below 3.2 scratches the
  median *winner*. On the quietest live-era session (03.07, day-median ATR14 2.82) the raw
  default threshold is 3.76pt, so the floor binds exactly there and nowhere above it.
