# Spec Lock Template V2

**Use:** Michael fills in once per spec area · אחר כך LOCKED · changes רק דרך D-XXX חדש.
**Version:** V2 (23/5 17:30) — Spec lock 2 (Adaptive Stop multipliers) removed · כבר locked ב-Master Summary Sheet 4.

---

## Spec lock 1 · Zohar thresholds (Auth Table P-6)

נדרש לפני: S2 D-091 Packages 2a, 2b, 2c


| Param                   | V1 default (Master hint)                           | מקור      | Notes                                                                                  |
| ----------------------- | -------------------------------------------------- | --------- | -------------------------------------------------------------------------------------- |
| `drop_threshold_pct`    | 90% (b2_vol ≤ 0.10 × b1_vol) — *Master Sheet 6 V3* | _________ | volume drop % for Reactive Bar 2 · "🟢 OK · לחשוף ל-config"                            |
| `belly_dominance_ratio` | **1.5×** — *Master Sheet 6 V2*                     | _________ | belly_buyers/belly_sellers · current code is "is not False" only — needs numeric check |
| `cot_window_min`        | _________                                          | _________ | session-scoped per fix (Master V10 verified 22/5)                                      |
| `amt_window_min`        | 90 min — *Master Sheet 6 V10*                      | _________ | 90-min rolling — verified 22/5                                                         |
| `expansion_ticks`       | **6-7 ticks (1.5-1.75pt)** — *Master Sheet 6 V4*   | _________ | Initiative bar 0 expansion range — "🟡 hardcoded · לחשוף ל-config"                     |
| `min_bars_for_drop`     | **3** (default) — *Master Sheet 7 Pkg 2b*          | _________ | minimum bars before drop check                                                         |


**Calibration plan:** SHADOW soak ≥20 trades · re-tune אם hit-rate < 30% · אחרת keep.

**Signed by:** Michael Barg · ____ / ____ / 2026
**Locked:** ⬜ NO / ⬜ YES (until D-XXX revises)

---

## ~~Spec lock 2 · Adaptive Stop multipliers~~ — ALREADY LOCKED in Master Summary

**Status:** ✅ N/A (locked 23/5 in `~/Downloads/S2_Master_Summary.xlsx` Sheet 4)

Values for reference (do not need re-signing — already authoritative):


| Family            | Multiplier × today_typical | Source                             |
| ----------------- | -------------------------- | ---------------------------------- |
| Reactive          | **1.0×**                   | Master Sheet 4 §"Adaptive ATR cap" |
| OFA (Initiative)  | **1.5×**                   | Master Sheet 4                     |
| Bull/Bear Flag    | **1.5×**                   | Master Sheet 4                     |
| Double Bottom/Top | **2.0×**                   | Master Sheet 4                     |
| H&S / Inverse H&S | **2.0×**                   | Master Sheet 4                     |
| **Floor** (noise) | **4 ticks (1.0pt MES)**    | Master Sheet 4                     |


**Behavior when structural > adaptive_cap:** **reduce_size · stop stays at adaptive_cap** (Master Sheet 4 §"א · עוגן מבני").

**Calibration plan:** SHADOW soak ≥10 trades per family · re-tune אם stop-out rate > 60%.

---

## Spec lock 3 · Bulkowski params (edge tolerances)

נדרש לפני: S2 D-091 Packages 5a, 5b, 5c

**Note:** Most pattern specifics (entry signals · stop anchors · T1/T2/T3 · day-type eligibility · contract split) are **already authoritative in Master Summary Sheet 2**. This spec lock fills the *edge tolerance* gaps only.

### 5a · Inverse H&S + H&S Top


| Param                        | Value                                          | Notes                                     |
| ---------------------------- | ---------------------------------------------- | ----------------------------------------- |
| `shoulder_symmetry_tol_pct`  | _________                                      | LS vs RS height diff tolerance            |
| `neckline_method`            | ⬜ linear · ⬜ horizontal                        | trendline connecting troughs (or peaks)   |
| `min_shoulder_distance_bars` | _________                                      | bars between LS and RS                    |
| `head_min_height_diff_pct`   | _________                                      | head must be at least N% beyond shoulders |
| Throwback tracking           | ✅ already in Master: Inv H&S 65% · H&S Top 68% | from Bulkowski                            |


### 5b · Double Bottom + Double Top


| Param                         | Value                                                                          | Notes                                         |
| ----------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------- |
| `equivalence_tol_pct`         | **0.15%** (D-091) — confirm                                                    | tolerance for "equal" tops/bottoms            |
| `min_distance_bars`           | _________                                                                      | bars between two bottoms/tops                 |
| `neckline_break_buffer_ticks` | _________                                                                      | confirmation = close beyond neckline + buffer |
| Eve vs Adam classification    | ⬜ shape-rounded vs sharp · ⬜ bar-count threshold · ⬜ derived from price action | how to distinguish                            |


### 5c · Bull Flag + Bear Flag


| Param                    | Value                 | Notes                                                |
| ------------------------ | --------------------- | ---------------------------------------------------- |
| `pole_min_bars`          | **2** (D-091 default) | confirm or change                                    |
| `pole_max_bars`          | _________             | upper bound for pole                                 |
| `consol_min_bars`        | _________             | minimum consol duration                              |
| `consol_max_bars`        | **7** (D-091 default) | upper bound                                          |
| `consol_slope_max`       | _________             | slight downward drift for Bull Flag                  |
| `breakout_buffer_ticks`  | _________             | confirmation = close beyond consol high/low + buffer |
| `vol_drop_pct_in_consol` | _________             | volume during consolidation (lower than pole)        |


**Calibration plan:** SHADOW soak ≥20 trades per pattern · re-tune individual params if hit-rate < 25%.

**Signed by:** Michael Barg · _22___ / _5___ / 2026  
**Locked:**  / ⬜ YES

---

*End of spec lock template V2 · 2026-05-23 17:30 IL*