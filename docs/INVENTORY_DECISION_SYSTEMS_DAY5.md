# MEMS26 Decision Systems Inventory — Day 5

**Generated:** 2026-05-07T12:00:00Z
**Branch:** feature/inventory-day5
**Commit at scan:** 9bdcd34059d338bd2dbd25cfd08b66e07418658c
**Repo LOC:** backend=7,171, frontend=11,405, DLL=2,195, bridge=5,110, tools=1,203

---

## 0. Repo Top-Level Structure

```
.
./analysis
./backend
./backend/engine
./backend/tests
./bridge
./docs
./frontend
./frontend/public
./frontend/src
./frontend/src/app
./frontend/src/components
./frontend/src/utils
./sc_study
./scripts
./tools
./tools/backtest
./tools/backtest/output
./tools/preflight
```

---

## 1. Decision Systems Catalog

### 1.1 — Quality Score (V1, Day-Adaptive)

- **Layer:** backend
- **Files:**
    - `backend/quality_score.py:11-204` (main scoring logic)
    - `backend/day_config.py:5-11` (weight tables)
    - `backend/day_config.py:13-19` (size threshold tables)
- **Purpose:** Computes a 0-100 quality score for a setup based on 4 components: Vegas tunnel alignment, TPO position, FVG matches, Footprint delta/imbalance. Weights vary by day type.
- **Inputs:** `market_data` dict (vegas, tpo, triggers, footprint_bools, price), `direction` (LONG/SHORT), `day_type`
- **Outputs:** `{total: int 0-100, breakdown: {vegas, tpo, fvg, footprint}, reasons: list[str], day_type_used, weights_applied}`
- **Invocation:** per-trigger (via `/quality/preview` POST endpoint, and inline during setup attempt logging in `_sequential_sim_loop`)
- **In production?** YES (always)
  → Evidence: Called from `backend/main.py:991` in `/quality/preview` route, and from `main.py:1043` in setup attempt scoring pipeline
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-01 michaelbarg feat(shadow): W38 — multi-source structural stops with priority + quality
- **Code excerpt (core scoring — Vegas component with flow override):**
```python
    if flow_disagree == "STRONG_DISAGREE":
        if direction_matches_flow:
            pts = int(max_vegas * 0.5)  # +15 for flow alignment
            breakdown["vegas"] = pts
        else:
            breakdown["vegas"] = 0
    elif trend_matches:
        if vwidth >= 0.5:
            breakdown["vegas"] = max_vegas
        elif vwidth >= 0.2:
            pts = int(max_vegas * 0.75)
            breakdown["vegas"] = pts
```

---

### 1.2 — Day-Adaptive Configuration

- **Layer:** backend
- **Files:**
    - `backend/day_config.py:1-61` (full file)
- **Purpose:** Central lookup tables for per-day-type weights, size thresholds, target R-multiples, and breakeven rules. Single source of truth for day-adaptive behavior.
- **Inputs:** `day_type` string (TREND_DAY, RANGE_DAY, GAP_FILL, NORMAL, DEVELOPING)
- **Outputs:** `{day_type, weights, thresholds, targets, be_rule, vegas_min_width}`
- **Invocation:** per-call (via `get_config()` from quality_score.py and main.py)
- **In production?** YES (always)
  → Evidence: Imported by `quality_score.py:8` — every quality score calculation uses it
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-04-29 michaelbarg feat(backend): Day-Adaptive Configuration module (Phase 5 Task 1)
- **Code excerpt (weight and threshold tables):**
```python
QUALITY_WEIGHTS = {
    "TREND_DAY": {"vegas": 40, "tpo": 20, "fvg": 25, "footprint": 15},
    "RANGE_DAY": {"vegas": 20, "tpo": 35, "fvg": 25, "footprint": 20},
    "NORMAL":    {"vegas": 30, "tpo": 25, "fvg": 25, "footprint": 20},
}
SIZE_THRESHOLDS = {
    "TREND_DAY": {"full": 60, "half": 45},
    "RANGE_DAY": {"full": 70, "half": 55},
    "NORMAL":    {"full": 70, "half": 50},
}
```

---

### 1.3 — Position Sizing (Tiered)

- **Layer:** backend
- **Files:**
    - `backend/quality_score.py:207-229` (function `determine_position_size`)
    - `backend/main.py:439` (shadow sim inline sizing: `contracts = 3 if score >= 70 else 2 if score >= 50 else 1`)
- **Purpose:** Maps quality score to number of contracts (0/2/3). Day-adaptive: thresholds differ per day type. In DEMO mode, low scores get a WARN instead of REJECT.
- **Inputs:** `score` (int 0-100), `mode` (DEMO/STRICT), `day_type`
- **Outputs:** `{qty: 0|2|3, exits: list, action: str, reject/warn: bool, thresholds_used}`
- **Invocation:** per-trigger (in `/quality/preview` response pipeline)
- **In production?** YES (always)
  → Evidence: Called from `backend/main.py:996`
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-01 (via quality_score.py)
- **Code excerpt:**
```python
def determine_position_size(score, mode, day_type=None):
    config = get_config(day_type)
    thresholds = config["thresholds"]
    if score >= thresholds["full"]:
        return {"qty": 3, "exits": ["C1", "C2", "C3"], "action": "FULL_SIZE"}
    elif score >= thresholds["half"]:
        return {"qty": 2, "exits": ["C1", "C2"], "action": "HALF_SIZE"}
```

**DUPLICATE NOTE:** `backend/main.py:439` has an independent inline sizing: `contracts = 3 if score >= 70 else 2 if score >= 50 else 1` which does NOT use day-adaptive thresholds. See §3.1.

---

### 1.4 — 3-Pillar Gate (Range Mode)

- **Layer:** bridge
- **Files:**
    - `bridge/shadow_trader.py:640-694` (function `_eval_range`)
- **Purpose:** Evaluates whether a setup passes 3 structural pillars for range/normal day types. All 3 must pass or setup is rejected.
  - P1 (ZONE): Must be a sweep at a macro level (PDH/PDL/ONH/ONL/IBH/IBL/VWAP/POC/VAH/VAL/SH/SL) with wick >= 1.5pt
  - P2 (PATTERN): MSS + FVG + RelVol > 1.2 + Stacked imbalance >= 2
  - P3 (FLOW): Absorption at FVG + delta confirmed on 1m
- **Inputs:** `hit` (sweep/rejection data), `direction`, `market_data`, `candles`, footprint bools, order flow
- **Outputs:** `{pass: bool, reason: str, eval_type: "range"}`
- **Invocation:** per-setup-hit (from `evaluate_setup` loop in shadow engine)
- **In production?** YES (always)
  → Evidence: Called from `bridge/shadow_trader.py:252` — Gate 3 in ordered gate logic, marked "NEVER loosened"
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-04-20 michaelbarg feat(v6.5.2): ordered gate logic with DEMO/STRICT mode support
- **Code excerpt (P1 zone check):**
```python
def _eval_range(self, hit, direction, market_data, candles, fp, of2, price):
    macro = ["PDH", "PDL", "ONH", "ONL", "IBH", "IBL", "VWAP", "POC", "VAH", "VAL", "SH", "SL"]
    if hit["type"] != "sweep":
        return {"pass": False, "reason": f"P1: Range requires sweep (not {hit['type']})"}
    if sweep_wick < 1.5:
        return {"pass": False, "reason": f"P1: Sweep wick {sweep_wick:.1f}pt < 1.5pt"}
    if hit["levelName"] not in macro:
        return {"pass": False, "reason": "P1: Middle of Nowhere"}
```

---

### 1.5 — 3-Pillar Gate (Trend Mode)

- **Layer:** bridge
- **Files:**
    - `bridge/shadow_trader.py:696-741` (function `_eval_trend`)
- **Purpose:** Evaluates 3 pillars for trend day setups (different criteria than range):
  - P1 (ZONE): Pullback to VWAP (within 3pt) or FVG pullback
  - P2 (PATTERN): Continuation MSS + FVG + RelVol > 1.2
  - P3 (FLOW): Declining delta (absolute values decreasing) + delta confirmed 1m
- **Inputs:** Same as 1.4 but includes `vwap` data
- **Outputs:** `{pass: bool, reason: str, eval_type: "trend"}`
- **Invocation:** per-setup-hit (when `day_type in ("TREND", "TREND_DAY")`)
- **In production?** YES (always)
  → Evidence: Called from `bridge/shadow_trader.py:637` — `if is_trend: return self._eval_trend(...)`
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-04-20
- **Code excerpt (P3 declining delta):**
```python
recent5 = candles[:5]
if len(recent5) >= 3:
    deltas = [abs(c.get("delta", 0) or 0) for c in recent5]
    if not (deltas[0] < deltas[1] or deltas[1] < deltas[2]):
        return {"pass": False, "reason": "P3: Delta not declining"}
```

---

### 1.6 — Day Type Classifier (DLL)

- **Layer:** DLL (sc_study)
- **Files:**
    - `sc_study/MES_AI_DataExport.cpp:824-881` (day type classification block)
- **Purpose:** Classifies the current trading day into one of 5 types based on IB range, Vegas flips, ATR, gap, and extension. Only activates after 60 minutes into session with IB locked.
- **Inputs:** `sesMin` (minutes into session), `ib_locked`, `vegas_flips`, `ib_break_held`, `atr_base`, `day_range`, `gap`, `daily_open`, `cp` (current price)
- **Outputs:** `day_class` string: DEVELOPING (default), TREND_DAY, RANGE_DAY, GAP_FILL, NORMAL. Plus `day_class_conf` (0.0-0.85)
- **Invocation:** per-bar (Sierra Chart AutoLoop, ~every 3s)
- **In production?** YES (always)
  → Evidence: Written to `mes_ai_data.json` as `day_classification.type`, consumed by bridge and backend
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-01 michaelbarg fix(dll): V7.15.0 — version bump + TPO VAH/VAL diagnostic logging
- **Code excerpt:**
```cpp
if (sesMin >= 60 && ib_locked) {
    if (vegas_flips <= 2 && ib_break_held && atr_base > 0 && day_range > atr_base * 0.7f)
        day_class = "TREND_DAY"; day_class_conf = 0.85f;
    else if (vegas_flips >= 4 && atr_base > 0 && day_range < atr_base * 0.5f)
        day_class = "RANGE_DAY"; day_class_conf = 0.75f;
    else if (fabs(gap) > 5.0f && ((gap > 0 && cp < daily_open) || (gap < 0 && cp > daily_open)))
        day_class = "GAP_FILL"; day_class_conf = 0.70f;
    else
        day_class = "NORMAL"; day_class_conf = 0.50f;
}
```

---

### 1.7 — Killzone Classifier

- **Layer:** bridge
- **Files:**
    - `bridge/shadow_trader.py:122-130` (function `_get_killzone`)
    - `bridge/config.py:109-114` (KILLZONES dict)
    - `frontend/src/components/PreEntryChecklist.tsx:43-55` (frontend duplicate `inKillzone`)
    - `frontend/src/components/AwaitingTriggerPanel.tsx:26-49` (`getKillzoneStatus`)
    - `backend/analytics.py:139-146` (analytics killzone assignment)
- **Purpose:** Determines if current time is within a trading killzone: London (03:00-05:00 ET), NY_Open (09:30-10:30 ET), NY_Close (15:00-16:00 ET), or OUTSIDE.
- **Inputs:** Current time (ET)
- **Outputs:** Killzone name string: "LONDON", "NY_OPEN", "NY_CLOSE", "OUTSIDE"
- **Invocation:** per-setup-evaluation + per-trade (for tagging)
- **In production?** YES (always) — but enforcement varies by ENTRY_MODE
  → Evidence: Called from `shadow_trader.py:224` in evaluate_setup. In STRICT mode (line 314-319), OUTSIDE killzone blocks the trade. In DEMO mode, it's tag-only.
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-04-20 (shadow_trader.py)
- **Code excerpt:**
```python
KILLZONES = {
    "LONDON":   ("03:00", "05:00"),
    "NY_OPEN":  ("09:30", "10:30"),
    "NY_CLOSE": ("15:00", "16:00"),
}
def _get_killzone(self) -> str:
    now = datetime.now(ET)
    et_min = now.hour * 60 + now.minute
    for name, (start_s, end_s) in KILLZONES.items():
        sh, sm = map(int, start_s.split(":"))
        eh, em = map(int, end_s.split(":"))
        if sh * 60 + sm <= et_min < eh * 60 + em:
            return name
    return "OUTSIDE"
```

---

### 1.8 — Ordered Gate Logic (Shadow Engine)

- **Layer:** bridge
- **Files:**
    - `bridge/shadow_trader.py:223-357` (gates 1-11 in `evaluate_setup`)
- **Purpose:** Sequential gate system that filters setup hits through 11 ordered checks. Hard gates (1, 3, 4) are NEVER loosened. Soft gates (8-11) only enforce in STRICT mode.
- **Gates:**
  1. Pre-Close Freeze (15:30 ET) — NEVER loosened
  2. News Freeze — NEVER loosened
  3. 3-Pillar evaluation — NEVER loosened
  4. Stop validation (3-8pt range) — NEVER loosened
  5. RelVol >= min (1.0 in DEMO, 1.2 in STRICT)
  6. FVG size <= max (5.0pt in DEMO, 4.0pt in STRICT)
  7. Sweep wick >= min (1.0pt in DEMO, 1.5pt in STRICT)
  8. News check (STRICT only)
  9. Killzone required (STRICT only)
  10. Max trades/day (STRICT only, cap=3)
  11. Circuit Breaker (STRICT only)
- **Inputs:** All market data, hit info, current CB state, news state
- **Outputs:** Either continues to trade creation or logs rejection with reason
- **Invocation:** per-setup-hit
- **In production?** YES (always)
  → Evidence: This IS the main entry pipeline for shadow trades
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-04-20
- **Code excerpt (gate flow):**
```python
# Gate 1: Pre-Close Freeze (NEVER loosened)
if is_pre_close:
    await self._log_attempt(hit, direction, {"pass": False, "reason": "PRE_CLOSE_FREEZE"}, ...)
    continue
# Gate 3: 3-Pillar evaluation (NEVER loosened)
eval_result = self._evaluate_pillars(hit, direction.lower(), market_data, ...)
if not eval_result["pass"]:
    await self._log_attempt(hit, direction, eval_result, ...)
    continue
# Gate 5: RelVol >= config minimum
if hit.get("relVol", 0) < RELVOL_MIN:
    ...
```

---

### 1.9 — Circuit Breaker

- **Layer:** backend + bridge
- **Files:**
    - `backend/main.py:2484-2540` (CB constants + `check_circuit_breaker` function)
    - `backend/main.py:2970-2990` (CB trigger logic in trade close)
    - `bridge/config.py:74-79` (bridge-side CB constants)
- **Purpose:** Prevents further trading when daily loss or consecutive losses exceed thresholds. Three trigger conditions:
  1. Hard lock: daily P&L loss >= $200 → locked until next day
  2. Soft lock: daily P&L loss >= $150 (SIM) / $100 (LIVE) → locked 30 min
  3. Consecutive losses >= 2 → locked 30 min
  4. Max trades/day: 3 (STRICT) / 999 (DEMO)
- **Inputs:** Daily state from Redis: pnl, trade_count, consecutive_losses, locked_until, hard_locked
- **Outputs:** `{allowed: bool, reason: str, lock_minutes: int}`
- **Invocation:** per-trade-attempt (checked before execution) + per-trade-close (updates state)
- **In production?** YES (always)
  → Evidence: Called from `main.py:2551` (GET /trade/circuit-breaker) and checked in `/trade/execute` flow
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-01 (main.py)
- **Code excerpt:**
```python
CB_SOFT_LIMIT  = 150 if _MODE == "SIM" else 100
CB_HARD_LIMIT  = 200
CB_MAX_TRADES  = 3
CB_CONSEC_LOSSES = 2
CB_LOCK_MIN    = 30

if abs(state["pnl"]) >= CB_HARD_LIMIT and state["pnl"] < 0:
    state["hard_locked"] = True
elif abs(state["pnl"]) >= CB_SOFT_LIMIT and state["pnl"] < 0:
    state["locked_until"] = time.time() + CB_LOCK_MIN * 60
elif state["consecutive_losses"] >= CB_CONSEC_LOSSES:
    state["locked_until"] = time.time() + CB_LOCK_MIN * 60
```

---

### 1.10 — Cooldown Logic (Bridge)

- **Layer:** bridge
- **Files:**
    - `bridge/shadow_trader.py:110` (cooldown dict)
    - `bridge/shadow_trader.py:204-208` (cooldown check)
    - `bridge/shadow_trader.py:338` (cooldown set)
- **Purpose:** Prevents re-entering the same level within 5 minutes (300 seconds). Per-level, per-direction.
- **Inputs:** `direction + level_name` composite key, current timestamp
- **Outputs:** Boolean (skip or continue)
- **Invocation:** per-setup-hit evaluation
- **In production?** YES (always)
  → Evidence: Executed at `shadow_trader.py:204-208` before gate logic
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-04-20
- **Code excerpt:**
```python
cooldown_key = f"{direction}_{hit['levelName']}"
if cooldown_key in self._cooldown_setups:
    if now - self._cooldown_setups[cooldown_key] < 300:
        continue
```

---

### 1.11 — Cooldown Logic (Backend Sequential Sim)

- **Layer:** backend
- **Files:**
    - `backend/main.py:670-674` (cooldown in `_sequential_sim_loop`)
- **Purpose:** In the sequential simulator, prevents executing a new setup if detected within 300 seconds of the previous trade's close.
- **Inputs:** `detected` timestamp, `last_close_ts`
- **Outputs:** `sim_skip_reason = "COOLDOWN"` or continue
- **Invocation:** per-setup in daily sequential scan (every 5 minutes)
- **In production?** YES (always)
  → Evidence: Part of `_sequential_sim_loop` which runs as background task
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-01
- **Code excerpt:**
```python
if detected - last_close_ts < 300 and last_close_ts > 0:
    if not was_exec:
        await update_setup_simulation(sid, {"sim_skip_reason": "COOLDOWN"})
    continue
```

---

### 1.12 — NORMAL Day Type Skip Filter

- **Layer:** backend
- **Files:**
    - `backend/main.py:17` (flag: `SKIP_NORMAL_DAY_TYPE`)
    - `backend/main.py:636-641` (in `_sequential_sim_loop`)
    - `backend/main.py:1084` (in quality preview attempt logging)
- **Purpose:** Skips all setups classified as NORMAL day type. Driven by analysis showing NORMAL days have inverted score-WR correlation (high scores lose, low scores win).
- **Inputs:** `day_type` field on setup, env var `SKIP_NORMAL_DAY_TYPE`
- **Outputs:** `sim_skip_reason = "NORMAL_DAY_SKIP"`
- **Invocation:** per-setup in sequential sim + per-attempt in quality preview
- **In production?** YES (default=true)
  → Evidence: `os.getenv("SKIP_NORMAL_DAY_TYPE", "true")` — on by default
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-01
- **Code excerpt:**
```python
SKIP_NORMAL_DAY_TYPE = os.getenv("SKIP_NORMAL_DAY_TYPE", "true").lower() == "true"
# ...
if SKIP_NORMAL_DAY_TYPE and s.get("day_type") == "NORMAL":
    await update_setup_simulation(sid, {"sim_skip_reason": "NORMAL_DAY_SKIP"})
    continue
```

---

### 1.13 — Footprint Opposes Direction Filter (Confluence Filter)

- **Layer:** backend
- **Files:**
    - `backend/main.py:787-797` (function `footprint_opposes_direction`)
    - `backend/main.py:642-648` (in `_sequential_sim_loop`)
    - `backend/main.py:1086-1095` (in quality preview attempt logging)
- **Purpose:** Blocks setups where footprint delta strongly opposes trade direction. LONG with delta < -500 = selling pressure → skip. SHORT with delta > +500 = buying pressure → skip.
- **Inputs:** `direction`, `footprint_delta` (extracted from score_reasons), env vars `CONFLUENCE_FILTER_ENABLED` (default true), `FOOTPRINT_OPPOSES_THRESHOLD` (default 500)
- **Outputs:** Boolean / `sim_skip_reason = "FOOTPRINT_OPPOSES"`
- **Invocation:** per-setup in sequential sim + per-attempt
- **In production?** YES (default=true)
  → Evidence: `os.getenv("CONFLUENCE_FILTER_ENABLED", "true")`
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-01
- **Code excerpt:**
```python
def footprint_opposes_direction(direction, footprint_delta):
    if not CONFLUENCE_FILTER_ENABLED or footprint_delta is None:
        return False
    if direction == "LONG" and footprint_delta < -FOOTPRINT_OPPOSES_THRESHOLD:
        return True
    if direction == "SHORT" and footprint_delta > FOOTPRINT_OPPOSES_THRESHOLD:
        return True
    return False
```

---

### 1.14 — Vegas Direction Filter (Trade Execute Gate)

- **Layer:** backend
- **Files:**
    - `backend/main.py:808-835` (function `validate_setup_against_vegas`)
    - `backend/main.py:2670-2707` (invocation in `/trade/execute`)
- **Purpose:** Blocks trade execution if setup direction conflicts with Vegas tunnel trend. LONG requires BULLISH, SHORT requires BEARISH. NEUTRAL = blocked. Fail-closed (no Vegas data = blocked).
- **Inputs:** setup direction, Vegas data from Redis (trend field)
- **Outputs:** Boolean — True = allowed, False = HTTP 400 rejection
- **Invocation:** per-trade-execution (only in `/trade/execute` endpoint)
- **In production?** YES (always, in `/trade/execute` flow)
  → Evidence: Called at `main.py:2680` — gating real trade execution
- **Linked decision:** UNTRACKED — partially redundant with Vegas scoring in Quality Score (see §3.2)
- **Last modified:** 2026-05-01
- **Code excerpt:**
```python
def validate_setup_against_vegas(setup, vegas):
    trend = vegas.get("trend")
    if trend == "NEUTRAL":
        return False
    direction = setup.get("direction", "").upper()
    if direction == "LONG" and trend != "BULLISH":
        return False
    if direction == "SHORT" and trend != "BEARISH":
        return False
    return True
```

---

### 1.15 — Flow-Vegas Disagreement Detection

- **Layer:** backend
- **Files:**
    - `backend/quality_score.py:28-59` (within `calculate_quality_score`)
- **Purpose:** Detects when Vegas tunnel trend disagrees with actual market flow (price position + footprint delta). Overrides normal Vegas scoring: if flow strongly disagrees with Vegas, setups aligned with real flow get 50% Vegas credit instead of 0.
- **Inputs:** Vegas trend/position, footprint delta from triggers
- **Outputs:** Modified Vegas score component (0 or max_vegas*0.25 or max_vegas*0.5)
- **Invocation:** per-quality-score-calculation
- **In production?** YES (always)
  → Evidence: Inline in `calculate_quality_score` function, commit a60e3ca (W35)
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-01
- **Code excerpt:**
```python
if vtrend == "BULLISH" and vpos == "BELOW" and fp_delta < -200:
    flow_disagree = "STRONG_DISAGREE"
elif vtrend == "BEARISH" and vpos == "ABOVE" and fp_delta > 200:
    flow_disagree = "STRONG_DISAGREE"
# ...
if flow_disagree == "STRONG_DISAGREE":
    if direction_matches_flow:
        pts = int(max_vegas * 0.5)  # +15 for flow alignment
```

---

### 1.16 — Target Calculation (Day-Adaptive)

- **Layer:** backend
- **Files:**
    - `backend/quality_score.py:232-304` (function `calculate_targets`)
    - `backend/day_config.py:21-27` (TARGET_RULES tables)
- **Purpose:** Computes C1/C2/C3 target prices based on day type. C1 uses R-based distance, C2 has special logic (PDC for GAP_FILL, TPO confluence for NORMAL/DEVELOPING), C3 enabled/disabled per day type. C2 capped at 4R (6R for GAP_FILL).
- **Inputs:** entry, stop, direction, market_data, day_type
- **Outputs:** `{c1, c2, c3_enabled, R, c2_method, day_type_used}`
- **Invocation:** per-quality-preview request
- **In production?** YES (always)
  → Evidence: Called from `main.py:997`
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-01
- **Code excerpt:**
```python
TARGET_RULES = {
    "TREND_DAY": {"c1_R": 1.0, "c2_R": 3.0, "c3_enabled": True,  "c2_special": None},
    "RANGE_DAY": {"c1_R": 0.8, "c2_R": 1.5, "c3_enabled": False, "c2_special": None},
    "GAP_FILL":  {"c1_R": 1.0, "c2_R": 2.0, "c3_enabled": False, "c2_special": "PDC"},
}
```

---

### 1.17 — Breakeven Strategy (Day-Adaptive)

- **Layer:** backend
- **Files:**
    - `backend/quality_score.py:307-310` (function `get_be_strategy`)
    - `backend/day_config.py:29-35` (BE_RULES table)
- **Purpose:** Returns the breakeven timing rule per day type. E.g., TREND_DAY = move stop to BE after C2 fill + half R; RANGE_DAY = move to BE on C1 fill.
- **Inputs:** `day_type`
- **Outputs:** BE strategy string (e.g., "after_c2_plus_half_R", "on_c1_fill", "on_c2_fill")
- **Invocation:** per-quality-preview
- **In production?** YES (returned in API response)
  → Evidence: Called from `main.py:998`
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-04-29
- **Code excerpt:**
```python
BE_RULES = {
    "TREND_DAY": "after_c2_plus_half_R",
    "RANGE_DAY": "on_c1_fill",
    "GAP_FILL":  "on_c1_fill",
    "NORMAL":    "on_c2_fill",
}
```

---

### 1.18 — Structural Stop Calculator

- **Layer:** backend
- **Files:**
    - `backend/quality_score.py:313-392` (function `compute_structural_stop_shadow`)
- **Purpose:** Multi-source stop placement using 6 priority-ordered sources. Returns FIRST valid stop in 3-15pt range. Sources: trigger_FVG, trigger_SWEEP, swing_5bar, swing_10bar, swing_20bar, fallback_atr.
- **Inputs:** direction, entry, triggers list, recent candles, ATR_14, buffer (default 1.0)
- **Outputs:** `{structural_stop_price, structural_stop_pts, structural_stop_source, structural_stop_valid, structural_stop_quality}`
- **Invocation:** per-setup-attempt (called in quality preview pipeline for shadow logging)
- **In production?** YES (shadow mode — logged, not executed)
  → Evidence: Called from `main.py:1136` and `main.py:1181`
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-01 (W38)
- **Code excerpt:**
```python
sources = []
# 1. trigger_FVG — deepest FVG matching direction
# 2. trigger_SWEEP — swept level
# 3-5. recent_swing at 5/10/20 bar windows
# 6. fallback_atr
for src_name, anchor in sources:
    stop_price = round(anchor - sign * buffer, 2)
    stop_pts = round(abs(entry - stop_price), 2)
    if MIN_PT <= stop_pts <= MAX_PT:
        return {..., "structural_stop_valid": True}
```

---

### 1.19 — News Guard

- **Layer:** bridge
- **Files:**
    - `bridge/news_guard.py:1-100+` (class `NewsGuard`)
    - `bridge/config.py:116-119` (NEWS_* constants)
- **Purpose:** Fetches USD high-impact economic events from ForexFactory. State machine: CLEAR → PRE_NEWS_FREEZE (10min before event) → POST_NEWS_OPPORTUNITY (3min after) → CLEAR. Blocks all entries during freeze.
- **Inputs:** ForexFactory JSON calendar, current time
- **Outputs:** State: CLEAR / PRE_NEWS_FREEZE / POST_NEWS_OPPORTUNITY / NEWS_ACTIVE
- **Invocation:** continuous (checked every tick in shadow engine + checked in gate 2/8)
- **In production?** YES (always — "NEVER loosened" even in DEMO)
  → Evidence: `bridge/config.py:41` `NEWS_GUARD_HARD = True` in DEMO mode
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-04-17
- **Code excerpt:**
```python
STATE_CLEAR       = "CLEAR"
STATE_PRE_FREEZE  = "PRE_NEWS_FREEZE"
STATE_POST_OPP    = "POST_NEWS_OPPORTUNITY"
# news freeze check in gate logic:
if ns in ("PRE_NEWS_FREEZE", "NEWS_ACTIVE"):
    await self._log_attempt(hit, direction, {"pass": False, "reason": "NEWS_FREEZE"}, ...)
```

---

### 1.20 — Pre-Close Freeze

- **Layer:** bridge
- **Files:**
    - `bridge/config.py:63-65` (PRE_CLOSE_FREEZE_TIME_ET, PRE_CLOSE_FREEZE_ENABLED)
    - `bridge/shadow_trader.py:227-247` (Gate 1 check)
- **Purpose:** Blocks all new entries after 15:30 ET. "NEVER loosened" — active in all modes including DEMO.
- **Inputs:** Current time (ET), `PRE_CLOSE_FREEZE_TIME_ET` config
- **Outputs:** Gate rejection: "PRE_CLOSE_FREEZE"
- **Invocation:** per-setup-hit (Gate 1 in ordered gates)
- **In production?** YES (always)
  → Evidence: `PRE_CLOSE_FREEZE_ENABLED = True` at `config.py:65`
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-04-20

---

### 1.21 — EOD Flatten

- **Layer:** bridge
- **Files:**
    - `bridge/config.py:94-96` (EOD_FLATTEN_TIME, EOD_FLATTEN_ENABLED)
    - `bridge/shadow_trader.py:395-399` (function `eod_flatten`)
- **Purpose:** Auto-closes all open shadow trades at 15:59 ET (1 minute before CME maintenance).
- **Inputs:** Current time vs EOD_FLATTEN_TIME
- **Outputs:** All open shadows closed with reason "EOD_FLATTEN"
- **Invocation:** called from bridge main loop at EOD
- **In production?** YES (always)
  → Evidence: `EOD_FLATTEN_ENABLED = True`
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-04-20

---

### 1.22 — Sequential Simulator (What-Would-Execute-Live)

- **Layer:** backend
- **Files:**
    - `backend/main.py:602-687` (function `_sequential_sim_loop`)
- **Purpose:** Every 5 minutes, scans today's setups and determines which ones would execute in a one-at-a-time LIVE scenario. Applies: NORMAL day skip, footprint opposition, killzone filter (STRICT only), score >= 70 threshold, one-trade-at-a-time, cooldown (300s). Writes `executed_in_sim` flag and `sim_skip_reason`.
- **Inputs:** All today's setups from Postgres, sorted by detection time
- **Outputs:** Per-setup: `executed_in_sim: True/False`, `sim_skip_reason: str`
- **Invocation:** background loop (every 300 seconds)
- **In production?** YES (always)
  → Evidence: Started as background task in `lifespan()` at `main.py:705`
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-01
- **Code excerpt:**
```python
# Filter cascade:
# 1. SKIP_NORMAL_DAY_TYPE → "NORMAL_DAY_SKIP"
# 2. footprint_opposes_direction → "FOOTPRINT_OPPOSES"
# 3. Killzone filter (STRICT only) → "OFF_HOURS_BLOCKED"
# 4. score < 70 → "LOW_SCORE"
# 5. Another trade open → "OTHER_TRADE_OPEN"
# 6. detected - last_close < 300s → "COOLDOWN"
# 7. → executed_in_sim = True
```

---

### 1.23 — Trade Health Score

- **Layer:** backend
- **Files:**
    - `backend/main.py:223-251` (inline health calc in `_build_status_payload`)
- **Purpose:** Real-time health score (0-100) for an open trade, based on P&L position, distance to stop, and bar delta. Baseline 70, adjustments: +10 (PnL > 1R), +5 (PnL > 0), -20 (PnL < -0.5R), -10 (PnL < 0), -25 (dist stop < 1pt), -15 (opposing delta > 80).
- **Inputs:** Current price, entry, stop, direction, bar delta
- **Outputs:** Integer 0-100
- **Invocation:** per-WebSocket-push (every 2 seconds while trade is open)
- **In production?** YES (always)
  → Evidence: Part of `_build_status_payload` which pushes to all WS clients
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-01

---

### 1.24 — Setup Expiry

- **Layer:** backend
- **Files:**
    - `backend/main.py:272-295` (function `_setup_expire_loop`)
- **Purpose:** Marks setups as EXPIRED if no new observation for 5+ minutes. Runs every 2 minutes.
- **Inputs:** `last_seen_ts` on setup, current time
- **Outputs:** Setup status = 'EXPIRED'
- **Invocation:** background loop (every 120 seconds)
- **In production?** YES (always)
  → Evidence: Started as background task in `lifespan()`
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-01

---

### 1.25 — Shadow Engine Setup Score

- **Layer:** bridge
- **Files:**
    - `bridge/shadow_trader.py:606-631` (function `_compute_score`)
- **Purpose:** Computes a 0-100 score for a setup hit. 3 critical checks (pattern found, price correct side, delta confirms > 50). 2 bonus checks (volume > 1.1x, reversal candle pattern). All criticals = 45-100% range.
- **Inputs:** direction, hit, bar data, rel_vol, cvd, candle patterns, price
- **Outputs:** Integer 0-100
- **Invocation:** NOT CALLED — see §6 (Dead Code)
- **In production?** DEAD (not called from anywhere in the codebase)
  → Evidence: No callers found in shadow_trader.py or anywhere else. The quality score (§1.1) is used instead.
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-04-20

---

### 1.26 — Pattern Scanner (Liquidity Sweep Chain)

- **Layer:** bridge
- **Files:**
    - `bridge/pattern_scanner.py:1-1229` (full file, ~10 pattern detectors)
- **Purpose:** Identifies classic chart patterns: Head & Shoulders, Double Top/Bottom, Cup & Handle, Ascending/Descending Triangles, Liquidity Sweep chain (Sweep → MSS → FVG on 5m), Base detection, MSS, FVG. Each returns entry/stop/targets with confidence score.
- **Inputs:** 960 × 3min candles, levels, day_type
- **Outputs:** List of `PatternResult` dicts with pattern, direction, entry, stop, T1/T2/T3, confidence
- **Invocation:** every 60 seconds (from bridge main loop via `PATTERN_SCAN_INTERVAL`)
- **In production?** YES (always)
  → Evidence: Consumed by frontend via Redis `mems26:patterns` key, displayed in PreEntryChecklist
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-04-17

---

### 1.27 — Backtest Scenario Engine

- **Layer:** tools
- **Files:**
    - `tools/backtest/run_scenarios.py:1-605`
    - `tools/backtest/scenarios.yaml:1-107`
- **Purpose:** Offline backtest framework that replays historical setup attempts with modified scoring parameters. Tests hypotheses: different weight distributions, footprint veto, day type blocking, score thresholds.
- **Inputs:** Historical attempts from Postgres (via API), scenario YAML config
- **Outputs:** Per-scenario metrics: WR, P&L, trade count, execution rate
- **Invocation:** manual (CLI tool)
- **In production?** DISABLED (tool only, not part of production pipeline)
  → Evidence: Located in `tools/` directory, requires manual execution
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-02

---

### 1.28 — Pre-Flight Checklist Script

- **Layer:** tools
- **Files:**
    - `tools/preflight/check.sh:1-408`
- **Purpose:** Shell script that validates system readiness before trading: checks bridge connection, Redis freshness, backend health, SC JSON age, MEMS26_MODE, entry gates, killzone settings, circuit breaker state.
- **Inputs:** Running services, env vars, Redis state
- **Outputs:** PASS/WARN/FAIL for each check, total score
- **Invocation:** manual (before trading session)
- **In production?** DISABLED (manual tool)
  → Evidence: Located in `tools/preflight/`
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-05-02

---

### 1.29 — Frontend Pre-Entry Checklist

- **Layer:** frontend
- **Files:**
    - `frontend/src/components/PreEntryChecklist.tsx:57-236`
- **Purpose:** UI checklist with 10 conditions that must pass before trade execution is allowed:
  1. Day Type (not ROTATIONAL/NON_TREND/NEUTRAL)
  2. Killzone active
  3. Sweep/Rejection detected
  4. Volume Exhaustion (absorption/CVD/delta — 2 of 3)
  5. MSS + Stacked >= 2
  6. Valid FVG
  7. Health Score >= 70
  8. Circuit Breaker allows
  9. Absorption at FVG
  10. Delta 5m confirmed
- **Inputs:** Live market data via WebSocket, setup data, API calls to /trade/health and /trade/circuit-breaker
- **Outputs:** Visual checklist, enables/disables EXECUTE button. TEST mode requires only 4/10 pass.
- **Invocation:** when user selects a setup for execution
- **In production?** YES (always visible in UI)
  → Evidence: Rendered in Dashboard.tsx when setup is selected
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-04-26

---

### 1.30 — AI Signal Engine (Claude)

- **Layer:** backend (engine module)
- **Files:**
    - `backend/engine/signal_engine.py:1-233`
    - `backend/engine/models.py:1-119`
- **Purpose:** Claude AI-powered signal generation. Scores 1-10 based on market structure (CVD, POC, VWAP, Woodies, reversals). Returns direction + entry/stop/targets.
- **Inputs:** MarketData struct (price, CVD, session, profiles, patterns)
- **Outputs:** SignalResult (direction, score, confidence, entry/stop/T1/T2/T3, rationale)
- **Invocation:** on-demand (via /market/analyze endpoint)
- **In production?** DEAD (not imported anywhere)
  → Evidence: `from engine` and `import signal_engine` have ZERO matches in main.py or any other file. The engine/ module is completely orphaned.
- **Linked decision:** UNTRACKED
- **Last modified:** 2026-03-23 michaelbarg push

---

## 2. Cross-Layer Decision Flow

| System | DLL | Bridge | Backend | Frontend | DB write |
|--------|-----|--------|---------|----------|----------|
| 1.1 Quality Score | ❌ | ❌ | ✅ compute (`quality_score.py`) | ✅ display (`QualityScorePanel.tsx`) | ✅ `setup_quality_score` column |
| 1.4/1.5 3-Pillar Gate | ❌ | ✅ compute (`shadow_trader.py`) | ✅ store (`pillars_detail`) | ✅ display (journal `p1/p2/p3`) | ✅ `pillar_detail` column |
| 1.6 Day Type | ✅ classify (`MES_AI_DataExport.cpp`) | ✅ forward (`json_bridge.py:431`) | ✅ consume + override (`main.py:974-989`) | ✅ display (`DayTypeBadge/Hero`) | ✅ `day_type` column |
| 1.7 Killzone | ❌ | ✅ classify (`shadow_trader.py`) | ✅ store + filter | ✅ display (2 separate impls) | ✅ `killzone` column |
| 1.8 Gate Logic | ❌ | ✅ enforce (`shadow_trader.py`) | ⚠️ partial (seq sim has own filters) | ✅ display (sim_skip_reason) | ✅ `sim_skip_reason` column |
| 1.9 Circuit Breaker | ❌ | ✅ check (STRICT only) | ✅ compute + enforce | ✅ display (PreEntryChecklist) | ❌ (Redis only) |
| 1.12 NORMAL Skip | ❌ | ❌ | ✅ enforce (`main.py`) | ❌ | ✅ `sim_skip_reason` |
| 1.13 Footprint Opposes | ❌ | ❌ | ✅ enforce (`main.py`) | ✅ display (opposes icon) | ✅ `sim_skip_reason` |
| 1.14 Vegas Filter | ❌ | ❌ | ✅ enforce (`main.py:2680`) | ❌ | ❌ |
| 1.18 Structural Stop | ❌ | ❌ | ✅ compute (`quality_score.py`) | ❌ | ✅ `structural_stop_*` columns |
| 1.19 News Guard | ❌ | ✅ enforce (`news_guard.py`) | ❌ | ❌ | ❌ (Redis state only) |
| 1.22 Sequential Sim | ❌ | ❌ | ✅ compute (`main.py`) | ✅ display (`ShadowTradesTodayCard`) | ✅ `executed_in_sim` |
| 1.23 Trade Health | ❌ | ❌ | ✅ compute (inline) | ✅ display (PreEntryChecklist) | ❌ |
| 1.29 FE Checklist | ❌ | ❌ | ❌ | ✅ compute + display | ❌ |

---

## 3. Suspected Duplicates / Overlaps

### 3.1 — Position Sizing: quality_score.py vs main.py inline

- **Systems involved:** 1.3 (determine_position_size) and inline code at `main.py:439`
- **What overlaps:** Both compute contract count from quality score. `quality_score.py` uses day-adaptive thresholds (e.g., TREND_DAY full=60, RANGE_DAY full=70). `main.py:439` uses hardcoded `3 if score >= 70 else 2 if score >= 50 else 1`.
- **Where they diverge:** The inline code at `main.py:439` ignores day type entirely — always uses 70/50 thresholds. For TREND_DAY (full=60, half=45), the inline code would incorrectly size a score-65 setup as "half" (2 contracts) instead of "full" (3).
- **Which is older:** `main.py:439` is in the shadow simulator loop; `quality_score.py` was created 2026-04-29 (newer).
- **Which actually drives production:** BOTH — `quality_score.py` drives the `/quality/preview` API response. `main.py:439` drives the shadow sim MAE/MFE tracking (different contract counts → different P&L calculations).
- **Recommended action:** Replace `main.py:439` inline sizing with `determine_position_size()` call. The inline code predates the day-adaptive module and is now incorrect.

### 3.2 — Vegas Validation: validate_setup_against_vegas vs Quality Score Vegas component

- **Systems involved:** 1.14 (validate_setup_against_vegas) and 1.1/1.15 (Vegas scoring in quality_score.py)
- **What overlaps:** Both check Vegas trend alignment with trade direction. The standalone filter is binary (allow/reject). The quality score gives partial credit (0-30pts) and has flow override logic.
- **Where they diverge:** `validate_setup_against_vegas` rejects NEUTRAL entirely and requires exact match (LONG→BULLISH, SHORT→BEARISH). Quality score gives NEUTRAL 30% credit and has weak/strong disagree overrides. The standalone filter runs in `/trade/execute` ONLY; quality score runs in `/quality/preview`.
- **Which is older:** `validate_setup_against_vegas` appears to be older (V7.10.0). Comment says "Not wired up yet" but it IS wired (at line 2680).
- **Which actually drives production:** The standalone filter gates real trade execution (`/trade/execute`). Quality score Vegas component only affects the preview/scoring. A setup could have Vegas=0 in quality score but still be blocked by the standalone filter (which has no flow override).
- **Recommended action:** Evaluate whether the flow override logic (W35, a60e3ca) should also apply to the trade execution gate. Currently a STRONG_DISAGREE scenario where real flow favors the trade direction would still be BLOCKED at execution because the standalone filter doesn't know about flow overrides.

### 3.3 — Killzone Classification: 4 independent implementations

- **Systems involved:** bridge `shadow_trader.py:122-130`, frontend `PreEntryChecklist.tsx:43-55`, frontend `AwaitingTriggerPanel.tsx:26-49`, backend `analytics.py:139-146`
- **What overlaps:** All 4 classify current time into killzone windows. All use hardcoded time ranges.
- **Where they diverge:**
  - Bridge: LONDON (03:00-05:00), NY_OPEN (09:30-10:30), NY_CLOSE (15:00-16:00) — reads from `config.py`
  - PreEntryChecklist: London (03:00-05:00), NY_Open (09:30-10:30), NY_Close (15:00-16:00) — hardcoded
  - AwaitingTriggerPanel: London (03:00-05:00), NY_Open (09:30-10:30), NY_Close (15:00-16:00) — hardcoded
  - Analytics: London (180-300min), NY_Open (570-630min), NY_Close (900-960min) — hardcoded minutes from midnight ET
  - **DISCREPANCY:** Frontend uses minutes from midnight UTC offset manually. Bridge uses ET timezone properly. If DST changes, frontend could drift.
- **Which is older:** All created between 2026-04-17 and 2026-05-01.
- **Recommended action:** Extract killzone config into a shared constant. At minimum, frontend should fetch killzone status from the backend instead of computing locally with potentially wrong timezone logic.

### 3.4 — Score Threshold: 70 used in multiple uncoordinated places

- **Systems involved:** Multiple
- **What overlaps:** The score threshold 70 appears in:
  - `main.py:439` (shadow sim sizing: `3 if score >= 70`)
  - `main.py:658` (sequential sim: `if score < 70: continue`)
  - `main.py:3852` (API: `?min_score=70`)
  - `day_config.py:17-18` (NORMAL/DEVELOPING full_size=70, but TREND_DAY=60, GAP_FILL=65)
  - `frontend/AttemptsTable.tsx:130` (filter score >= 70)
  - `frontend/AwaitingTriggerPanel.tsx:58` (Score >= 70 check)
  - `frontend/QualityScorePanel.tsx:29` (FULL SIZE label at 70)
  - `frontend/SetupsTable.tsx:111` (tooltip "peak score >= 70")
- **The problem:** `day_config.py` defines different full-size thresholds per day type (60/65/70), but most code hardcodes 70. A TREND_DAY setup with score 63 should be FULL_SIZE (threshold=60) but is treated as "not executed" by the sequential sim (`main.py:658`).
- **Recommended action:** Replace all hardcoded 70 references with `get_config(day_type)["thresholds"]["full"]`. This is a significant correctness bug — the sequential sim is rejecting setups that the quality score module says should execute.

---

## 4. Anti-Pattern Filter Coverage (vs D-037)

| # | Anti-Pattern | Status | Where checked (file:line) | Notes |
|---|--------------|--------|---------------------------|-------|
| 1 | Footprint opposes direction | ✅ | `backend/main.py:787-797` (`footprint_opposes_direction`) + `main.py:642-648` (seq sim) + `main.py:1086-1095` (attempt logging) | Threshold=500 (env configurable). Applied in backend only (sequential sim + quality preview). NOT checked in bridge shadow engine gate logic. |
| 2 | Cluster >= 5 in 60 sec | ❌ | NOT FOUND | No cluster detection logic exists anywhere in the codebase. No grep matches for "cluster.*5" or "cluster.*60" or cluster rate-limiting. |
| 3 | LATE_DAY phase | ⚠️ | `bridge/shadow_trader.py:241-247` (Pre-Close Freeze at 15:30 ET) | Pre-Close Freeze blocks after 15:30 ET, but there is NO "LATE_DAY" phase classification. No phase-based gating between normal trading hours and 15:30. If LATE_DAY means e.g., after 14:00 ET, this is NOT implemented. |
| 4 | London killzone | ⚠️ | `bridge/config.py:111` (LONDON 03:00-05:00 ET) + `shadow_trader.py:314-319` | London killzone IS classified. But blocking is ONLY in STRICT mode (`KILLZONE_REQUIRED = True`). In DEMO mode (current production), London killzone is tag-only — trades CAN execute during London. |
| 5 | Day type DEVELOPING | ⚠️ | `backend/main.py:637-641` (NORMAL day skip only) + `tools/backtest/scenarios.yaml:85,103` (DEVELOPING blocked in scenarios) | DEVELOPING is NOT blocked in production. Only NORMAL is blocked. The backtest scenarios test DEVELOPING blocking but it's not deployed. |
| 6 | Score < 75 | ⚠️ | `backend/main.py:658` (score < 70 skip in seq sim) | Threshold is 70, NOT 75. No 75 threshold exists anywhere in production code. The day-adaptive thresholds in `day_config.py` range from 45-70 for "half" and 60-70 for "full" — none use 75. |
| 7 | NY_Close killzone | ⚠️ | `bridge/config.py:113` (NY_CLOSE 15:00-16:00 ET) | Same issue as #4 — classified but only enforced in STRICT mode. In DEMO, NY_Close is tag-only. Additionally, Pre-Close Freeze at 15:30 ET partially covers this (blocks last 30min of NY_Close window). |

**Coverage summary:** 1/7 fully implemented, 5/7 partial (⚠️), 1/7 missing (❌).

**Critical gap:** Cluster detection (#2) has ZERO implementation. If D-037 requires blocking when >= 5 setups trigger within 60 seconds, this needs to be built from scratch.

---

## 5. Direction-Specific Checklist Coverage (vs D-038)

### 5.A — LONG checklist (6 items)

| # | Item | Signal computed? | Where? | LONG-specific branch exists? |
|---|------|------------------|--------|------------------------------|
| 1 | Score >= 75 | ⚠️ Computed at >= 70 | `main.py:658`, `day_config.py:17` (NORMAL full=70) | NO — same threshold for LONG and SHORT |
| 2 | Footprint NOT opposing | ✅ | `main.py:787-797` | NO — same logic for LONG and SHORT (delta < -500 for LONG, > +500 for SHORT — threshold is symmetric) |
| 3 | Not LATE_DAY | ⚠️ Pre-Close only | `shadow_trader.py:241` (15:30 ET) | NO — same time check for both directions |
| 4 | Cluster < 5/60s | ❌ NOT FOUND | — | — |
| 5 | Not London | ⚠️ Tag-only in DEMO | `shadow_trader.py:314-319` | NO — same killzone check for both directions |
| 6 | Day type NOT DEVELOPING | ❌ Not blocked in prod | Only in backtest scenarios | NO |

### 5.B — SHORT checklist (6 items)

| # | Item | Signal computed? | Where? | SHORT-specific branch exists? |
|---|------|------------------|--------|-------------------------------|
| 1 | Vegas BEARISH or NEUTRAL | ⚠️ | `quality_score.py:46-83` (Vegas scoring) + `main.py:808-835` (Vegas filter) | NO — Vegas filter requires exact match (SHORT→BEARISH). NEUTRAL is REJECTED, not allowed for SHORT. Quality score gives NEUTRAL 30% credit but standalone filter blocks it. |
| 2 | Footprint delta negative | ⚠️ | `quality_score.py:165-183` (delta confirms direction) | YES — `(direction == "SHORT" and delta < 0)` at line 167. But this is scoring (0-14pts), not a gate. A SHORT with positive delta scores 0 on footprint but is NOT blocked. |
| 3 | Score >= 80 (NOT 75!) | ❌ NOT FOUND | No 80 threshold for SHORT | NO — zero direction-specific score thresholds exist in the codebase |
| 4 | TREND_DAY or strong momentum | ❌ NOT FOUND | — | NO — no direction-specific day type requirement |
| 5 | Not London/NY_Close | ⚠️ Same as LONG | `shadow_trader.py:314-319` | NO — same killzone logic for both |
| 6 | Cluster < 5 | ❌ NOT FOUND | — | — |

**Direction differentiation in code:** **NO**

The entire codebase uses a **single path for both LONG and SHORT**. The only direction-specific branches are:
1. Quality score Vegas component: different trend matching (LONG↔BULLISH, SHORT↔BEARISH) — but this is scoring, not gating
2. Quality score Footprint delta: confirms vs opposes based on direction — but scoring only
3. Quality score TPO: price above/below POC per direction — scoring only
4. `footprint_opposes_direction()`: symmetric thresholds (500 both ways)
5. `validate_setup_against_vegas()`: direction matching — but no flow override for SHORT

**D-038 says LONG and SHORT need DIFFERENT checklists.** This is NOT implemented. SHORT-specific requirements (Score >= 80, TREND_DAY required, Vegas NEUTRAL allowed) are completely absent. All thresholds, filters, and gates apply identically to both directions.

---

## 6. Dead / Orphaned Code

### 6.1 — `backend/engine/signal_engine.py` + `backend/engine/models.py`

- **Why dead:** Zero imports found. `from engine` and `import signal_engine` match nothing in main.py or any other file. The engine/ module is completely disconnected from the application.
- **What it was:** Claude AI signal generation (scores 1-10, direction recommendation). Predates the current Quality Score system.
- **Last modified:** 2026-03-23 (oldest code in repo)
- **Size:** 233 + 119 = 352 lines

### 6.2 — `bridge/shadow_trader.py:606-631` (`_compute_score` method)

- **Why dead:** Defined in `ShadowEngine` class but never called. No reference to `_compute_score` or `self._compute_score` exists outside its definition. The Quality Score from `quality_score.py` (§1.1) replaced this.
- **Last modified:** 2026-04-20
- **Size:** 26 lines

### 6.3 — `bridge/shadow_trader.py:37` (`BUILDING_EXPIRE_MIN = 90`)

- **Partial dead:** The building setup expiry IS used (`_check_building_expiry` method exists), but the `HYPO_FORWARD_MIN = 60` constant at line 38 is NOT referenced anywhere in the file.
- **Size:** 1 line

---

## 7. Configuration & Flags

| Flag | File | Default | Effect when ON | Effect when OFF |
|------|------|---------|----------------|-----------------|
| `MEMS26_MODE` | `bridge/config.py:16`, `backend/main.py:2485` | `SIM` | SIM: CB soft=$150, 3 contracts. LIVE: CB soft=$100, 1 contract, forces STRICT | — |
| `MEMS26_ENTRY_MODE` | `bridge/config.py:21` | `DEMO` (SIM) / `STRICT` (LIVE) | DEMO: relaxed gates (KZ/MaxTrades/Health = tag-only). STRICT: all gates enforced | — |
| `SKIP_NORMAL_DAY_TYPE` | `backend/main.py:17` | `true` | Skips all NORMAL day type setups in sequential sim | NORMAL day setups evaluated normally |
| `CONFLUENCE_FILTER_ENABLED` | `backend/main.py:18` | `true` | Footprint opposition filter active | No footprint direction check |
| `FOOTPRINT_OPPOSES_THRESHOLD` | `backend/main.py:19` | `500` | Delta magnitude threshold for opposition filter | — |
| `PRE_CLOSE_FREEZE_ENABLED` | `bridge/config.py:65` | `True` (hardcoded) | Blocks entries after 15:30 ET | — (no way to disable without code change) |
| `EOD_FLATTEN_ENABLED` | `bridge/config.py:96` | `True` (hardcoded) | Auto-close at 15:59 ET | — |
| `KILLZONE_REQUIRED` | `bridge/config.py:34,44,54` | `False` (DEMO), `True` (STRICT) | Blocks outside killzone | Killzone is tag-only |
| `PILLAR3_HARD_GATE` | `bridge/config.py:40,50,60` | `True` (DEMO/STRICT), `False` (RESEARCH) | P3 flow confirmation required | P3 becomes informational |
| `NEWS_GUARD_HARD` | `bridge/config.py:41,51,61` | `True` (DEMO/STRICT), `False` (RESEARCH) | News freeze blocks entries | News freeze bypassed |
| `QUALITY_SCORE_VERSION` | `docs/QUALITY_SCORE_V2_DESIGN.md:306` | NOT IMPLEMENTED | Would select v1/v2/ab scoring | — |

---

## 8. Production Reality Check

- **Last backend commit deployed:** UNKNOWN — needs Render check. `main` branch HEAD is `9bdcd34` (2026-05-02). If Render auto-deploys on push, this should be the deployed version.
- **Last frontend commit deployed:** UNKNOWN — needs Netlify check. Same HEAD `9bdcd34`.
- **Last DLL build version:** V7.15.0 (from `MES_AI_DataExport.cpp` version bump commit `31d004f` on 2026-05-01). DLL is compiled locally in Sierra Chart — deployment is manual.
- **Current MEMS26_MODE:** Expected `SIM` (default). Cannot confirm without checking Render env vars.
- **Current ENTRY_MODE:** Expected `DEMO` (default in SIM). Cannot confirm without checking Render/Bridge env vars.

---

## 9. Open Questions for Michael

1. **Cluster detection (D-037 #2):** Is cluster rate-limiting (>= 5 setups in 60 seconds) a new feature to build, or was it supposed to exist already?

2. **LATE_DAY phase (D-037 #3):** What time defines "LATE_DAY"? Is Pre-Close Freeze (15:30 ET) sufficient, or should there be an earlier phase (e.g., 14:00 ET) with different behavior?

3. **Score threshold 75 vs 70 (D-037 #6):** D-037 references score < 75. Production uses 70. Which is correct? Should it be 75?

4. **SHORT-specific score threshold 80 (D-038 #3):** D-038 says SHORT requires score >= 80 (not 75). This is NOT implemented. Is this a requirement for the next sprint?

5. **SHORT + TREND_DAY requirement (D-038 #4):** D-038 says SHORT requires TREND_DAY or strong momentum. This is NOT implemented. Priority?

6. **SHORT + Vegas NEUTRAL (D-038 #1):** D-038 says SHORT should allow NEUTRAL Vegas. Currently `validate_setup_against_vegas` REJECTS NEUTRAL for all directions. Should SHORT be exempted?

7. **DEVELOPING day type blocking:** Backtest scenarios test blocking DEVELOPING but production doesn't block it. Should it be blocked? The analysis shows DEVELOPING is profitable (56.4% WR, +$100).

8. **Sequential sim score threshold:** `main.py:658` uses hardcoded `score < 70` regardless of day type. `day_config.py` defines TREND_DAY full_size=60. Is the seq sim intentionally more conservative, or is this a bug?

9. **Bridge vs Backend gate divergence:** The bridge shadow engine has 11 ordered gates including 3-Pillar. The backend sequential sim has 6 filters (NORMAL skip, footprint opposes, killzone, score < 70, one-trade, cooldown). These are NOT the same logic. Which is the source of truth for "would this trade execute in LIVE"?

10. **DLL Day Type before IB lock:** Before `sesMin >= 60 && ib_locked`, day type defaults to DEVELOPING (line 825). Should DEVELOPING setups before 10:30 ET be treated differently than DEVELOPING after 10:30?

11. **Quality Score V2:** `docs/QUALITY_SCORE_V2_DESIGN.md` specifies a V2 with direction-agnostic Vegas scoring. Is this the next priority? The `QUALITY_SCORE_VERSION` env var is designed but not implemented.
