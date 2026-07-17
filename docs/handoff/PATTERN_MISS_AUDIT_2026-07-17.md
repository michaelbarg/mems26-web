# PATTERN-MISS AUDIT — week of 2026-07-13 → 07-17 (prepared 2026-07-17, cowork-dev)

**Question:** why did the system attempt ZERO entries on every profitable move this week
(07-17: +61pt LONG 16:45-17:20 and −26pt SHORT from 17:40 — decisions feed: fired 0,
blocked 0), while Michael took +27pt manually reading the same chart?

**Answer in one line:** the losses are **upstream of the gateway** — the detectors'
entry criteria are calibrated for an *already-established, painted* trend, so on
gap-and-drive days every criterion that encodes "wait for establishment"
(Sierra BLUE paint, 6-blue-bar ZLR stage-1, fresh-cross-only GB100, B1-B4 quiet-volume
geometry against an overnight-poisoned average, FHB) expires the move before it is
tradeable. Nothing ever reached the gate chain, so no gate ever logged a block.

**TL;DR (עברית):** הזיהוי לא ירה כי כל הקריטריונים דורשים "טרנד מבוסס" — צבע BLUE של
סיירה (פיגור ~6 נרות), 6 נרות כחולים ב-ZLR, קרוס טרי בלבד ב-GB100, ונפח-שקט ב-S2 שנמדד
מול ממוצע-לילה מורעל. ביום גאפ הראלי נגמר לפני שהקריטריונים מבשילים. למטה: סקריפט כימות
+ 8 הצעות מדורגות לפסיקה, כולן דגל-OFF.

---

## 1. The exact numeric criteria that gated entries (read from code 07-17)

### S4 · ZLR (`backend/v9/systems/woodies/patterns/zlr.py`, ZLR_SPEC_V2=1 live)
| # | criterion | value | file:line |
|---|---|---|---|
| base | extreme CCI ≥ **100** (`ZLR_CCI_MIN`, unset→100) on trade side within last **12** bars (`LOOKBACK`) | 100 / 12 | zlr.py:32,132-142,200-209 |
| base | pullback bar with CCI in (−100,100] after extreme; bounce `cur>prev`; band 0<cur<**200** | — | zlr.py:203-209 |
| AP1 | bars since ANY \|CCI\|≥100 extreme ≤ **12** (else "pullback too long") | 12 | anti_patterns.py:44-82 |
| AP8 | CCI range over last **3** bars ≥ **50** (flat veto, universal) | 3/50 | anti_patterns.py:197-229 |
| S1.1 | ≥ **6** bars `trend_state==BLUE` (RED for short) since the extreme — **Sierra paint, not CCI side** | 6 | zlr.py:75-82 |
| S1.3 | ≥1 SWI yellow/green bar in trend window (\|swi\|>20) | 20 | zlr.py:46-53,84-88 |
| S1.4 | last **3** closes beyond EMA-34 | 3 | zlr.py:90-98 |
| S3.3 | \|ΔCCI\| entry-bar ≥ **15** | 15 | zlr.py:102-105 |
| S3.7 | entry CCI ≤ **120** | 120 | zlr.py:107-111 |
| S3.4/8 | SWI not red at entry (\|swi\|≤20 ⇒ defer to 2nd bar) | 20 | zlr.py:113-118 |
| S3.5 | CZI with-direction **3/3** last bars | 3 | zlr.py:120-124 |

### S4 · GB100 (`gb100.py`)
| # | criterion | value | file:line |
|---|---|---|---|
| trend | `trend_state == BLUE` (LONG) / `RED` (SHORT) — **hard**; GRAY does not pass | — | gb100.py:91,147 |
| cross | `cur>100 AND prev≤100 AND prev2<100` — the cross must be **fresh (1 bar)** | 100 | gb100.py:91,147 |
| AP2 | YELLOW blocked always | — | anti_patterns.py:85-109 |
| AP6 | consecutive bars on opposite side of ZL ≤ **6** | 6 | gb100.py:69-79 |
| AP8 | as above | 3/50 | — |

### S4 · TT (`tt.py:80-145`) — BLUE/RED + CCI-side + TCCI touch(≤cci+5)/bounce(>cci+5, rising)/was-beyond(+10) + AP7 gap≥5.

### S4 system-level (woodies_system.py)
* `S4_EXTREME_TREND_RELABEL=1`: \|CCI\|≥**200** relabels GRAY/YELLOW→BLUE/RED (trend_relabel.py:15-30). 200 was never reached before 17:00 on 07-17 → GRAY held.
* P-W5 LOCK A: YELLOW drops ALL patterns (woodies_system.py:619-624).
* `HTLB_DIRECTION_GATE=1` (**ON**): a latched zoned-HTLB bias drops every opposite-direction S4 pattern (woodies_system.py:572-590); latch reset flag `HTLB_LATCH_RESET_V1=0` **OFF** → stale overnight bias possible at the open (audit 07-14).
* DLL-fallback: `zlr_detected=1` from the DLL fires a conf-0.65 ZLR **even when the Python detector rejects** (woodies_system.py:471-524) — see Finding F2.

### S2 · REACTIVE (`five_min_system.py:617-815`; B1=bars[-4]…B4=bars[-1])
| # | criterion | value | file:line |
|---|---|---|---|
| B1 | opposite-side drive close (sellers for LONG), vol>0 | — | :687,752 |
| B2 | volume gate, live variant **UNION** (config/s2_firing.yaml): VSA(`b2<b1 AND b2<b0 AND b2≤0.7×avg20`) OR RVOL(`b2≤0.5×avg20`) OR STRICT(VSA + range<0.7×ATR14). avg20 = last 20 **non-zero vols of the whole buffer** — includes overnight | 0.7/0.5 | :650-681 |
| B3 | with-direction close | — | :688,753 |
| B4 | with-direction close **AND close beyond B3's full extreme (100% of range)**; 75% only when S2_VOL_ADAPTIVE regime (avg14 range ≥ **8.0pt**) | 100%/75%/8.0 | :66-95,693,756 |
| CVD | (`S2_CVD_DETECTION_V1=1`) absorption/distribution on entry bar or divergence; **fail-open** if CVD stream missing | — | :726-794 |
| FHB | First-Hour Buffer 09:30-10:30 ET: count 1-3 nothing, **4**+ REACTIVE, **7**+ INITIATIVE, 13+/10:30 all | 4/7/13 | first_hour_buffer.py:26-79 |
| bypassed | lookback-quiet (VSA on), belly, COT/AMT (`S2_REQUIRE_COT_AMT=0`) | — | :694-708 |

### S2 · INITIATIVE (`five_min_system.py:817-934`)
B1 drive close + range in [**1.3×**, **2.5×**] avg14-range (VOLATILE: floor capped **8.0pt**) ·
B2 test = higher-low/lower-high OR POC-return ≤ **0.2×**avg-range · B3 joining range > **1.0×**B1
(0.8× VOLATILE) · B4 second test + close beyond B1 extreme · FHB ≥ 7 · CVD net-delta with-flow.

---

## 2. Findings (code-level, verifiable)

**F1 — Sierra paint is the single point of trend-blindness.** GB100/TT hard-require
BLUE/RED; ZLR S1.1 counts **paint-BLUE** bars, not CCI>0 bars. The Sierra study needs
~6 same-side bars to repaint (confirmed in code comment woodies_system.py:392 "audit: 6
bars confirmed"). So Woodies' own "6 bars beyond zero-line = trend" becomes, in
practice, **~6 CCI bars + ~6 paint-lag bars ≈ 1 hour** on 5-min — longer than the whole
07-17 rally. Doctrine (Woodies): trend is defined by *CCI vs the zero line*, the paint
is an implementation. Counting ZL-side bars directly is doctrine-faithful, not a relax.

**F2 — 17:35 DLL ZLR=UP did not route, and the code says it should have.**
`detect_all_patterns` returns only detected=True (pattern_engine.py:53-59), so a
SPEC_V2 rejection leaves "ZLR" out of `_dll_pattern_ids` → the DLL-fallback branch
(woodies_system.py:491-524) builds a conf-0.65 ZLR anyway. Non-route therefore
happened **downstream**: Mechanism-C dedup (:440-449), T3 stop-guard (:516,526),
HTLB latch drop (:572-590), YELLOW lock, dispatcher, or sizing-reject (no decisions-feed
entry is emitted for sizing="reject"). **Mac-side action:** grep the 17:30-17:40 backend
log for `ZLR-TRACE` / `Mechanism-C` / `HTLB dir-gate` / `V2 sizing` before relaxing
anything ZLR (Pre-LIVE: diagnose first).

**F3 — S2 B2 "quiet volume" is measured against an overnight-poisoned average.** The
rolling avg20 uses the last 20 non-zero volumes of the buffer; at 09:30-11:00 those are
mostly overnight bars with a fraction of RTH volume → `b2 ≤ 0.7×avg` is near-impossible
→ REACTIVE structurally cannot complete in the first ~100 RTH minutes. This is a
context bug, not doctrine: VSA "no-demand/no-supply" is defined vs *comparable* bars.
(Self-test reproduces: b2=2000 needs ≤700 because avg is warmup-1000.)

**F4 — FHB + fresh-cross interaction on gap days.** GB100's cross must be fresh (1
bar); on 07-17 the only fresh +100 cross of the rally printed at 16:55 — inside the
opening window, exactly where GRAY still holds (F1) and where item-10
(`OPENING_WINDOW_FIRE_V1=1`, ON) already declares with-drive opening signals
override-worthy. The doctrine hook for a bounded exception already exists in the stack.

**F5 — This evaluator found ZERO base fires possible on the synthetic gap-day shape**
(self-test): with live flags, no S4/S2 detector can pass all criteria during the first
third of a gap-and-drive rally. That matches the live evidence (fired 0 / blocked 0 —
nothing ever emitted).

---

## 3. The quantification tool — `scripts/audit_pattern_miss.py` (NEW, standalone)

Surfaces audit: `replay_day.py` (raw detector replay — KEEP), `decision_replay.py`
(gateway decisions — KEEP), `missed_trade_watch.py` (live gate supervision — KEEP).
None answers "*which single criterion failed and by how much per swing*" → new script
(ADAPTs replay_day's loading conventions; no backend imports so criteria are explicit
and annotated file:line).

What it does: loads `v9_bars_5min_woodies` (+`v9_bars_5min` for S2, honest fallback,
`v9_bars_cumulative_delta` fail-open) → zigzag swings ≥15pt → for each swing's first
third evaluates the FULL criteria vector of ZLR/GB100/TT/S2-REACTIVE/S2-INITIATIVE →
prints `swing → catchable-by → blocking-criterion → delta` (e.g. `blue_bars=5 need>=6
(d=1)`), BASE fire list, DLL-flag cross-check, and `--relax` runs (each of the 5 named
relaxations + ALL) reporting newly-caught swings and **added FALSE fires** (no ≥8pt
favorable move within 6 bars — both configurable).

**Verified in sandbox (Rule 5):** `python3 scripts/audit_pattern_miss.py --selftest` →
`SELFTEST PASS — swings=2; gb100_gray_open newly-catches; s2_b4_confirm_75 adds a
FALSE fire`. Market truth still needs the Mac (sandbox has no DB access).

**RUN ON THE MAC (paste + attach raw output to this doc):**
```bash
cd ~/mems26_web_git   # repo root, backend venv
python3 scripts/audit_pattern_miss.py --date 2026-07-17 --relax all --out docs/reports/PATTERN_MISS_RUN_2026-07-17.md
python3 scripts/audit_pattern_miss.py --date 2026-07-16 --relax all --out docs/reports/PATTERN_MISS_RUN_2026-07-16.md
python3 scripts/audit_pattern_miss.py --date 2026-07-15 --relax all --out docs/reports/PATTERN_MISS_RUN_2026-07-15.md
```
(07-15 caveat: S2 was dead all day from the le=3 schema bug — that day quantifies S4 only.)

---

## 4. RANKED proposals for Michael's ruling (all build flag-OFF; enabling any = trading-risk change → Michael sign-off)

Ranking = (expected catches this week × doctrine-safety) ÷ expected false-fire cost.
"Expected catches" below are reasoned from the documented micro-causes; the **numbers
come from the Mac run above** — do not rule on estimates alone (Rule 5).

| # | proposal | change (file:param) | doctrine call | expected catches (this week) | false-fire cost est. | flag (default-OFF) |
|---|---|---|---|---|---|---|
| **0** | **Diagnose F2 first** — why 17:35 DLL-ZLR didn't route | log-chase, no code | n/a — Pre-LIVE "diagnose first, fix second" | explains 07-17 17:35; may make #3 unnecessary | none | (task for cc-imac, not a flag) |
| **1** | GB100 may fire on GRAY (never YELLOW) inside the opening window (first 6 RTH bars) | `gb100.py:91,147` + rth-index guard | **Calibration with doctrine cover**: Dalton gap-&-go = opening drive IS the trend; item-10 (ON) already encodes "with-drive opening overrides refusals". Woodies purist objection: trend not yet established — bounded to 30 min | 07-17 16:55 fresh +100 cross → rally continued ~+40pt | LOW: needs a fresh ±100 cross in first 30min + AP6/AP8 still on; script quantifies | `GB100_GRAY_OPENING_V1` |
| **2** | S2 B2 volume average = RTH-session-only (or time-of-day RVOL) instead of buffer-last-20 | `five_min_system.py:658-659` (`_vol_buf`) | **Bug-fix, not relax**: VSA quiet is vs comparable bars; comparing RTH to overnight is category error (F3) | unblocks REACTIVE first ~100min all week; 07-16/07-17 B1-B4 completions | NET-NEGATIVE possible (it *tightens* when overnight avg was inflating passes); script quantifies both directions | `S2_RVOL_SESSION_V1` |
| **3** | ZLR S1.1 count 6→3, and count **CCI>0-side bars** not paint-BLUE | `zlr.py:75-82` param | S1.1 is **Michael's own spec knob**, not Woodies core; counting ZL-side bars is *more* Woodies-faithful than paint (F1). 6 paint-bars ≈ 12 doctrine-bars | 07-17 17:35 had blue=5 (d=1) → caught; likely earlier bars too | LOW-MED: rest of SPEC_V2 (SWI/CZI/EMA/≤120) still gates | `ZLR_S11_BLUE_MIN` (param, default 6) + `ZLR_S11_COUNT_ZL_SIDE_V1` |
| **4** | REACTIVE B4-confirm 100%→75% of B3 range in ALL regimes | `five_min_system.py:88-95` (`_VOL_CONFIRM_FRACTION` scope) | Calibration: the 75% rule already exists and is doctrine-accepted in VOLATILE; 06-12 audit showed 100% failed 18/18 | S2 sequences "tracked but never completed" 07-16/17 | MED: more marginal completions everywhere; script's false-fire count is the ruling input | `S2_B4_CONFIRM_FRAC` (param, default 1.0) |
| **5** | ZLR extreme window 12→20 bars (base + AP1 together) | `zlr.py:32` + `anti_patterns.py:70` | Calibration: 12 bars=1h is DLL-matching convention; Woodies bounds pullback by *shape* (not beyond −100), not by a wall-clock | late-pullback ZLRs after long drives (07-16 19:40 cluster context) | MED: AP1 exists to kill stale hooks; expect some stale adds — quantify | `ZLR_EXTREME_WINDOW` (param, default 12) |
| **6** | FHB halved: REACTIVE from count 2, INITIATIVE from 4 | `first_hour_buffer.py:69-79` | House risk-discipline, not Dalton; Dalton: the open often gives the day's best location. Aligned with item-10 being ON | 07-17 16:45-17:05 S2 window opens ~10-25 min earlier | MED on rotation opens (first bars are noisiest) — quantify per day | `S2_FHB_FAST_V1` |
| **7** | Extreme-trend relabel threshold 200→150 with 2-bar persistence (affects ZLR S1.1/GB100/TT trend source) | `trend_relabel.py:29` param | Extension of an already-ruled mechanism (S4_EXTREME_TREND_RELABEL ON since SHADOW); \|CCI\|≥150 for 2 bars = strong initiative per Woodies | 07-17 CCI ran 130-190 through the rally → BLUE by ~17:00 → GB100/TT eligible | MED-HIGH: relabel feeds every trend consumer incl. CONT_TREND_STATE_CERT — needs shadow A/B first | `TREND_RELABEL_150_V1` |

**Not proposed:** HFE re-enable (Michael's standing ruling — not his pattern);
touching S3/COT-AMT (standing OFF); any gateway-gate relaxation (nothing reached the
gates this week — the problem is not there).

**Interaction warning:** #1+#7 overlap (both give GB100 a trend source earlier) — if
both are ruled in, enable one first, A/B in shadow, then decide. #3's two sub-flags are
independently rulable.

---

## 5. What is honestly NOT quantified yet (needs the Mac)

* The per-swing near-miss deltas and per-relaxation newly-caught / FALSE-fire counts
  for 07-15/16/17 — the sandbox cannot reach local Postgres; run §3 commands.
* F2's actual root cause (log-only).
* Whether `v9_bars_5min` was gapped this week (script reports its source fallback).
* HTLB latch state during 07-17 RTH (`HTLB_DIRECTION_GATE=1` + reset flag OFF —
  if a stale DOWN bias was latched, it silently dropped every LONG S4 pattern all
  morning; check `[Woodies] HTLB dir-gate` lines in the backend log).

*Sources read for this audit: zlr.py, gb100.py, tt.py, anti_patterns.py,
pattern_engine.py, woodies_system.py, trend_relabel.py, five_min_system.py,
first_hour_buffer.py, session_classifier.py, FLAG_INDEX.md, SOURCE_OF_TRUTH.md,
config/s2_firing.yaml. Flag states per docs/FLAG_INDEX.md as of 2026-07-17.*
