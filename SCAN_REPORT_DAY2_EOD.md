# MEMS26 Pre-Phase-3.2 Scan Report
## Day 2 EOD — 1/5/2026 | DLL v7.15.0 | Commit a42d2d0+

---

## 1. Layer-by-Layer Findings

### Layer 1: DLL (v7.15.0)
- **Day classification**: Returns 5 types: TREND_DAY, RANGE_DAY, GAP_FILL, NORMAL, DEVELOPING. **NEUTRAL not present** (only in Vegas/CVD trends).
- **IB tracking**: ib_high, ib_low present. ib_break_held computed as `(breakout_up || breakout_down) && !returned_after_breakout`. **current_tpo_period MISSING** — uses `tpo_letter_minutes: 30` instead.
- **Vegas hysteresis**: 2-bar confirm + distance check via persistent keys 220/221. Working correctly.
- **Trigger IDs**: Unique format `T_<TYPE>_<UNIX>_<COUNTER>` with persistent counter. Confirmed unique.
- **Vegas flips**: RTH-only counting, date reset, capped at 50 (v7.14.2 fix).

### Layer 2: Bridge (V6.7.0)
- **Fields forwarded**: 28 top-level keys in enrich() including vegas, tpo, triggers, day_classification.
- **TPO fallback**: Present — populates VAH/VAL from market_profile when TPO current_day has nulls.
- **Trading hours**: Sun 18:00-Fri 17:00 ET, daily 17:00-18:00 maintenance. Corrected in V8.1.6.
- **Field renames**: current_price→price, cvd.current→total, woodi_pivots→woodi, time_levels→levels.

### Layer 3: Backend
- **53+ endpoints** across market, trade, analytics, quality categories.
- **Quality Score weights** (from day_config.py): 5 day types, all sum to 100.
  - Vegas: 20-40, TPO: 20-35, FVG: 25 (fixed), Footprint: 15-20
- **Flow-Vegas disagreement** (W35): Detects when price position contradicts Vegas trend. Gives partial credit to counter-trend setups when flow aligns.
- **Structural stop shadow**: Computed and stored in extra_json for every new setup.
- **Sequential sim filters**: NORMAL_DAY_SKIP, FOOTPRINT_OPPOSES, OFF_HOURS_BLOCKED, LOW_SCORE (<70), COOLDOWN (300s), OTHER_TRADE_OPEN.
- **Shadow sim**: 60s interval, MAE/MFE computed with 50pt cap, BE-strategy-aware PnL.

### Layer 4: Database
- **Tables**: setups, setup_attempts, setup_observations, trades.
- **4,149 attempts** with outcomes (score buckets computed).
- **Direction balance**: LONG 55% / SHORT 45% (improved from 98% LONG pre-W35).
- **Day type distribution**: NORMAL 43%, DEVELOPING 42%, UNKNOWN 8%, RANGE 4%, TREND 2%, GAP_FILL <1%.
- **Sequential today**: 4 executed, 238 skipped, WR 75%, PnL +$150.

### Layer 5: Frontend
- **24 components** in /components/.
- **Trade tab order**: ShadowTradesTodayCard → TradeStatusRow → DayTypeHero → QualityScorePanel → StrategyPreview → TriggerPanel → VegasTunnelPanel → SetupsTable → AttemptsTable.
- **Journal**: REAL/SHADOW tabs, KPIs from API summaries, filters+sort all working.
- **Missing panels**: Playbook, IB Tracker, Auto-Execute, Failsafe — none exist as files.
- **Unused components** (9): CVDPanel, DailyTracker, LevelsBadges, ReversalStatus, SignalCard, TradingChart, TrafficLight, chartpanel, VersionModal (conditional).

---

## 2. Gap Analysis vs 5 Day-Type Spec

### TREND_DAY
| Layer | Needed | Status |
|-------|--------|--------|
| DLL | Classification + confidence | Present (0.85 conf) |
| Backend | Vegas=40, c2_R=3.0, BE=after_c2+0.5R | All configured |
| Backend | Counter-trend hard reject | NOT PRESENT (only score weighting) |
| Frontend | Playbook panel showing "Ride the trend, wider targets" | NOT PRESENT |

### RANGE_DAY
| Layer | Needed | Status |
|-------|--------|--------|
| DLL | Classification + confidence | Present (0.75 conf) |
| Backend | TPO=35 weight, c2_R=1.5, C3 disabled, BE=on_c1 | All configured |
| Backend | Mean-reversion entry filter | NOT PRESENT |
| Frontend | Playbook showing "Fade extremes, tight targets" | NOT PRESENT |

### GAP_FILL
| Layer | Needed | Status |
|-------|--------|--------|
| DLL | Classification + confidence | Present (0.70 conf) |
| Backend | c2_special=PDC, C3 disabled, BE=on_c1 | All configured |
| Backend | Gap direction awareness | PARTIAL (PDC fallback works) |
| Frontend | Gap visualization on chart | NOT PRESENT |

### DEVELOPING (< 60 min session)
| Layer | Needed | Status |
|-------|--------|--------|
| DLL | Default before classification | Present (sesMin < 60) |
| Backend | Same as NORMAL weights | Configured |
| Frontend | "Developing — wait for IB close" indicator | PARTIAL (DayTypeHero shows type) |

### NEUTRAL (new — requested in spec)
| Layer | Needed | Status |
|-------|--------|--------|
| DLL | Classification logic | NOT PRESENT (no NEUTRAL in day_class) |
| Backend | Weights, targets, BE config | NOT PRESENT in day_config.py |
| Frontend | Display | NOT PRESENT |

---

## 3. Data Quality Snapshot

### Score Bucket Performance (4,149 attempts with outcomes)
| Bucket | n | WR | Avg MFE | Avg MAE |
|--------|---|---|---------|---------|
| <30 | 95 | 31.6% | 5.49 | 12.08 |
| 30-49 | 1,386 | 44.2% | 11.86 | 8.49 |
| 50-69 | 1,324 | 35.5% | 11.12 | 11.98 |
| 70+ | 1,344 | 34.6% | 8.84 | 11.36 |

**Anti-correlation persists**: 30-49 bucket (44.2% WR) > 70+ bucket (34.6% WR). W35 flow-disagree helped but didn't fully resolve.

### Direction Balance
- LONG: 2,190 (55%), SHORT: 1,795 (45%)
- **Improved** from 98% LONG (pre-W35) to 55/45 split.

### Day Type Distribution
| Day Type | n | WR | Avg MFE | Avg MAE |
|----------|---|---|---------|---------|
| NORMAL | 1,707 | 40.3% | 7.21 | 7.21 |
| DEVELOPING | 1,678 | 37.6% | 13.39 | 13.18 |
| TREND_DAY | 92 | **52.2%** | 11.44 | 10.10 |
| RANGE_DAY | 179 | 40.8% | 12.68 | 12.66 |
| UNKNOWN | 327 | 41.9% | 9.65 | 12.30 |

### Killzone Performance
| Killzone | n | WR | Note |
|----------|---|---|------|
| NY_Close | 116 | **50.0%** | Best WR |
| UNKNOWN | 810 | 48.0% | Pre-killzone-fix data |
| OFF_HOURS | 2,685 | 38.1% | Blocked in sequential sim |
| NY_Open | 124 | 33.9% | Worst active KZ |
| London | 250 | 26.4% | Very poor |

### Sequential Sim Today (1/5)
- Executed: 4, Closed: 4, WR: 75%, PnL: +$150
- Skip distribution: OFF_HOURS 117, NORMAL_DAY 52, LOW_SCORE 30, FOOTPRINT_OPPOSES 24, COOLDOWN 12

### Strategic Tags Completeness
- Based on recent setups: rel_vol, cvd_direction, mtf_aligned, vwap_side, minutes_into_session — **all populated since W20 (30/4)**.
- Historical pre-W20 data: these fields are NULL.
- extra_json (shadow_structural_stop): populated since W30a, backfilled on resimulate.

---

## 4. Risks Going Into Phase 3.2

### Known Bugs
1. **MAE outliers**: Shadow sim occasionally produces 600+ pt MAE values. Capped at 50pt in V8.2.7o but root cause not fixed (sim reads bars outside trade window).
2. **GAP_FILL**: Only 2 observations total — insufficient data for any conclusion. Classification may trigger incorrectly.
3. **London killzone WR 26.4%**: Concerning — may indicate London setups are systematically worse, or timing/volatility issue.

### Data Gaps
1. **TREND_DAY sample size**: Only 92 setups (2.3%). Need more for statistical significance. Could take 2-3 weeks.
2. **C3 target**: Always NULL — c3_enabled=True but no price computed. Cannot evaluate runner strategy.
3. **minutes_into_session**: NULL for pre-RTH setups (-1 from DLL cast to None). ~50% of setups affected.

### DLL/Bridge State
- Bridge version V6.7.0 label is stale (actual code is much newer). No functional impact.
- DLL v7.15.0 includes all fixes through W37.

---

## 5. Prioritized V2 Fixes

### Critical for 5-Day-Type Spec (Phase 3.3 must-have)
1. **Vegas scoring direction-agnostic** — Score tunnel width, not trend match. Root cause of anti-correlation. (quality_score.py)
2. **NEUTRAL day type** — Add to DLL classification + day_config.py. Currently only 4+DEVELOPING types.
3. **Counter-trend rejection for TREND_DAY** — If day=TREND_DAY and setup direction opposes trend, hard reject (not just lower score).
4. **C3 target price computation** — Currently c3_enabled=True but no price. Need trailing logic or fixed 3R.

### Important for Clean Data (Phase 3.2 should-have)
5. **MAE root cause** — Fix shadow sim bar window filtering (not just cap at 50pt).
6. **London killzone investigation** — Is 26.4% WR real or data artifact? Consider excluding from sequential sim.
7. **Structural stop comparison** — Shadow structural stop is recorded but no analysis pipeline exists yet.

### Nice-to-Have (Sprint 7+)
8. **IB Tracker panel** — Frontend display of IB levels, break direction, held status.
9. **Day Type Playbook panel** — Per-type strategy guidance in dashboard.
10. **Unused component cleanup** — Remove 9 dead components (CVDPanel, etc.).
11. **Auto-Execute control panel** — For Sprint 7 implementation.
12. **Bridge version alignment** — V6.7.0 label → match actual version.
