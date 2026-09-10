# DOCTRINE WALK — ENTRIES: WHERE WE ENTER + THE PRICE/VOLUME CONFIRMATION

**Date:** 2026-09-10 (written 09:35–09:55 IL, read-only — no code, `.env`, flag or service touched)
**Scope:** Michael's framing — *"וכניסה לעסקאות בנקודות יחד עם השילוב של מחיר, ווליום"*.
**Authority:** `docs/spec_authority/DALTON_DOCTRINE.md` §1.4 / §1.6 / §1.7 / §5 · `MEMS26_CONSTITUTION_V3_FINAL.txt`
· `S2_AUTH_TABLE_V1.md` · producers located via `SYSTEM_INDEX.md` / `PATTERN_ACCESS_MAP.md` (index-first, no blind grep).
**Measurement basis:** `v9_trades` where `mode='live' AND pnl_sierra IS NOT NULL AND state<>'CANCELLED' AND entry_ts>='2026-07-07'`
→ **n=108, Σ −$491.25** (broker-priced only; `pnl_sierra`, never `pnl_usd`/`daily_pnl`).

---

## 0 · Live flag state at the moment of writing (from the running backend's `[env_loader]` boot line, not memory)

```
[env_loader] applied 304 vars … DAYTYPE_POSITION_GATE=0 DAYTYPE_PLAYBOOK=1 NONTREND_DISABLE_ALL=1 DIRECTION_LSMA_VETO=1 ZLR_SPEC_V2=1
```
`.env`: `DALTON_PLAYBOOK_V1=1` · `DAYTYPE_LOCATION_GATE=1` · `ENTRY_LOCATION_QUALITY_V1=1` · `EDGE_ENTRY_LOCATION_FIX_V1=1`
· `REV_EDGE_DAY_STRUCTURE_V1=1` · `REQUIRE_WITH_TREND_DAY_DIRECTION_V1=1` · `RESPONSIVE_WITH_DAY_TREND_V1=1` · `CONT_TREND_FILTER=1`
· `S2_VSA_VOLUME=1` (variant **UNION**, `config/s2_firing.yaml:6`) · `S2_ADAPTIVE_THRESHOLDS_V1=1` · `S2_REACTIVE_DAYTYPE_V1=1`
· `S2_CVD_DETECTION_V1=shadow` · `S2_REQUIRE_COT_AMT` unset (standing-OFF) · `EDGE_FADE_V1` unset (never fired live)
· `RE_ACCEPTANCE_V1=shadow` · `VA_FADE_V1=shadow` · `FAILED_BREAK_VA_V1=shadow` · `OPENING_TYPE_GATE=0` · `DIRECTION_CONTEXT=0`.

⚠ **`PATTERN_ACCESS_MAP.md` §0 is stale on 4 rows** — it lists `LAYER0_CHOP_GATE 🔴`, `DAYTYPE_POSITION_GATE ✅ ON`,
`OPENING_TYPE_GATE ✅ ON`, `DIRECTION_CONTEXT ✅ ON`. Live truth: position-gate **OFF**, opening-type-gate **OFF**,
direction-context **OFF**. Consequence: `DAYTYPE_PLAYBOOK` is **no longer inert** (it returns FULL only when
`DAYTYPE_POSITION_GATE=1` — `daytype_playbook.py:179`), so hole **R1 in CASCADE_AUDIT §5 is closed**, and the
per-pattern×day-type matrix is now a live blocker (14 blocks in the current log window, §4 below).

---

## 1 · Status table — doctrine rule → code → status

Line numbers in the *doctrine* column are `docs/spec_authority/DALTON_DOCTRINE.md`.

| # | Doctrine rule (quote ≤12 words · line) | Code (file:line) | Status | Evidence |
|---|---|---|---|---|
| **A. RESPONSIVE vs INITIATIVE (§1.6)** |
| A1 | "the reference is the **previous day's value area**" (L75) | — nothing in the entry path reads prior-day VA except `opening_entry.py:374-380` | **MISSING** | `grep vah\|val\|value_area backend/v9/systems/five_min/five_min_system.py` → 0 hits inside `_detect_reactive` (874-1129) / `_detect_initiative` (1131-1290). The only "POC" there is a **per-bar volume POC** with an `(h+l+c)/3` fallback (`:692-696`, `:707-711`) — a bar proxy, not the day's value area. |
| A2 | "responsive is the obverse (buy below value / sell above value)" (L76) | `location_gate.py:154-165` `zone_of()` + `:335-359` | **PARTIAL — exists, but scoped away from the detector** | The rule *is* live (`DAYTYPE_LOCATION_GATE=1`): REV LONG only at `near_val`/`below_value`, SHORT only at `near_vah`/`above_value`, tolerance `0.25×IB` floor 1pt cap 4pt (`:145-151`). **But it fires only after detection, only for `family=="REV"` (`:202-203`), and only on rotation days `("Variation","Normal_Variation","Normal","Neutral")` (`:27,:205`).** REACTIVE *is* REV (`daytype_position_gate.py:43`); ZLR/INITIATIVE/GB100/TLB/TT/FLAGS are CONT (`:33-41`) → for them the gate returns `True, "CONT — with/no expansion"` at `location_gate.py:201` **without ever computing a zone**. |
| A3 | **Answer to "does anything require *below VAL* for a responsive buy?"** | `location_gate.py:335-336` | **YES — for REACTIVE/HNS/DBDT/VEGAS/GHOST/FAMIR/HTLB, on rotation days only. NO — for ZLR/INITIATIVE/GB100/TLB/TT/FLAGS, ever.** | Verified by family map + the `family != "REV"` early return. |
| A4 | "initiative activity carries more confidence than responsive" (L81) | `five_min_system.py:1039` (REACTIVE conf 0.75/0.80) vs `:1244` (INITIATIVE 0.80 flat) | **PARTIAL** | Confidence is a constant per branch, not derived from placement-vs-value. No initiative/responsive tag is emitted (doctrine §6 item 7, L256: "Initiative/responsive tagging (pp.45–49) absent from S1 outputs"). |
| A5 | Constitution: "🟢 RESPECTING — בתוך VA, Reactive OK · 🟡 EXPANDING — פורץ, Initiative OK" (`MEMS26_CONSTITUTION_V3_FINAL.txt:35-36`) | not gated anywhere; location only feeds the **size** tier (`S2_AUTH_TABLE_V1.md:156` → `quality_tier.py:35-53`) | **PARTIAL** | Confirms memory T-215: location is a size input, never an entry veto, on the S2 path. |
| **B. ACCEPTANCE vs REJECTION (§1.7)** |
| B1 | "acceptance = price *spends time* / builds double TPO prints" (L84) | `relative_features.py:157-173` (≥2 consecutive closes beyond edge + ≥8% session volume) | **ALIGNED — but it is a day-type classifier input, not an entry trigger** | Consumed by `daytype_classifier.py` / `S1_ACCEPTANCE_RECLASS_V1=1`. No entry producer calls it. |
| B2 | Same test at an **entry** | `re_acceptance.py:37-90` — closed bar, `cpos ≥0.75/≤0.25`, close crosses IB/VA/open, `|delta| ≥0.7× session-max`, `vol ≥0.7× session-max` | **BUILT, DEAD** | `RE_ACCEPTANCE_V1=shadow` **and** `:76-77 if delta is None: return None` — delta is not populated (see C3). Two independent reasons it can never trade. |
| B3 | Which detectors trigger on **close-beyond** vs **touch** | INITIATIVE: `b4["c"] > b1["h"]` (`:1215`) / `< b1["l"]` (`:1254`) — **close-beyond, 1 bar** · REACTIVE: `b4["c"] > b3_high` (`:970`, relaxed to 75% of b3 range in a volatile regime, `:137-144`) — **close-beyond, 1 bar** · `location_gate.probe_level`/`probe_detected` (`:71-74`) — **penetrate + close back inside = rejection, 1 bar** · ZLR `zlr.py:220/:296` `entry = bar.close` — **no level, no acceptance test at all** · EDGE_FADE `edge_fade.py:124-141` — probe of session H/L + `close_pos ≤0.5` — **1-bar rejection** | **PARTIAL across the board — "1 closed bar" everywhere, "N bars / TPO time" nowhere on the entry path** | Nothing on the entry path implements the doctrine's *time*-based acceptance (≥2 bars). Only the S1 classifier does. Doctrine L91: "no acceptance test at prior-day VA/range, balance-area, gap". |
| B4 | "rejection = tails, swift moves away" (L84) | `location_gate.py:71-74` probe (LIVE, REV-only) · `edge_fade.py:124-141` (flag OFF) · `dalton_edge.py` (`DALTON_EDGE_V1=live`) | **PARTIAL** | Rejection is implemented and live — but again only for the REV family, and only as a *permission* on a fade, never as its own trigger for CONT. |
| **C. VOLUME (§1.4 "volume acceptance"; §5 sizing)** |
| C1 | VSA gate — b2 volume collapse | `five_min_system.py:915-936`: rolling20 mean of `bars[:-3]`; **A_VSA** `b2<b1 ∧ b2<b0 ∧ b2 ≤ 0.7×roll20`; **B_RVOL** `b2 ≤ 0.5×roll20`; **C_STRICT** `A ∧ b2_range < 0.7×ATR`; live variant **UNION** (`config/s2_firing.yaml:6`) | **ALIGNED, input alive, ratio is relative → did NOT silently drift** | Measured on `v9_bars_5min_woodies`, RTH 16:30–23:00 IL, 3,139 bars, 8 ISO weeks — see §2. |
| C2 | Lookback quiet gate `max(3 bars) < 0.6×b1_vol` (`:85`, `:988-991`) | bypassed: `if S2_VSA_VOLUME: lookback_quiet = True` (`:993-994`, `:1225-1226`) | **INERT** (Michael-approved 2026-06-02) | — |
| C3 | CVD / delta requirement | `_compute_setup_cvd` `:749-822` reads `v9_bars_cumulative_delta`; consumers `:1021,:1090,:1235,:1264` | **DEAD INPUT — fail-open** | (a) `S2_CVD_DETECTION_V1=shadow` → never blocks. (b) `[S2-CVD] insufficient coverage: 1/20 rows (min=18) — returning None (Rule 1)` × **40,773** lines in `/tmp/backend.err.log`, still firing **today 09:40:15**. (c) On all **108** live broker-priced trades, `cross_context→footprint_system`: `cot` present 98/108 but **cot≠0: 0/108, delta≠0: 0/108, cumulative_delta≠0: 0/108**. |
| C4 | COT/AMT order-flow confirmation | `:903-905`, `:983`, `:1065`, `:1160-1162`, `:1213`, `:1255` | **CORRECTLY OFF** (`S2_REQUIRE_COT_AMT` standing-OFF, CLAUDE.md §S2⟂S3) | C3 proves the input is zero on 108/108 rows — re-requiring it would block every S2 fire. The standing decision is empirically right. |
| C5 | Belly / belly_ratio (footprint) | `:960,:965,:996-997,:1069-1070` | **INERT (graceful)** | `belly is not False` → `None` passes; `belly_ratio is None` → passes. `v9_bars_footprint` max ts = **2026-09-06 17:05** (4 days stale). |
| C6 | Opening volume-vs-median | `opening_entry.py:341-388`: `if opening_vol < median_open_vol: return None` (relative, `:356-360`), + 30-min momentum `≥2.0pt` (`:337`), + acceptance of **PDH/PDL/prior VAH/VAL** with a **1.0pt absolute buffer** (`:338,:374-380`) | **ALIGNED — the ONE live consumer of prior-day VA on any entry path** | `OPENING_DIR_FUSION_V1=1`. But it is a *direction filter for opening entries only* — it never reaches S2/S4. |
| **D. CANDLE STRUCTURE** |
| D1 | Evidence must be relative to the leg and the level (Michael, repeated; `TREND_STEP_AUDIT` found absolute thresholds fail OOS) | `entry_location_quality.py:33-37,79-116`: `pos=|entry−leg_base|/L ≤0.66` · `rr=stop/ATR ≤1.5` · `ex=(entry−VAH)/VA_width ≤0.25` | **ALIGNED — all three relative** | `ENTRY_LOCATION_QUALITY_V1=1`, gateway `:1892-1960`. Note its `vah/val` come from `tpo.json` = **today's developing VA** (`:1913-1918`), not prior day. |
| D2 | Bar geometry, ATR-relative | `:924-926` `b2_range < 0.7×ATR` · `:1180-1184` expansion floor `max(P80 of last-20 ranges, 0.55×ATR14) ×0.85` on Trend/Variation · `:1197` join cap `0.55×ATR` · `:164-178` `get_expansion_range` = `k × mean(last-N ranges)` | **ALIGNED** | Relative by construction. |
| D3 | Bar geometry, **absolute** points | `edge_fade.py:50-53`: `EDGE_ZONE_PTS=3.0`, `EDGE_MIN_RANGE_PTS=20.0`, `EDGE_STOP_OFFSET_PTS=1.5`, `EDGE_STOP_CAP_PTS=15.0` · `five_min_system.py:117` `_VOL_EXP_FLOOR_CAP_PT=8.0` · `opening_entry.py:337-338` `2.0`/`1.0` pt | **CONTRADICTS D1** | All fixed MES points, none scaled to ATR or to the level being tested. `edge_fade.py` is `EDGE_FADE_V1`-OFF so it costs nothing today; `_VOL_EXP_FLOOR_CAP_PT` and the fusion constants are live. |
| D4 | Close location within the bar, relative to the **level** | `edge_fade.py:118` `close_pos=(c−l)/range` · `re_acceptance.py:80` same · `location_gate.py:71-74` close-back-inside-the-level | **PARTIAL** | `close_pos` is bar-relative (correct); only `probe_level` measures the close against the **level**, and only for REV. |
| **E. ENTRY POINT / ORDER PLACEMENT** |
| E1 | ZLR — source (`S4_WOODIES_TABLE_A`, `PATTERN_ACCESS_MAP.md:§2`): "buy-stop 1T above the high of the Stage-3 bar" | `zlr.py:220` (LONG) and `zlr.py:296` (SHORT): **`entry = bar.close`** | **CONTRADICTS** | The source's buy-stop is a momentum filter — the *next* bar must take out the signal-bar high. The code takes **every** Stage-3 bar at its close, with no confirmation. This is the largest single entry-placement deviation in the stack and ZLR is the largest producer. |
| E2 | REACTIVE / INITIATIVE — entry at the B4 close (`:970`, `:1215`) | as specified (Master Summary Sheet 2) | **ALIGNED** | Entry = the confirming bar's close, i.e. up to 5 min after the geometry completes. Structural anchor recorded (`:1038`, `:1108`, `:1243`, `:1272`). |
| E3 | Late entries? | — | **Measured: no for REACTIVE, partly yes for ZLR** | ZLR median hold **10.1 min**, losers **7.8 min**, 19/34 exits are stop-outs worth **−$1,343.75**. Entering at the close of a CCI-geometry bar with no level and no acceptance produces a stop-out inside two bars. REACTIVE median hold **26.4 min**, winners **69.0 min**, only 6 stop-outs worth **−$48.75**. |

---

## 2 · Did the fixed volume ratio silently become a different rule?

RTH 16:30–23:00 IL, `v9_bars_5min_woodies`, 8 ISO weeks + current partial, VSA/RVOL/STRICT recomputed exactly as
`five_min_system.py:915-926` (rolling-20 of `bars[:-3]`, b2 = 3rd-from-last):

| week | bars | median b2 vol | median roll-20 | VSA % | RVOL % | STRICT % | UNION % |
|---|---|---|---|---|---|---|---|
| 2026-W29 | 261 | 7,543 | 8,814 | 21.8 | 9.2 | 12.3 | 21.8 |
| 2026-W30 | 337 | 6,749 | 8,210 | 24.3 | 16.0 | 13.6 | 24.3 |
| 2026-W31 | 360 | 8,852 | **12,041** | 24.4 | 10.3 | 12.8 | 24.4 |
| 2026-W32 | 328 | 7,434 | 10,336 | 28.4 | 10.7 | 14.9 | 28.4 |
| 2026-W33 | 365 | 6,316 | 7,920 | 27.1 | 6.8 | 10.7 | 27.1 |
| 2026-W34 | 365 | 6,564 | 8,030 | 26.0 | 10.7 | 12.1 | 26.0 |
| 2026-W35 | 365 | 7,022 | 8,767 | 26.8 | 10.7 | 14.5 | 26.8 |
| 2026-W36 | 365 | 7,386 | 9,261 | 26.0 | 6.0 | 11.5 | 26.0 |
| 2026-W37 (partial) | 183 | 5,630 | **7,785** | 30.6 | 14.2 | 16.4 | 30.6 |

**Verdict: NO silent drift on the S2 volume gate.** The volume *regime* did move — median rolling-20 ran
12,041 (W31) → 7,785 (W37), a **1.55× swing** — but every threshold in the gate is a **ratio to a rolling mean**
(`0.7×roll20`, `0.5×roll20`, `0.8×roll20`), so the pass-rate stayed inside 21.8 %–30.6 % (A_VSA) across the whole
range. UNION == VSA in every week (the RVOL and STRICT variants are strict subsets of what VSA already passes,
so `UNION` adds **zero** fires over `A_VSA` — the 2026-06-12 variant change was a no-op).
Note W37's +40 % relative rise in pass-rate (21.8→30.6) tracks the *falling* regime — the gate gets looser as
volume dries up. That is the direction the doctrine wants (quiet b2 = withdrawal of supply), but it is unmeasured.
**The genuinely absolute constants are elsewhere** (D3): `_VOL_EXP_FLOOR_CAP_PT=8.0`, `FUSION_MOM_MIN_PTS=2.0`,
`FUSION_ACCEPT_BUFFER_PTS=1.0`, and the whole `edge_fade.py` constant block.

---

## 3 · Producer table — broker-priced live, 2026-07-07 → 2026-09-10

`mode='live' AND pnl_sierra IS NOT NULL AND state<>'CANCELLED'`; short sign pts = entry − exit; stop width from
`quality→initial_stop` (the `stop` column is the *current* stop and reads 0.25pt after BE moves — do not use it).

| producer | n | Σ $ | win % | med init-stop (pt) | med hold (min) |
|---|---:|---:|---:|---:|---:|
| REACTIVE_SHORT | 9 | **+412.50** | 67 % | 7.75 | 69.0 |
| REACTIVE_LONG | 4 | **+310.00** | 75 % | 6.0 | 11.3 |
| GB100 | 7 | +277.50 | 71 % | — | 30.1 |
| INITIATIVE_LONG | 8 | +168.75 | 75 % | 6.5 | 40.1 |
| DOUBLE_BOTTOM_EE_LONG | 2 | +103.75 | 50 % | 6.5 | 30.9 |
| HTLB | 3 | +37.50 | 67 % | 3.75 | 9.7 |
| TT | 1 | +33.75 | 100 % | — | 71.5 |
| VEGAS | 1 | −40.00 | 0 % | 4.0 | 2.7 |
| BEAR_FLAG_SHORT | 3 | −58.75 | 67 % | 8.5 | 20.4 |
| CONFLUENCE_RI_ZLR | 1 | −60.00 | 0 % | 4.5 | 0.7 |
| OPENING_ORR | 1 | −95.00 | 0 % | 10.0 | 1.9 |
| BULL_FLAG_LONG | 1 | −137.50 | 0 % | 5.25 | 13.1 |
| *(pattern_id NULL)* | 10 | −157.50 | 50 % | 6.0 | 12.2 |
| GHOST | 5 | −161.25 | 20 % | 5.25 | 5.6 |
| TREND_STEP | 4 | −166.25 | 25 % | 5.0 | 9.8 |
| INITIATIVE_SHORT | 11 | −180.00 | 36 % | 5.5 | 8.9 |
| **ZLR** | **34** | **−347.50** | **44 %** | **5.0** | **10.1** |
| OPENING_DRIVE | 3 | −431.25 | 0 % | 4.5 | 0.8 |
| **TOTAL** | **108** | **−491.25** | 46 % | | |

By `entry_kind` (`config/dalton_playbook.yaml:24-54` map, applied by `dalton_playbook.entry_kind_for`):

| entry_kind | n | Σ $ | win % | Jul | Aug | **Sep** |
|---|---:|---:|---:|---:|---:|---:|
| **EDGE_FADE** (= REACTIVE_LONG + REACTIVE_SHORT) | **13** | **+722.50** | **69 %** | +127.50 (n=6) | +595.00 (n=7) | **0 trades** |
| BREAK (ZLR, INITIATIVE, GB100, GHOST, VEGAS…) | 68 | −178.75 | 47 % | | +882.50 (n=30) | −467.50 (n=17) |
| PULLBACK (TREND_STEP) | 4 | −166.25 | 25 % | | −166.25 | 0 |
| REVERSAL (OPENING_ORR) | 1 | −95.00 | 0 % | | −95.00 | 0 |
| WITH_DRIVE (OPENING_DRIVE) | 3 | −431.25 | 0 % | | −100.00 | 0 |
| unmapped (HTLB / TT / FLAGS / CONFLUENCE) | 9 | −187.50 | 56 % | | | −137.50 |
| NULL pattern | 10 | −157.50 | 50 % | | −157.50 | 0 |

### ✅/❌ Verification of the two figures I was asked to check independently
- **EDGE_FADE n=13, +$722.50, 69 % — ✅ CONFIRMED** exactly (9 winners / 13).
- **ZLR n=34, −$347.50, 44 % — ✅ CONFIRMED** exactly (15 winners / 34).
- **"the only entry_kind positive in *both* the August and September windows" — ❌ FALSE.** EDGE_FADE has
  **zero September trades**. Its last live broker-priced fire is **id 877, 2026-08-31 17:00:03**. In September
  *nothing* was positive: BREAK −$467.50 (n=17), BULL_FLAG_LONG −$137.50 (n=1). The correct statement is
  **"EDGE_FADE is the only entry_kind positive in July *and* August, and it has been silent for 10 days."**

---

## 4 · 🔴 The finding that matters most today: the only positive producer is being blocked, not missing

`v9_five_min_setups` **detected 17 REACTIVE setups between 2026-09-01 and 2026-09-09**
(09-01 ×2, 09-02 ×3, 09-03 ×4, 09-04 ×1, 09-07 ×5, 09-08 ×1, 09-09 ×1). **Live fires: 0.**
Every REACTIVE that reached the gateway inside the current `backend.err.log` window was blocked — by **four
different gates**, no single culprit:

```
2026-09-07 17:00  REACTIVE_SHORT  → blocked_by=direction_compass
2026-09-07 17:05  REACTIVE_SHORT  → blocked_by=location_gate
2026-09-07 18:00  REACTIVE_SHORT  → blocked_by=daytype_playbook
2026-09-07 19:35  REACTIVE_LONG   → blocked_by=daytype_playbook
2026-09-07 19:40  REACTIVE_LONG   → blocked_by=daytype_playbook
2026-09-08 22:50  REACTIVE_SHORT  → blocked_by=eod_entry_cutoff
2026-09-09 20:40  REACTIVE_SHORT  → blocked_by=dalton_intent:kind
```

Root of the largest slice (`daytype_playbook`, 3/7): `config/daytype_playbook.yaml:188` —
`REACTIVE: { group: REV, require_with_trend: true, … }`, enforced at `daytype_playbook.py:194-209` on
`_DIRECTIONAL_DAYS = {"Trend_Normal","Trend_DD","Variation"}` (`:36`). **"Variation" is the modal live label**
(21/34 ZLR and 6/13 REACTIVE carry it). So on the most common day of the week, the *responsive* family is
required to be **with-trend** — the doctrinal inverse of a responsive entry. This is not a bug: it is Michael's
ruling `RESPONSIVE_WITH_DAY_TREND_V1` (07-23, `config/RULED_FLAGS.yaml:193`) layered on
`REQUIRE_WITH_TREND_DAY_DIRECTION_V1` (07-20, `:188`), both **standing and correct at the time**. What changed
since is that `DAYTYPE_POSITION_GATE` went to **0**, which un-inerted `daytype_playbook` and turned an advisory
matrix into a live blocker. **Nobody ruled that combination.** It needs a number, not an argument.

Meanwhile the *negative* producer kept firing: **ZLR is CONT (`daytype_position_gate.py:36`) → exempt from the
value-location rule (`location_gate.py:202-203`) and from `require_with_trend`** — it took 4 more live trades in
September for **−$263.75**.

**Second-order proof that the family split is wrong**: `location_gate.py:12` cites its own justifying evidence as
*"#449/#452/#456 (mid-value, no probe) BLOCKED"*. Those three trade ids are **ZLR SHORTs** (07-21 20:56 / 21:05 /
21:55, all `mid_value`, together **−$130.00**). Because ZLR is CONT, the gate that was built on them **cannot
block them** — it returns at `:201` before the zone is ever computed.

---

## 5 · EDGE_FADE vs ZLR — what actually separates them

Location reconstructed with the gate's own `zone_of()` (0.25×IB tolerance, floor 1 / cap 4) against the
developing VA carried in each trade's `cross_context→tpo_system` at entry.

| cut | ZLR (n=34) | EDGE_FADE / REACTIVE (n=13) |
|---|---|---|
| `mid_value` entries (no reference) | **n=8, −$341.25, 25 %** | n=3, +$213.75, 100 % |
| entries ≥21:00 IL (phase D) | **n=5, −$243.75, 0 %** | n=0 |
| **`mid_value` OR ≥21:00 (union)** | **n=11, −$490.00, 18 %** | n=3, +$213.75, 100 % |
| **everything else** | **n=23, +$142.50, 57 %** | n=10, +$508.75, 60 % |
| day type: Variation | n=21, −$461.25, 38 % | n=6, +$3.75, 50 % |
| day type: Trend_* / Nonconviction / None | n=12, +$168.75, 58 % | **n=6, +$677.50, 83 %** |
| median hold — all / winners / losers | 10.1 / 12.2 / 7.8 min | **26.4 / 69.0 / 3.6 min** |
| exits: stop-outs vs targets | 19 stops = **−$1,343.75**; 9 target-hits = +$578.75 | 6 stops = **−$48.75**; 4 target-hits = +$576.25 |
| median \|entry − POC\| — winners / losers | 14.5 / 15.3 pt (**no separation**) | 5.5 / 15.5 pt (**3× separation**) |

**The separator, in one number: `mid_value OR ≥21:00` costs ZLR −$490.00 on 11 trades at an 18 % win rate;
strip those 11 and ZLR's remaining 23 trades are +$142.50 at 57 %, i.e. the entire ZLR loss and more.**
EDGE_FADE has essentially no exposure to that condition (3 trades, all winners).

It is **not** volume (both run the same live VSA gate; CVD is dead for both — §C3). It is **not** stop width
(ZLR losers had *tighter* initial stops than its winners: 3.75 vs 6.12 pt median). It is **reference and phase**:
ZLR enters at the close of a CCI-geometry bar with no level to lean on, and the losers exit in 7.8 minutes.
REACTIVE enters at a bar that closed beyond a *structure* (b3's extreme) with a recorded structural anchor, and
its winners run 69 minutes to T3 (3 of its 4 target-hits are T3, worth +$505.00).

**Honesty caveat, stated because it cuts against the live gate.** Reconstructing `zone_of` for the 24 REV-family
broker-priced trades gives: *at the doctrinally correct edge* n=5, **−$127.50**, 20 % win · *wrong location*
n=19, **+$790.00**, 63 % win. That is the opposite of what `DAYTYPE_LOCATION_GATE` assumes. n is small, my
reconstruction uses the developing VA from `cross_context` rather than the gate's `tpo.json` + gap adjustment,
and I did not reconstruct the probe requirement — so this is **not** a verdict, it is a flag that the live
location gate has **never been measured against broker-priced P&L**. Per the learning doctrine
(`LEARNING_DOCTRINE_2026-09-09.md`), that makes it an `UNMEASURED` ruled flag.

---

## 6 · Gaps ranked by money-relevance

| # | Gap | Money (measured) | Smallest correct fix | Ruling status |
|---|---|---|---|---|
| **G1** | The only positive producer (EDGE_FADE/REACTIVE, +$722.50, 69 %) has taken **0 of 17 detected setups** since 09-01, because `daytype_playbook` became a live blocker when `DAYTYPE_POSITION_GATE` went to 0, and `daytype_playbook.yaml:188` requires the *responsive* family to be with-trend on Variation days. | +$722.50 producer at **zero throughput**; 10 sessions | **Measure before touching anything**: replay the 17 September REACTIVE setups through the current gate chain and report Σ$ if allowed. Then one ruling on the `require_with_trend` × `Variation` cell only. Do **not** flip `DAYTYPE_POSITION_GATE` back — that would silently re-inert the whole matrix. | **NEEDS-MICHAEL** — the *combination* (`RESPONSIVE_WITH_DAY_TREND_V1` × non-inert playbook) was never ruled; the two flags individually were (07-20, 07-23). |
| **G2** | ZLR is family **CONT**, so the value-location rule + probe (`location_gate.py:202-203`) and `require_with_trend` never apply to it. It entered `mid_value` 8× for **−$341.25**. The gate's own cited evidence (#449/#452/#456, −$130.00) is ZLR and is unblockable. | **−$341.25** | Add a `mid_value` veto for CONT on rotation days — i.e. extend `location_gate.py:187-201` with the same `zone_of` computation it already imports, blocking CONT only at `mid_value` (leave `near_*`/`beyond` alone). ~6 lines, flag-gated, replay-verified. | **NEEDS-MICHAEL** (trading-risk surface; new behavior, no prior ruling). |
| **G3** | Phase-D (21:00+ IL) entries: **n=14, −$395.00** across all producers, vs n=94, −$96.25 before 21:00. ZLR alone: n=5, −$243.75, **0 % win**. | **−$395.00** | **ALREADY CLOSED 09-09.** `DALTON_PLAYBOOK_V1=1` + `config/dalton_playbook.yaml:21 phase_d: manage_only` → `dalton_playbook.py:74-77` returns phase D → `size_frac 0.0` → `evaluate_gate:175-176` blocks. Verified live: **74 `dalton_intent:stand_down` blocks** in the log, 152 `dalton_intent` blocks on 09-09. **No action — do not re-open.** | **RULED + LIVE** (Michael 09.09 11:15). |
| **G4** | 18 broker-priced trades (**−$850.00**) carry a pattern id that maps to **no family** — `TREND_STEP` (4, −$166.25), `OPENING_DRIVE` (3, −$431.25), `OPENING_ORR` (1, −$95.00), and **10 rows with `pattern_id_at_entry` NULL** (−$157.50). Unmapped → `_pattern_family` returns `None` → **fail-open on every family gate** (`location_gate.py:202`, `daytype_position_gate.py:84`). | **−$850.00** | Two lines: add `TREND_STEP`→CONT and `OPENING_*`→their family in `daytype_position_gate.py:33-48`; and fix whatever writes NULL `pattern_id_at_entry` (a recording bug, zero trading risk). | Family-map addition = **NEEDS-MICHAEL** (changes what gets blocked). NULL-pattern recording fix = **SHIPPABLE**. |
| **G5** | ZLR entry placement contradicts its own source: `zlr.py:220/:296` `entry = bar.close`, source says buy-stop 1T above the Stage-3 bar high. No momentum confirmation → 19/34 stop-outs, −$1,343.75, median loser held 7.8 min. | up to **−$347.50** (all of ZLR) | Shadow-only first: emit the source-correct stop-entry alongside the close-entry for 20 sessions and compare. Do not change the live trigger on an argument. | **NEEDS-MICHAEL** after the shadow number. |
| **G6** | The doctrine's defining reference — **prior-day value area** — is read by exactly one live entry consumer (`opening_entry.py:374-380`, opening window only). `_detect_reactive` / `_detect_initiative` never see it; `location_gate` and `entry_location_quality` use **today's developing** VA. Doctrine §1.6 L75. | not separately priced; it is the substrate under G1/G2 | Feed prior VAH/VAL into `location_gate.decide_location` alongside the developing pair (the plumbing exists — `location_gate.py:260-300` already reads the previous RTH session for `EDGE_ENTRY_LOCATION_FIX_V1`). Flag-gated, shadow-tagged. | **NEEDS-MICHAEL**. |
| **G7** | Acceptance-at-a-level as an **entry** is built and doubly dead: `RE_ACCEPTANCE_V1=shadow` **and** `re_acceptance.py:76-77` hard-requires `delta`, which is 0 on 108/108 trades. Same starvation makes `S2_CVD_DETECTION_V1` a no-op (`insufficient coverage 1/20`, 40,773 log lines, still today). | opportunity cost only | Fix the **feed**, not the flag: `v9_bars_cumulative_delta` holds 6,628 rows total / 4,103 non-zero since 07-07 against ~5,000 expected RTH bars, and `v9_bars_footprint` is stale at 2026-09-06 17:05. This is a bridge/DLL question, and it is the precondition for *any* "price + volume together" confirmation. | **SHIPPABLE** (diagnostic; no trading-logic change). |
| **G8** | Absolute-point thresholds surviving in live code: `_VOL_EXP_FLOOR_CAP_PT=8.0` (`five_min_system.py:117`), `FUSION_MOM_MIN_PTS=2.0` / `FUSION_ACCEPT_BUFFER_PTS=1.0` (`opening_entry.py:337-338`), and the whole `edge_fade.py:50-53` block. Contradicts D1 and the `TREND_STEP_AUDIT` finding. | unpriced (edge_fade is OFF) | Express each as an ATR fraction with the current value as the calibration point, flag-gated, byte-identical when OFF. | **SHIPPABLE** as shadow; enabling = **NEEDS-MICHAEL**. |
| **G9** | `config/s2_firing.yaml:6 variant: UNION` is a **no-op** — RVOL and STRICT pass strict subsets of VSA in all 8 weeks measured (UNION % ≡ VSA % in every row of §2). | $0 | Documentation only: mark UNION ≡ A_VSA in `FLAG_INDEX`/`PATTERN_ACCESS_MAP` so nobody re-litigates it. | **SHIPPABLE** (doc). |
| **G10** | `PATTERN_ACCESS_MAP.md` §0 states 4 gate states that are false live (`DAYTYPE_POSITION_GATE`, `OPENING_TYPE_GATE`, `DIRECTION_CONTEXT` all OFF; playbook no longer inert). A stale map is how G1 went unnoticed. | indirect | Regenerate/annotate §0 from `docs/FLAG_INDEX.md` + the `[env_loader]` boot line. | **SHIPPABLE** (doc). |

---

## 7 · Answer

**Can we enter at the right points today at 16:30?** Partly. The *placement* machinery is doctrine-correct and
live — value-edge zoning with a mechanical probe (`location_gate.py:335-359`), three relative quality
disqualifiers (`entry_location_quality.py:79-116`), relative volume and expansion floors (§2), and as of
yesterday the phase-tree that finally stands us down after 21:00 (−$395.00 of the −$491.25 total loss sat in that
window). What is **not** right is *who* those rules reach: the responsive family that made all the money
(+$722.50, 69 %) has been blocked on 7 of 7 gateway arrivals since 09-01 and has not traded in 10 days, while the
continuation family that lost the money (ZLR −$347.50) is structurally exempt from the value-location rule and
entered `mid_value` eight times for −$341.25. **The single change that would most improve entry quality: replay
the 17 September REACTIVE setups through the current gate chain and put one number in front of Michael for the
`daytype_playbook.yaml:188` `require_with_trend` × `Variation` cell — because today's most likely label is
Variation, and on a Variation day the system is currently allowed to buy the middle of value with ZLR and
forbidden to fade its edge with REACTIVE.**

---

*Every claim above carries a `file:line` or a query result. No claim rests on memory, on `FLAG_INDEX` semantics
columns, or on `pnl_usd`. Written read-only: no code, config, `.env`, flag or service was modified.*
