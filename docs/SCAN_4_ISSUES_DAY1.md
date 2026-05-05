# MEMS26 — 4 Issues Scan Report (Day 1 EOD)
**Date:** 1/5/2026
**Mode:** Read-only investigation

## Issue 1 — OFF_HOURS_BLOCKED in SIM

- **Current mode:** SIM (env `MEMS26_MODE=SIM`, default)
- **Code location:** `backend/main.py:649-656` (sequential sim loop)
- **Logic:** UNCONDITIONAL — blocks any killzone not in {London, NY_Open, NY_Close}
- **Mode check:** None. Comment says "STRICT mode" but code has no mode check.
- **Spec violation:** YES — SIM/Research mode should allow 24/5 trading per V6.5.x spec.

```python
# W34: Killzone filter — OFF_HOURS blocked in STRICT mode  ← comment is WRONG
_ALLOWED_KZ = {"London", "NY_Open", "NY_Close"}
_kz_setup = s.get("killzone") or "OFF_HOURS"
if _kz_setup not in _ALLOWED_KZ:  # ← no mode check
    ...
    continue
```

- **Impact:** 117 setups blocked today that should have been allowed in SIM mode.
- **Recommended fix:** Wrap in mode check: `if _MODE == "LIVE" or _MODE == "STRICT":` before the killzone filter. Or add env var `KILLZONE_FILTER_ENABLED`.

## Issue 2 — NORMAL_DAY_SKIP filter

- **Env var:** `SKIP_NORMAL_DAY_TYPE` = `"true"` (default ON)
- **Code location:** `backend/main.py:637-641` (sequential sim) + `main.py:1083` (phase 6 logger)
- **Skip logic:** ALL setups with `day_type == "NORMAL"` are skipped unconditionally.
- **Day type distribution today:** NORMAL=1707 (43%), DEVELOPING=1678 (42%), TREND=92 (2%), RANGE=179 (4%)
- **Aligned with W20 intent:** YES — W20 was intentional to skip NORMAL days during Phase 3.2.
- **Impact:** 86 setups blocked. This is by design — NORMAL day scoring was poor in analysis.
- **Recommended action:** KEEP enabled during Phase 3.2. Review after calibration data collected.

## Issue 3 — Footprint reason strings

- **Code:** `quality_score.py:183`
  ```python
  reasons.append(f"Footprint: delta={delta:+d} opposes {direction}")
  ```
- **Bug type:** NOT A BUG — the `direction` variable is correctly used.
- **What user saw:** "delta=-1942 opposes LONG" on a SHORT setup.
- **Explanation:** The QualityScorePanel frontend sends `direction: 'LONG'` hardcoded (line 75 of QualityScorePanel.tsx: `body: JSON.stringify({ direction: 'LONG', entry: price, stop: price - 5 })`). The dashboard Quality Score panel ALWAYS shows the LONG score, not the PLANNED direction's score.

**API verification:**
- SHORT preview: Vegas 7/30, FVG bearish 25/25, delta=+327 opposes SHORT (CORRECT)
- LONG preview: Vegas 30/30, FVG bullish 25/25, delta=+327 confirms LONG (CORRECT)

- **Root cause:** QualityScorePanel.tsx hardcodes LONG direction. It doesn't read the PLANNED setup's actual direction.
- **Recommended fix:** QualityScorePanel should use `liveSetup?.opportunity` direction instead of hardcoded LONG. Frontend-only fix.

## Issue 4 — Vegas BULLISH awarded on SHORT setup

- **Code:** `quality_score.py:46-72` — correctly checks `trend_matches` = direction+trend alignment.
- **W35 commit:** Flow-disagree override logic. Correctly implemented — only awards partial points when flow matches.
- **Bug confirmed:** NO — the Vegas logic is correct.

**API verification:**
- SHORT: Vegas 7/30 ("OPPOSES SHORT, but flow hints favor") — CORRECT
- LONG: Vegas 30/30 ("BULLISH match") — CORRECT

- **What user saw:** Dashboard showed "Vegas BULLISH match 30/30" on PLANNED SHORT card.
- **Root cause:** Same as Issue 3 — QualityScorePanel hardcodes LONG, so user sees LONG's breakdown while PLANNED card shows SHORT direction.
- **Recommended fix:** Same frontend fix as Issue 3.

## Bonus — FVG scoring

- **Same issue as Vegas?** NO — FVG logic is correct.
- **Direction mapping:** `fvg_dir = "bullish" if direction == "LONG" else "bearish"` (line 117)
- **What user saw:** "FVG bullish 10 matches" on SHORT card — this is from the LONG preview (same hardcoded direction issue).
- **API confirms:** SHORT preview shows "FVG bearish: 9 recent matches" (CORRECT).

## Skip Reasons Inventory

All skip reasons in sequential sim (`main.py:637-673`):
1. `NORMAL_DAY_SKIP` — day_type == NORMAL (W20, env-gated)
2. `FOOTPRINT_OPPOSES` — delta opposes direction > 500 threshold (W22)
3. `OFF_HOURS_BLOCKED` — killzone not in {London, NY_Open, NY_Close} (W34)
4. `LOW_SCORE` — peak_score < 70
5. `COOLDOWN` — detected < 300s after last close
6. `OTHER_TRADE_OPEN` — another sequential trade still open

Phase 6 logger filtered_reason (main.py:1083):
1. `NORMAL_DAY_SKIP` — same as above
2. `FOOTPRINT_OPPOSES` — same as above

## Verdict & Recommendations

### Critical (fix before Day 2):
1. **QualityScorePanel hardcoded LONG** — Frontend shows LONG breakdown regardless of PLANNED direction. All 4 "bugs" (Vegas, FVG, Footprint display) are symptoms of this ONE root cause. **Fix: read direction from liveSetup.** ~15 min frontend fix.

### Important (should fix this week):
2. **OFF_HOURS_BLOCKED unconditional** — Should be mode-gated. In SIM, log as tag but don't skip. Reduces today's 117 blocked → 0 blocked, giving 117 more data points for Phase 3.2. ~10 min backend fix.

### Defer to Phase 3.3:
3. **NORMAL_DAY_SKIP** — Working as intended. Keep until calibration proves NORMAL days are tradeable.
