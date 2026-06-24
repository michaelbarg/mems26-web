# Trades Today — 2026-06-22 (Central Time) — SHADOW mode

**Source:** local Postgres `mems26` — `v9_trades`, `v9_trade_management_log`,
`v9_bars_5min_woodies`, `v9_bars_5min`, `v9_day_type_state`.
**Analysis cut at:** 2026-06-22 **10:21:45 CT** (session still LIVE — last 5-min bar = 10:20 CT).
All timestamps converted `(ts AT TIME ZONE 'America/Chicago')`. PnL model = 3-contract
MES @ $5/pt; `pnl_r` normalized to `3 × initial_risk_per_contract`.

---

## CORRECTIONS to the briefing (verified against DB)

1. **There are 11 fires today, not 8.** The brief listed 8 (ids 188,190,191,193,194,195,196,197).
   Three MORE fired at **10:20 CT** and are still open: **199** (S2 REACTIVE_SHORT), **200** (S2
   REACTIVE_SHORT — duplicate of 199), **201** (S4 ZLR).
2. **The bar tables did NOT stall at 08:55.** Both `v9_bars_5min` (32 rows today, max 10:20 CT)
   and `v9_bars_5min_woodies` (115 rows, max 10:20 CT) are current as of 10:20 CT. The session is
   live; this is a mid-session snapshot, not an end-of-day post-mortem.
3. **`day_type_at_entry` IS stamped** on every trade (Nontrend for the early S4 batch, Variation
   for the 09:40+ batch). What is `None` is the **nested** copy inside `quality.day_type` and inside
   `cross_context[...].day_type` — a stamping gap in the quality/context payload, not the column.
4. Trade 197 (10:10 REACTIVE_SHORT) is **open/FILLED**, never hit T1, and is currently **underwater**
   (last close 7542.25 vs entry 7538.50 = −3.75 pts against the short).

---

## 1. Per-trade table

Prices in MES points. "Loc vs IB" uses IB = **7560.50 – 7599.25**, POC ≈ **7532**, session range so far
**7527.25 – 7599.25**. Risk = |entry − initial stop|.

| # | id | Time CT | Sys | Pattern | Dir | Entry | Loc vs IB | Init.Stop | Risk | T1 | T2 | T3 | Exit | Reason | PnL $ | R | Outcome |
|---|----|---------|-----|---------|-----|-------|-----------|-----------|------|----|----|----|------|--------|-------|---|---------|
| 1 | 188 | 08:30:02 | S4 | TLB | SHORT | 7572.50 | mid-IB | 7579.75 | 7.25 | 7567.06 | 7558.00 | — | 7579.75 | STOP_HIT | **−108.75** | −1.0 | LOSS |
| 2 | 190 | 08:35:07 | S4 | TLB | SHORT | 7577.50 | mid-IB | 7591.00 | 13.50 | 7568.73 | 7550.50 | — | 7591.00 | STOP_HIT | **−202.50** | −1.0 | LOSS |
| 3 | 191 | 08:50:05 | S4 | HFE | SHORT | 7591.50 | upper-IB | 7597.50 | 1.50* | 7586.70 | 7582.50 | — | 7590.00 | STOP_HIT (post-T1 trail) | **+39.00** | +0.43 | WIN |
| 4 | 193 | 08:55:09 | S4 | HFE | SHORT | 7586.00 | upper-IB | 7597.50 | 11.50 | 7579.10 | 7568.75 | — | 7597.50 | STOP_HIT | **−172.50** | −1.0 | LOSS |
| 5 | 194 | 09:05:01 | S4 | HFE | SHORT | 7593.50 | top-IB | 7598.25 | 4.75 | 7589.70 | 7586.38 | — | 7598.25 | STOP_HIT | **−71.25** | −1.0 | LOSS |
| 6 | 195 | 09:40:00 | S2 | INITIATIVE_SHORT | SHORT | 7551.00 | below-IB | 7556.50 | 5.50 | 7541.13 | 7521.75 | 7502.38 | 7546.50 | STOP_HIT (post-T1 trail) | **+94.38** | +1.14 | WIN |
| 7 | 196 | 09:45:00 | S2 | INITIATIVE_SHORT | SHORT | 7550.50 | below-IB | 7554.00 | 3.50 | 7541.13 | 7521.75 | 7502.38 | 7541.00 | STOP_HIT (post-T1 trail) | **+141.88** | +2.70 | WIN |
| 7 | 197 | 10:10:08 | S2 | REACTIVE_SHORT (B_RVOL) | SHORT | 7538.50 | far-below-IB | 7547.75 | 9.25 | 7531.56 | 7520.00 | — | — | OPEN | — | — | **OPEN** |
| 8 | 199 | 10:20:03 | S2 | REACTIVE_SHORT (B_RVOL) | SHORT | 7537.75 | far-below-IB | 7546.25 | 8.50 | 7531.38 | 7520.75 | — | — | OPEN | — | — | **OPEN** |
| 9 | 200 | 10:20:05 | S2 | REACTIVE_SHORT (B_RVOL) | SHORT | 7537.75 | far-below-IB | 7546.25 | 8.50 | 7531.38 | 7520.75 | — | — | OPEN | — | — | **OPEN (dup of 199)** |
| 10| 201 | 10:20:05 | S4 | ZLR | SHORT | 7538.00 | far-below-IB | 7547.75 | 9.75 | 7530.69 | 7518.50 | — | — | OPEN | — | — | **OPEN** |

\* Trade 191 risk note: `metadata.stop_initial = 7597.50` (risk 6.0) but the **stored** `stop`
column at fire = 7590.00 (1.5). The trail history (HWM 7584 → stop ratcheted 7591.25→7590.0)
shows the SMART_BE/TRAIL had already pulled the effective stop to 7590.0 by the time it was hit.
pnl_r=0.43 is normalized off the 6.0-pt initial risk.

**Realized totals (closed trades only):** 6 closed → 2 wins / 4 losses.
−108.75 −202.50 +39.00 −172.50 −71.25 +94.38 +141.88 = **−$279.74 net** on the 7 closed.
4 trades still open (197, 199, 200, 201), all shorts, all currently small-underwater.

---

## 2. Per-trade narrative (entry → management → exit)

### Trade 188 — 08:30 S4 TLB SHORT @7572.50 → LOSS −$108.75 (−1.0R)
- **Entry/location:** Mid-IB (IB at this point was still forming, TPO `ib_low=7554 ib_high=7563.75 NARROW`).
  Shorting into a BLUE (up) trend bar — the 08:30 bar ran 7573→**7590.25 high**→7578 close. The fire was
  caught on the way up.
- **Plan:** stop 7579.75 (7.25 risk), T1 7567.06, T2 7558. Half size.
- **Management:** none — single management event = STOP_HIT. Price never went in favor (MFE only 1.0 pt;
  lowest_low 7571.5). Adverse excursion 23 pts.
- **Exit:** stopped 08:35 @7579.75. **Read:** shorted strength inside the range before any breakdown —
  wrong side, correctly cut at −1R.

### Trade 190 — 08:35 S4 TLB SHORT @7577.50 → LOSS −$202.50 (−1.0R)
- **Entry/location:** Mid/upper-IB. The 08:35 bar exploded 7578→**7595.50 high/close** (BLUE). Another
  short into an up-thrust.
- **Plan:** stop 7591.00 (**13.5 risk — widest stop of the day**), T1 7568.73, T2 7550.5. Half size.
- **Management:** none — straight STOP_HIT. MFE 1.5 pts; MAE 19.25.
- **Exit:** stopped 08:40 @7591.00 = biggest single loss of the day (wide stop × move). **Read:** same
  mistake as 188, one bar later and into a stronger up-bar; the wide 13.5-pt stop made it the costliest.

### Trade 191 — 08:50 S4 HFE SHORT @7591.50 → WIN +$39.00 (+0.43R) — the only managed winner of the early batch
- **Entry/location:** Upper-IB, near the highs (TPO `ib_high≈7596.75 WIDE`). HFE = failed-extension short.
- **Plan:** initial stop (metadata) 7597.50 (6.0 risk), T1 7586.70, T2 7582.50. Half size.
- **Management (full chain):**
  - 08:55:08 **T1_HIT** (price reached 7586.7; bar low 7584.0).
  - 08:55:08 **SMART_BE** stop 7597.5 → **7591.25** (locked just above entry).
  - 08:55:14 / 08:55:48 / 08:55:54 three **TRAIL** steps (k=1.0, risk 6.0): 7591.25 → 7590.75 → 7590.5 → **7590.0**, HWM ratcheting 7584.75→7584.0.
  - 09:00 **STOP_HIT** @7590.0.
- **Exit:** trailed-stop hit @7590.0. Booked +0.43R. **Read:** correct mechanics — T1 secured, BE+trail
  protected, exited green when price bounced. Worked exactly as designed; small win because the move
  (MFE 7.5 pts) reversed before T2.

### Trade 193 — 08:55 S4 HFE SHORT @7586.00 → LOSS −$172.50 (−1.0R)
- **Entry/location:** Upper-IB. The 08:55 bar ran back up to **7596.50** (BLUE). Shorted into the re-test
  of the highs.
- **Plan:** stop 7597.50 (11.5 risk), T1 7579.10, T2 7568.75. Half size.
- **Management:** none — STOP_HIT only. MFE 2.0 pts; price held up near 7596 then poked **7599.25** (session
  high) at 09:10 — the exact bar that stopped it.
- **Exit:** stopped 09:10 @7597.50. **Read:** shorted the top a third time before the break; the high print
  7599.25 took it out at −1R.

### Trade 194 — 09:05 S4 HFE SHORT @7593.50 → LOSS −$71.25 (−1.0R)
- **Entry/location:** Top-IB, right at the highs. The 09:05 bar 7593→7597 (BLUE).
- **Plan:** stop 7598.25 (4.75 risk — tight), T1 7589.70, T2 7586.38. Half size.
- **Management:** none. MFE 4.5 pts (bar low 7589.0 — **T1 7589.70 was technically grazed**, lowest_low 7589.0 ≤
  7589.7), but no T1_HIT was logged and the trade was stopped before any partial registered.
- **Exit:** stopped 09:10 @7598.25 on the same 7599.25 high-print bar that killed 193. **Read:** the closest
  of the early shorts to working (0.95R favorable) — it nearly tagged T1 — but the final push to the session
  high stopped it first. Tight stop kept the loss small.

### Trade 195 — 09:40 S2 INITIATIVE_SHORT @7551.00 → WIN +$94.38 (+1.14R)
- **Entry/location:** **Below-IB** (IB now locked 7560.5–7599.25 WIDE; entry 7551 is below IB low). This is
  the breakdown trade — price had already fallen 7599→7551 and the trend flipped **GRAY→RED at 09:40**, the
  exact fire bar.
- **Plan:** initial stop 7556.50 (5.5 risk), T1 7541.13, T2 7521.75, **T3 7502.38** (full ladder). 1 contract.
- **Management:**
  - 09:45 **T1_HIT** (bar low 7540.0, below T1 7541.13).
  - 09:45 **SMART_BE** 7556.5 → **7550.75**.
  - 09:50 **TRAIL** (k=1.0, risk 5.5) 7550.75 → **7546.50**, HWM 7541.0.
  - 09:50 **STOP_HIT** @7546.50.
- **Exit:** trailed stop @7546.50 = +1.14R. **Read:** correct direction, caught the break, banked T1+trail.
  But MFE was 11 pts / **2.44R** (low 7540.0) — the trail exited on the 09:45 pullback bounce while T2 (7521.75)
  was still 19 pts further down. **Left ~1.3R on the table** relative to MFE.

### Trade 196 — 09:45 S2 INITIATIVE_SHORT @7550.50 → WIN +$141.88 (+2.70R) — best trade of the day
- **Entry/location:** Below-IB, second breakdown entry one bar after 195.
- **Plan:** initial stop 7554.00 (**3.5 risk — tightest meaningful stop**), T1 7541.13, T2 7521.75, T3 7502.38. 1 contract.
- **Management:** all four events fired in one burst at 09:53:27 (catch-up processing on the 09:50 bar that printed low 7532.25):
  - **T1_HIT** → **SMART_BE** 7554→7550.25 → **TRAIL** (risk 3.5) to **7541.00** (HWM 7537.5) → **STOP_HIT** @7541.00.
- **Exit:** trailed stop @7541.00. Economics: c1 booked @T1 7541.13, c2/c3 @trailed 7541.00 → +$141.88;
  normalized to the tiny 3.5-pt risk = **2.70R**. **Read:** the tight stop is what produced the 2.70R — same
  pts of profit as 195 but on smaller risk. Yet MFE was **18.25 pts / 1.92R-of-additional-room** (low 7532.25 =
  basically AT POC 7532) — T2 7521.75 was 10 pts further. The 1-bar trail again kicked it out on the bounce
  while the down-leg had more to give. **Left money** vs holding a runner to POC/T2.

### Trade 197 — 10:10 S2 REACTIVE_SHORT (B_RVOL) @7538.50 → OPEN (currently −3.75 pts)
- **Entry/location:** Far-below-IB, near POC (7532). REACTIVE short = fading a bounce back up toward value.
  TPO at fire: `poc=7532.25 vah=7539.5 val=7527.25` → entry 7538.50 is right at VAH, fading the upper edge of
  the developing value area. Variant B_RVOL (relative-volume confirm). **Size 2 contracts.**
- **Plan:** stop 7547.75 (9.25 risk), T1 7531.56, T2 7520.00.
- **Management:** none yet (0 events). MFE since entry only 4.0 pts (low 7534.5); T1 7531.56 not reached.
- **Status:** OPEN, last close 7542.25 → **−3.75 against**. **Read:** mean-reversion fade inside a still-down
  market; price chopped 7534–7544 and is currently above entry. Not yet wrong (stop 7547.75 intact) but the
  reactive-long-against-trend logic is the riskier of the two S2 modes on a trend-down day.

### Trades 199 / 200 — 10:20:03 & 10:20:05 S2 REACTIVE_SHORT (B_RVOL) @7537.75 → OPEN (DUPLICATE PAIR)
- Two identical S2 REACTIVE_SHORT fires **2 seconds apart**, same entry 7537.75, same stop 7546.25, same
  T1/T2, same variant B_RVOL, **size 2 each**. This is a **double-fire** — almost certainly one signal written
  twice (no dedup), not two independent setups. Combined that would be 4 contracts of reactive short stacked on
  top of 197's 2 = **6 contracts of REACTIVE_SHORT** open against the same level.
- Both OPEN, last close 7542.25 → **−4.50 against**. No management events.
- **Read:** flag the duplicate. Same fade thesis as 197.

### Trade 201 — 10:20:05 S4 ZLR SHORT @7538.00 → OPEN (currently −4.25)
- **Entry/location:** Far-below-IB. ZLR (Zero-Line Reject) S4 pattern, confidence 0.65, fired at the same
  10:20 bar as the S2 reactive cluster.
- **Plan:** stop 7547.75 (9.75 risk), T1 7530.69, T2 7518.50.
- **Management:** none yet. MFE 3.5 pts (low 7534.5).
- **Status:** OPEN, last close 7542.25 → **−4.25 against**. **Read:** an S4 short layered onto the S2 reactive
  cluster at the same instant — four separate open shorts (197/199/200/201) now sit between 7537.75–7538.50,
  a **concentration of risk on one 5-min bar** worth noting.

---

## 3. Overall

### 3a. The 09:05 → 09:40 fire gap (35 min) — was the engine blind?
**No — the engine had data; it correctly sat out a GRAY (no-trend) transition.** Bars flowed every 5 min
through the whole window (09:10, 09:15 … 09:35 all present in both tables). What happened:

- 09:10 bar printed the **session high 7599.25**, then rolled over. Woodies `trend_state` flipped
  **BLUE → GRAY at 09:15** and stayed **GRAY through 09:35** (09:15, 09:20, 09:25, 09:30, 09:35 all GRAY).
- S4 (HFE/TLB/ZLR) requires a colored (BLUE/RED) Woodies trend; **GRAY is a no-fire zone.** So during the
  *actual* 48-pt breakdown (7599→7551, 09:10→09:40) S4 was correctly muted.
- The trend flipped to **RED at 09:40** — and S2 INITIATIVE_SHORT fired on that exact bar (trade 195).

So the gap is **expected behavior, not a data outage**: the system declines to chase a transition it can't
yet color, then engages once direction confirms RED. The cost is it **missed the meat of the move** (entered
7551 after the drop from 7599 was nearly done). That's a known tradeoff of trend-confirmation gating, not a bug.
The earlier `v9_bars_5min`-stall concern from prior sessions did **not** recur today.

### 3b. `day_type_at_entry` stamping
- **Top-level column is correct on all 11 trades:** early S4 batch = **Nontrend**, the 09:40+ batch = **Variation**.
- The live day-type machine (`v9_day_type_state`, latest 10:20 CT) reads: `day_type=Variation, stage=B2,
  opening_type=OPEN_DRIVE, ib_width_class=WIDE, lock_state=PENDING, confidence=0.38`. Consistent with the
  Variation stamp on the later trades. (The early Nontrend stamps reflect the pre-IB-lock classification while
  the profile was still narrow — before the day revealed itself as a downside Variation/breakout.)
- **The gap you spotted is real but narrower than "day_type=None":** it is the **nested** `quality.day_type`
  (None on every trade) and `cross_context[...].systems...day_type`. The persisted *column* is fine; the
  *quality/context JSON* isn't carrying the classification through. Low-risk (column is the source of truth for
  gating/stamping) but worth fixing so the trade-card/journal payload isn't misleading. — **OPEN item.**

### 3c. Did profit-realization leave money on the table on the breakdown winners?
**Yes, materially, on both S2 winners** — the 1-bar ATR trail (k=1.0) exits on the first pullback bounce while
the down-leg still had room:

| id | Realized R | MFE R (to lowest low) | Lowest low | Next target down | Left on table |
|----|-----------|-----------------------|-----------|------------------|---------------|
| 195 | +1.14R | **+2.44R** (low 7540.0) | 7540.0 | T2 7521.75 (−19 pts) | ~1.3R |
| 196 | +2.70R | ~+5.2R of room (low 7532.25 = POC) | 7532.25 | T2 7521.75 (−10 pts) | runner closed at POC bounce |

Both stopped on the **trailed** stop the bar after T1, on the 09:45/09:50 bounce, even though price kept
grinding to POC (7532) and the session low (7527.25) shortly after. On a clean trend-down day the **runner
(c3 → T2/T3 / structural trail)** is where the asymmetric money lives, and the tight k=1.0 trail cut it off.
This is exactly the trailing-runner lever in the roadmap (memory: *trend_gate_t1_widen*, trailing-runner
+$273 bt) — today is live evidence the current trail is too tight on the trend leg.

The early S4 batch (188/190/193/194) is the inverse problem: **four shorts into strength near the IB top
before the break** (7572–7593), three of them with no favorable excursion at all (MFE ≤2 pts). Net those four
= −$555; the two true breakdown trades (195/196) + the managed HFE (191) = +$275. **The day's edge was the
post-break S2 shorts; the pre-break S4 top-picking was the drag.**

### 3d. Other flags
- **Duplicate fire (199 = 200):** two identical S2 REACTIVE_SHORT writes 2s apart — needs dedup; otherwise
  size doubles silently (4 contracts instead of 2 on one signal).
- **Risk concentration at 10:20:** trades 197/199/200/201 = four open shorts in a 7537.75–7538.50 band, two
  systems firing the same direction on the same bar. Worth a gateway-level "already-positioned" check.
- **Trade 191 stop bookkeeping:** stored `stop`=7590.0 vs `metadata.stop_initial`=7597.5 — the column reflects
  the post-trail stop, not the initial. Cosmetic, but note when auditing risk from the column alone.

---

*Generated read-only from local Postgres `mems26`. No code or trading state modified.*
