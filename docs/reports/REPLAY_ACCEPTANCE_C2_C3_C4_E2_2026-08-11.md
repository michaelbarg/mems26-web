# REPLAY ACCEPTANCE — C2 / C3 / C4 / E2 (2026-08-11)

**Agent:** replay-agent (Cowork) · **Mode:** READ-ONLY (no flag enabled, no backend
restart, no write to `~/SierraChart_Data`, no DB write — a LIVE session was running).
**Script:** `scripts/replay_c2_c3_c4_e2.py` (`--part all`) · raw output pasted per section.
**Data:** `v9_bars_5min_woodies` RTH (09:30–16:15 ET) + `v9_trades` + `v9_day_type_history`
+ `docs/reports/OPS_LOG_*.md` gateway lines. `.env` loaded via `flag_guard.parse_env`
(mandatory — without it the classifier mislabels days).

**Window:** 2026-07-15 … 2026-08-10 → **19 sessions with RTH bars**
(07-15, 07-16, 07-17, 07-20, 07-21, 07-22, 07-23, 07-24, 07-27, 07-28, 07-29, 07-30,
07-31, 08-03, 08-04, 08-05, 08-06, 08-07, 08-10).
All 19 start at 09:30 ET (IB valid). Four have truncated tails / a gap
(07-15 → 14:25 · 07-16 → 14:50 · 07-22 gap 11:05–…, → 15:10 · 07-28 → 15:30 ·
**08-04 → 12:50**), so late-session MTM on those days is measured early.

---

## 🏁 VERDICT TABLE

| Flag | metric | NET | n | verdict | recommended env |
|---|---|---|---|---|---|
| **C2 `RE_PULLBACK_ENTRY_V1`** | simulated 2c | **−$77.60** | 21 triggers / 19 days | **NO-GO (keep OFF)** | `RE_PULLBACK_ENTRY_V1=0` |
| **C3 `extreme_chase_guard` calibration** | blended (measured where traded) | **−$1,308.75** vs **−$2,286.25** live default → **+$977.50** | 195 candidates | **GO — but only the scope+maturity levers** | `EXTREME_CHASE_SCOPE=CONT+REV` · `CHASE_MIN_SESSION_BARS=10` · `EXTREME_MIN_DIST_PTS=6.0` (unchanged) · `CHASE_IB_FRAC=0.30` (unchanged) |
| **C4 `NEUTRAL_PLAYBOOK_V1`** | simulated 2c | **−$28.75** (08-10 alone **+$43.75**) | 7 triggers / **3 neutral days** | **DEFER (n too small)** | keep `NEUTRAL_PLAYBOOK_V1=0`, shadow-log 2 more neutral days |
| **E2 `S6_TREND_BE_DELAY_V1`** | measured runner delta | **−$55.00** (08-03+08-04 only: **+$42.50**) | 16 resolved Trend trades (4 BE-clipped) | **DEFER / NO-GO as built** | keep `S6_TREND_BE_DELAY_V1=0` |

**Only C3 is a GO — and not the lever that was proposed.** Relaxing the *distance*
threshold (the "19pt left on the table" fix) is NET-negative on every setting tried;
the money is in the *scope* (`CONT+REV`) plus the *session-maturity* bypass.

---

## C2 — `RE_PULLBACK_ENTRY_V1` → **NO-GO**

Method: walk every bar from IB-lock (`session_min ≥ 60`) through
`backend/v9/systems/five_min/patterns/pullback_retest.detect_pullback_retest`
with the real IB (first 12 RTH bars). Cooldown 6 bars, max 2/day. 2-contract sim
(C1→T1, C2→T2, stop→BE after T1, stop assumed hit before target inside a bar).

```
── C2 RE_PULLBACK_ENTRY_V1 ──
n triggers = 21   NET = -$77.60
date       time   dir       entry     stop       t1       t2    rr       outcome      pnl$
2026-07-15 12:10  SHORT   7587.75  7594.25  7578.12  7564.50  1.48          STOP    -65.00
2026-07-16 12:00  SHORT   7595.25  7600.00  7590.38  7582.25  1.03         T1+BE     24.35
2026-07-16 12:30  SHORT   7589.75  7598.75  7590.38  7582.25  0.07         T1+T2     34.35
2026-07-17 12:05  LONG    7535.50  7528.75  7548.25  7562.75  1.89          STOP    -67.50
2026-07-17 13:40  SHORT   7497.25  7505.00  7490.25  7475.75  0.90          STOP    -77.50
2026-07-20 12:35  SHORT   7504.00  7510.75  7482.88  7459.75  3.13          STOP    -67.50
2026-07-20 13:30  SHORT   7500.00  7510.00  7482.88  7459.75  1.71        T1+MTM    168.10
2026-07-21 12:20  LONG    7547.50  7544.00  7555.50  7567.00  2.29          STOP    -35.00
2026-07-21 13:35  LONG    7544.50  7541.00  7555.50  7567.00  3.14          STOP    -35.00
2026-07-23 11:45  SHORT   7440.25  7451.25  7423.88  7403.00  1.49          STOP   -110.00
2026-07-23 12:30  SHORT   7441.00  7449.75  7423.88  7403.00  1.96         T1+BE     85.60
2026-07-27 11:30  SHORT   7432.25  7443.00  7402.12  7364.75  2.80          STOP   -107.50
2026-07-28 14:00  LONG    7477.00  7470.75  7506.62  7536.50  4.74          STOP    -62.50
2026-07-28 15:00  LONG    7477.00  7470.75  7506.62  7536.50  4.74          STOP    -62.50
2026-07-29 12:30  SHORT   7389.75  7400.25  7366.88  7335.50  2.18          STOP   -105.00
2026-07-29 15:30  SHORT   7389.75  7412.50  7366.88  7335.50  1.01         T1+T2    385.60
2026-07-30 13:40  LONG    7453.25  7445.75  7469.88  7493.25  2.22        T1+MTM    253.15
2026-08-05 10:50  SHORT   7783.25  7802.00  7782.00  7769.25  0.07         T1+BE      6.25
2026-08-06 11:40  SHORT   7733.00  7740.25  7726.12  7712.00  0.95          STOP    -72.50
2026-08-06 12:40  SHORT   7730.25  7740.25  7726.12  7712.00  0.41          STOP   -100.00
2026-08-07 11:45  LONG    7783.25  7776.50  7799.12  7817.75  2.35          STOP    -67.50
ACCEPTANCE 2026-08-10 ~7791.25 : FAIL (no trigger)
ACCEPTANCE 2026-08-07 10:45/10:55: FAIL (no trigger)
```

**Both acceptance cases FAIL — and in both cases the module is right and the
premise was wrong:**

* **2026-08-10 ~7791.25.** IB = 7791.25 / 7771.00 (width 20.25, `min_break` = 3.04).
  The only qualifying break is 10:45 (h 7797.00, c 7795.50). The retest rule needs a
  later bar that **closes back above 7791.25**. Raw bars: 10:50 c 7785.25 · 10:55 c
  7781.50 · 11:00 c 7783.75 · 11:05 c 7782.00 · … the market never reclaimed the edge —
  it kept going to 7778. A LONG @7791.25 would have been an immediate ~13pt loser.
  The Dalton report's "would have given LONG @7791.25 / targets 7801-7811" is a
  hypothesis the bars do not support. **Module correctly declines.**
* **2026-08-07 10:45 + 10:55** (`ZLR LONG @7771.25` / `@7770.25`, blocked by
  `awaiting_release`). At those bars the session high was 7781.25 against IBH 7780.50 —
  a 0.75pt penetration vs the 5.59pt `min_break`. **The IB was never broken**, so these
  are not "retests of a broken edge" at all; they were mid-IB longs. C2 cannot and
  should not capture them. Their block is a **release-gate** question, not a C2 gap.

**Distribution:** 6 wins / 15 losses, NET −$77.60 over 19 sessions ≈ −$4/day. Two
outliers (07-29 +$385.60, 07-30 +$253.15) carry the whole positive side; remove them
and the flag is −$716. Also note `RETEST_TOL_PT = 1.5` and the "close beyond the edge"
rule together mean it fires mostly on *shallow* retests that are still inside the
prior swing — 15 of 21 hit the stop.

**Verdict: NO-GO. Keep `RE_PULLBACK_ENTRY_V1=0`.** Not a regression — the module works
as specified; the specification does not pay on this data set. If it is revisited,
extend it to **POC / VA-edge** retests (the workorder's actual wording) rather than
IB-only, and re-replay.

---

## C3 — `extreme_chase_guard` calibration → **GO (scope + maturity only)**

**Universe (195 candidates):** 46 entries the guard actually blocked live
(parsed from `docs/reports/OPS_LOG_*.md`, deduped to one per 5-min bar) + 149 trades
that actually fired (`v9_trades`, live preferred over shadow, deduped).

**Two metrics, both reported:**
* `net_sim` — every candidate re-simulated with one uniform model (structure stop from
  the last 3 bars clamped to 3–12pt, T1 = 1R, T2 = 2R, 2 contracts, BE after T1).
  Apples-to-apples across settings, but crude.
* `net_blend` — **measured** `pnl_usd` for candidates that really traded; simulated
  only for the counterfactual (entries the guard actually blocked). This is the
  metric to trust.

The guard is re-implemented faithfully (scope/family, `max(EXTREME_MIN_DIST_PTS,
CHASE_IB_FRAC × ib_width)`, `CHASE_MIN_SESSION_BARS` maturity bypass,
`release_gate.trend_bypass`, K3d tip-revocation, 3-bar pullback check).
**Not modelled:** `_live_leg` (LEG_RIDE) — live-only state. Consequence: the replay
blocks a few entries live let through; see the caveat below.

### Distance sweep (the proposed lever) — every setting is NET-negative

```
LIVE default (CONT, base 6.0, frac 0.30, min_bars 6): n_pass=101 net_sim=-$1,053.75 net_blend=-$2,286.25

scope       base  frac  pass  block    net_sim$   net_blend$  acceptance(b0807/b0810/a7777/a7778)
CONT         3.0  0.30   101     94    -1053.75     -2286.25  Y/n/n/n
CONT         4.0  0.20   118     77    -2916.25     -3471.25  Y/n/Y/Y
CONT         5.0  0.20   117     78    -2866.25     -3421.25  Y/n/Y/Y
CONT         6.0  0.30   101     94    -1053.75     -2286.25  Y/n/n/n
CONT+REV     3.0  0.20   102     93    -2008.75     -2841.25  Y/Y/Y/Y  <== ALL PASS
CONT+REV     4.0  0.00   155     40    -2876.25     -4145.00  Y/Y/Y/Y  <== ALL PASS
CONT+REV     4.0  0.20   102     93    -2008.75     -2841.25  Y/Y/Y/Y  <== ALL PASS
CONT+REV     5.0  0.20   101     94    -1958.75     -2791.25  Y/Y/Y/Y  <== ALL PASS
CONT+REV     6.0  0.30    80    115     -625.00     -2092.50  Y/Y/n/n
```
(full 40-row grid in the script output; the rows above are the informative ones.)

To let the 2026-08-10 longs through on **distance** you must drop `min_dist` to ≤5.0
(their distances were 5.50 / 5.00 from a session high that was 5 bars old). Doing that
costs **−$1,383.75 sim / −$748.75 blend** versus simply tightening the scope. **The
distance lever is a NO-GO.**

### Maturity sweep (`CHASE_MIN_SESSION_BARS`, distance left at 6.0/0.30) — this is where the money is

```
scope      min_bars  pass  block    net_sim$   net_blend$  acceptance(b0807/b0810/a7777/a7778)
CONT              6   101     94    -1053.75     -2286.25  Y/n/n/n    <-- LIVE TODAY
CONT             10   109     86      -60.00     -1390.00  Y/n/Y/Y
CONT+REV          6    80    115     -625.00     -2092.50  Y/Y/n/n
CONT+REV          7    86    109      -93.75     -2151.25  Y/Y/Y/Y  <== ALL PASS
CONT+REV          8    87    108       97.50     -1960.00  Y/Y/Y/Y  <== ALL PASS
CONT+REV          9    90    105      416.25     -1443.75  Y/Y/Y/Y  <== ALL PASS
CONT+REV         10    92    103      581.25     -1308.75  Y/Y/Y/Y  <== ALL PASS
CONT+REV         12    94    101      381.25     -1336.25  Y/Y/Y/Y  <== ALL PASS
```

**Best all-acceptance-passing setting: `CONT+REV` + `CHASE_MIN_SESSION_BARS=10`**
→ `net_sim` **+$581.25** (vs −$1,053.75 live → **+$1,635.00**),
`net_blend` **−$1,308.75** (vs −$2,286.25 live → **+$977.50**).
Both metrics agree on direction and on the ranking — that is the reason to act.

### Acceptance cases — all four PASS at the recommended setting

```
  block_0807_zlr_7783.75   2026-08-07 11:40 ZLR                   fam=CONT   dist=  3.00 ib_w= 37.25 bars_since_extreme= 3 sim_pnl=  -77.50 actual=-86.25
  block_0810_655_7795      2026-08-10 10:45 ZLR                   fam=CONT   dist=  2.00 ib_w= 20.25 bars_since_extreme= 0 sim_pnl=  -72.50 actual=None
  block_0810_655_7795      2026-08-10 10:45 DOUBLE_BOTTOM_EE_LONG fam=REV    dist=  2.00 ib_w= 20.25 bars_since_extreme= 0 sim_pnl=  -72.50 actual=-63.75
  allow_0810_7777.75       2026-08-10 09:55 ZLR                   fam=CONT   dist=  5.50 ib_w= 20.25 bars_since_extreme= 5 sim_pnl=  108.75 actual=None
  allow_0810_7778.25       2026-08-10 09:55 ZLR                   fam=CONT   dist=  5.00 ib_w= 20.25 bars_since_extreme= 5 sim_pnl=  116.25 actual=None
```

* `#655` (`DOUBLE_BOTTOM_EE_LONG`, **REV family**) fired live only because the guard's
  scope was `CONT`. The identical `ZLR LONG @7795` on the same bar **was** blocked.
  `EXTREME_CHASE_SCOPE=CONT+REV` closes exactly that hole (−$63.75 saved on the day).
* The 08-10 09:55 longs are 6 bars into the session against a **5-bar-old** high
  (the 09:30 bar). The maturity bypass — "an extreme of a 30-minute session is not an
  extreme" (Michael 07-30 doctrine) — is the correct instrument, not a lower threshold.

### Decisive candidate sets

* **Newly blocked by `CONT+REV` (n=17):** `net_sim` −$641.25 but **measured `pnl_usd`
  sums to +$47.50.** Honest caveat: on the REV entries that actually traded, the scope
  extension is roughly break-even, not a big saver — its value in the blend comes from
  the counterfactual REV entries plus #655. Do not oversell this arm.
* **Newly allowed by `min_bars 6→10` (n=8, `net_sim` +$993.75):** 5 were genuinely
  blocked live (07-27 10:00 + 10:05 `INITIATIVE_SHORT` @7473.75, 07-29 09:55 @7434.25,
  08-10 09:55 @7778.25 + @7777.75) worth **+$738.75 simulated**; the other 3 fired live
  anyway (my replay over-blocks them because `_live_leg` is not modelled), and their
  measured P&L is +$157.50. Both subsets point the same way.

### Verdict

**GO** on `EXTREME_CHASE_SCOPE=CONT+REV` and `CHASE_MIN_SESSION_BARS=10`
(8–12 are all positive on `net_sim`; **12** = exactly IB-lock and is the doctrinally
cleanest choice, within noise of 10). **NO-GO** on lowering `EXTREME_MIN_DIST_PTS` or
`CHASE_IB_FRAC` — keep 6.0 / 0.30.

**Caution for Michael:** `min_bars=10` means the chase guard is **inert for the first
50 minutes** of RTH. That window is covered by `COLD_START_GUARD_V1`,
`OPENING_WINDOW_FIRE_V1` and first-trade-strict, but it is a real widening of the
opening risk surface, and the delta rests on ~12 candidates. If that is too much,
`CHASE_MIN_SESSION_BARS=8` (40 min) still passes all four acceptance cases and is
still better than today (`net_sim` +$97.50 / `net_blend` −$1,960.00).

---

## C4 — `NEUTRAL_PLAYBOOK_V1` → **DEFER (n too small)**

Method: only days whose `v9_day_type_history` label starts with `Neutral`
(3 in the window: **07-29 Neutral_Extreme, 08-06 Neutral_Center, 08-10 Neutral_Center**).
Developing profile (POC/VAH/VAL, 70% VA, volume spread across each 5-min bar's range,
**no look-ahead**) recomputed each bar. Entry only on an **edge rejection** (bar tags
VAH/VAL and closes back inside). **T1 = POC · T2 = opposite edge · stop beyond the
session extreme (EXCESS tail) +1.0pt · 2 contracts · 12-bar time-stop.** Wrong-side
targets are skipped (A1 doctrine). Cooldown 6 bars, max 3/day.

```
── C4 NEUTRAL_PLAYBOOK_V1 ──
neutral days in window: {'2026-08-10': 'Neutral_Center', '2026-07-29': 'Neutral_Extreme', '2026-08-06': 'Neutral_Center'}
n triggers = 7   NET = -$28.75
date       time   dir       entry     stop   T1=POC  T2=edge    rr       outcome      pnl$
2026-07-29 10:40  LONG    7398.00  7392.25  7409.25  7439.50  1.96         T1+BE     56.25
2026-07-29 11:40  LONG    7395.75  7392.00  7403.75  7432.00  2.13          STOP    -37.50
2026-08-06 11:10  LONG    7749.50  7739.25  7756.00  7762.25  0.63          STOP   -102.50
2026-08-06 13:30  LONG    7730.50  7723.25  7732.75  7755.50  0.31         T1+BE     11.25
2026-08-10 10:35  SHORT   7790.00  7794.50  7789.25  7776.25  0.17          STOP    -45.00
2026-08-10 11:55  SHORT   7789.75  7798.00  7784.75  7778.00  0.61         T1+T2     83.75
2026-08-10 14:30  LONG    7772.00  7762.75  7773.00  7786.25  0.11         T1+BE      5.00
actual P&L on those days (live if any, else shadow): {'2026-08-10': -63.75, '2026-07-29': 0, '2026-08-06': -63.75}
ACCEPTANCE 2026-08-10 (Neutral_Center): n=3 NET=+$43.75 (actual that day -63.75)
```

**Acceptance day 2026-08-10 PASSES directionally**: +$43.75 replayed vs **−$63.75
actually lost** → a **+$107.50** swing on the acceptance day, and it does it with
edges-only entries (10:35 / 11:55 shorts from the upper edge, 14:30 long from the
lower edge) instead of the 10:46 chase at the session high.

**But the flag is NET −$28.75 over the whole window, on n=7 trades across 3 days.**
That is inside noise. Structural weakness visible in the table: **R:R to T1 is
0.11–0.63 on 4 of 7 trades** — when POC sits 1–2pt from the edge, "T1 = POC" is not a
target, and the stop-beyond-the-tail is 4–10pt away. The playbook needs a minimum
POC-distance / R:R floor before it can be trusted.

**Verdict: DEFER.** Keep `NEUTRAL_PLAYBOOK_V1=0`. Same class as the 08-09
`EXCESS n=4 DEFER` call. Recommended next step: **shadow-log** the playbook on the
next 2–3 neutral days and add an `R:R ≥ 0.8 to POC` precondition, then re-rule.

---

## E2 — `S6_TREND_BE_DELAY_V1` → **DEFER / NO-GO as built**

Method: every trade with `day_type_at_entry LIKE 'Trend%'` that reached T1
(n=19; 3 excluded because no exit was ever recorded → the *actual* runner is
unmeasurable: ids 582, 595, 620). For each, the **runner (1 contract)** is compared:
* **actual** — T2 if `t2_hit_ts`, else the recorded `exit_price` (`BE` when it is
  within 0.25pt of entry).
* **E2 alternative** — no BE move; stop = structure trail behind the last 2 closed bars
  (never widens); **the T2 target is left intact** (it is an attached OCO — E2 only
  changes the stop).

```
   id date       time   mode   dir   pattern                  actual_run       tag  alt_run     alt_tag    delta$
  378 2026-07-15 11:57  shadow SHORT GB100                         14.50        T2     2.75  TRAIL_STOP    -58.75
  379 2026-07-15 11:57  live   SHORT GB100                         10.50        T2     2.75  TRAIL_STOP    -38.75
  580 2026-07-31 10:05  shadow SHORT INITIATIVE_SHORT              23.50        T2    23.50          T2      0.00
  581 2026-07-31 10:05  live   SHORT INITIATIVE_SHORT              23.50        T2    23.50          T2      0.00
  592 2026-08-03 10:10  shadow LONG  REACTIVE_LONG                  9.00        T2     9.00          T2      0.00
  593 2026-08-03 10:10  live   LONG  REACTIVE_LONG                  9.00        T2     9.00          T2      0.00
  594 2026-08-03 10:36  shadow LONG  ZLR                            0.00        BE     6.50          T2     32.50
  596 2026-08-03 10:40  shadow LONG  ZLR                            0.00        BE     0.75  TRAIL_STOP      3.75
  597 2026-08-03 10:51  shadow LONG  ZLR                            0.00        BE     8.25          T2     41.25
  611 2026-08-04 10:05  shadow LONG  REACTIVE_LONG                 11.25        T2    11.25          T2      0.00
  612 2026-08-04 10:05  live   LONG  REACTIVE_LONG                 11.25        T2    11.25          T2      0.00
  613 2026-08-04 10:15  shadow LONG  INITIATIVE_LONG                0.25        BE    -6.75  TRAIL_STOP    -35.00
  614 2026-08-04 10:35  shadow LONG  REACTIVE_LONG                 14.50        T2    14.50          T2      0.00
  615 2026-08-04 10:35  live   LONG  REACTIVE_LONG                 13.25        T2    13.25          T2      0.00
  616 2026-08-04 10:35  shadow LONG  ZLR                           14.00        T2    14.00          T2      0.00
  619 2026-08-04 11:38  shadow LONG  ZLR                           10.50        T2    10.50          T2      0.00
excluded (no recorded exit, actual unmeasurable): n=3 ids=[582, 595, 620]
TOTAL delta (resolved n=16)   = -$55.00
TOTAL delta (live only n=5) = -$38.75
TOTAL delta (BE-clipped n=4)  = +$42.50
  2026-08-03: n=5 delta=+$77.50
  2026-08-04: n=7 delta=-$35.00
ACCEPTANCE 08-03+08-04: n=12 delta=+$42.50
```

**Findings:**
1. **The acceptance days do pay, barely: 08-03 + 08-04 = +$42.50** — and *all* of it
   comes from 3 shadow ZLR longs on 08-03 that BE clipped to exactly $0 (594, 596, 597).
   That is consistent with cc's "−$72.50 measured" order of magnitude, not identical
   (cc counted the T1 leg; this replay isolates the runner leg).
2. **Over the whole window it is −$55.00.** The single trade that decides the sign is
   **07-15 GB100 SHORT (378/379)**: with BE it ran to T2 (+14.50 / +10.50pt); with the
   structure trail it was stopped at +2.75pt → **−$97.50 combined**. On a trend day the
   2-bar structure trail is *tighter* than BE once the move accelerates.
3. **The population the flag actually touches is 4 trades** (`BE-clipped`), 3 of them
   shadow-only, on 2 days. n is far too small to rule on.
4. Only **5 of 16** are live rows and they total **−$38.75**.

**Verdict: DEFER (NO-GO as currently built).** Keep `S6_TREND_BE_DELAY_V1=0`.
The finding is real (BE at exactly $0 on three 08-03 ZLR runners) but the proposed
replacement — hand the runner to a 2-bar structure trail — **loses more on the trades
where BE worked than it gains on the trades where BE hurt**. Proposed fix before
re-ruling: delay BE by a *condition*, not remove it — e.g. move to BE only after
price advances ≥ 1.0R **beyond** T1, keeping the original stop until then. That is
a different implementation than what is in `manager.py` today.

---

## Method caveats (Rule 5 honesty)

1. **Uniform simulator.** C2/C3/C4 use one 2-contract model (C1→T1, C2→T2, BE after
   T1, stop assumed hit before target within the same bar → conservative). It does not
   model MAE-scratch, per-contract dynamic management, TP-1, target-realism, slippage
   or commission. Absolute NET figures are therefore indicative; **the ranking between
   settings (C3) is the reliable output.**
2. **C3 blend.** `net_blend` mixes measured `pnl_usd` (149 fired candidates) with
   simulated P&L (46 counterfactual blocked candidates). No way around it — the blocked
   entries never traded.
3. **`_live_leg` (LEG_RIDE) is not modelled** in the C3 guard replay, so the replay
   blocks a handful of entries the live gateway allowed. Quantified above (3 candidates,
   measured +$157.50) and it does not change the ranking.
4. **Truncated bar days** (07-15, 07-16, 07-22, 07-28, and especially **08-04 which
   ends at 12:50 ET**) mean any MTM/trail exit after those times is measured at an
   artificially early session end. This affects C2 (07-15/16, 07-28) and E2 (08-04).
5. Day labels for C4 come from `v9_day_type_history` (the recorded label per date),
   not from a bar-by-bar intraday replay of the classifier.
6. **Nothing was enabled.** No `.env` edit, no backend restart, no DB write, no
   `~/SierraChart_Data` write. Reproduce with:
   `python3 scripts/replay_c2_c3_c4_e2.py --part all`
