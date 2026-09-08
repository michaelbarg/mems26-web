# SIX DAYS — the tape vs. the book (2026-09-08)

Six live sessions reviewed the way a Dalton trader reviews his own tape: what did the
market offer, and what did we take. Read-only review; nothing in the trading stack was
touched.

**MES = $5.00 / point.** Every $ figure below names its contract count. Short arithmetic
is `points = entry − exit`; a stopped short is negative.

## Reproduce

```bash
PSQL=/Applications/Postgres.app/Contents/Versions/latest/bin/psql
DB=postgresql://localhost/mems26

# Q1 — RTH bars (78/day on all 16 days pulled; ts = bar OPEN, window [09:30,16:00) ET)
$PSQL $DB -At -F',' -c "COPY (SELECT to_char(ts AT TIME ZONE 'America/New_York','YYYY-MM-DD HH24:MI') et,
  open,high,low,close,volume,trend_state,zlr_detected,hfe_detected
  FROM v9_bars_5min_woodies
  WHERE (ts AT TIME ZONE 'America/New_York')::date BETWEEN date '2026-08-12' AND date '2026-09-02'
    AND (ts AT TIME ZONE 'America/New_York')::time >= time '09:30'
    AND (ts AT TIME ZONE 'America/New_York')::time <  time '16:00'
  ORDER BY ts) TO STDOUT WITH CSV HEADER" > /tmp/sixdays/bars.csv

# Q2 — live trades
$PSQL $DB -c "SELECT id, entry_ts, exit_ts, firing_system, pattern_id_at_entry, direction,
  entry_price, exit_price, stop, exit_reason, pnl_usd, pnl_sierra, pnl_r, outcome,
  day_type_at_entry, quality->>'contracts', quality->>'initial_stop'
  FROM v9_trades WHERE mode='live'
    AND (entry_ts AT TIME ZONE 'America/New_York')::date IN
        ('2026-08-14','2026-08-27','2026-08-28','2026-08-31','2026-09-01','2026-09-02')
  ORDER BY entry_ts;"

# Q3 — canonical 7-type day-type (per docs/SOURCE_OF_TRUTH.md §Day-type)
curl -s "http://localhost:8000/api/v9/day_type/classify_replay?date=<D>"

# Q4 — broker truth, per trade, joined on Sierra InternalOrderID
python3 scripts/sierra_activity_join.py --date <D>     # dry-run, writes nothing
```

Structure + dominant-move arithmetic: `outputs/six_days_analyze.py` (this session).
IB derived from **bars**, never `v9_tpo_history` (time-shifted before 31.08). Cross-check:
bars-derived IB equals the classifier's `sierra_tpo` IB to the tick on **6/6** days.

### Dominant-move definition (used for "what the day was worth")

Entry is a **bar close**, never the extreme tick. The favourable extreme is the running
max-high / min-low. The move terminates on the first bar whose **close** gives back more
than 40% of the excursion established so far. Close-based on purpose: an intrabar rule
lets the same bar that makes the high kill its own move with its own low, which returned
absurd 6-point "dominant moves" on a 34-point day. Only the single largest move per day
is reported — one good trade, not the sum of the wiggles.

---

## ⚠️ Money: three layers, and they do not agree

Before any ratio below is read as precise, this must be on the table.

| date | books `pnl_usd` | `pnl_sierra` | `broker_pnl` (activity log) | headline used | acct-day total | unmapped residual |
|---|---|---|---|---|---|---|
| 2026-08-14 | −135.00 (n=5) | −212.50 (n=4) | −62.50 (n=5) | **−167.50** | +120.00 | +182.50 |
| 2026-08-27 | +123.75 (n=5) | +50.00 (n=3) | +175.00 (n=5) | **+123.75** | +301.25 | +126.25 |
| 2026-08-28 | +348.75 (n=8) | +146.25 (n=4) | +535.00 (n=7) | **+348.75** | +412.50 | −122.50 |
| 2026-08-31 | −203.75 (n=7) | −203.75 (n=4) | −65.00 (n=6) | **−203.75** | −100.00 | −35.00 |
| 2026-09-01 | −236.25 (n=3) | −236.25 (n=3) | −286.25 (n=3) | **−236.25** | −226.25 | +60.00 |
| 2026-09-02 | +422.50 (n=4) | +270.00 (n=2) | +253.75 (n=3) | **+270.00** | +602.50 | +348.75 |

Findings, not opinions:

1. **`pnl_sierra` is NULL on 12 of 32 live rows** — every `phantom_reconcile` /
   `MAE_SCRATCH` / `manual` exit. `Σ pnl_sierra` is therefore a sum over a subset, not a
   day total. This is T-160 / T-256, still open.
2. **The fixed headline for 2026-08-14 (−$167.50) matches none of the three layers.**
   Books say −135.00, `pnl_sierra` −212.50, the activity log −62.50. The other five
   headlines each match one layer (08-27/08-28 = books; 08-31/09-01 = both; 09-02 =
   `pnl_sierra`). Flagged, not re-ranked — the six-day ordering was given as fixed.
3. **`sierra_activity_join` reports COVERAGE INCOMPLETE on 6/6 days.** Its own header then
   says the per-trade deltas are "indicative only". The residual is not error — account
   37138283 is shared with Eti's manual trading, so the account-day total is *not* the
   system's P&L and cannot be used as ground truth for it.
4. **9 rows are marked `!!` (unresolved)** — the two independent broker computations
   (summed Closed-Trade-P/L vs. reconstruction from fill prices) disagree, so the join
   cannot say which fill a P/L record belongs to: `673, 828, 830, 848, 851, 853, 942, 950,
   963`. Those broker numbers are carried below with `!!` and are not used in any total.
5. `entry_price` differs from the actual fill on **24 of 32** rows (up to 2.50 pts on
   #838) — our `entry_price` is a submission record, not a fill (T-256).

Every ratio below uses the fixed headline as the numerator. Given (1)–(4) the honest
precision is roughly **±$100/day**, so treat the capture percentages as a band, not a
decimal.

---

# 2026-08-28 · +$348.75 · the best day

**1 · The day, structurally.** Prior close 7741.25 → open 7746.25 (**gap +5.00**), opened
*in* prior value. IB 7726.50–7760.50 (**34.00 pts**, 49th pctile, NORMAL). The session then
went **both ways**: range extension **up +22.00** to 7782.50 at 11:00, then a 67-point
liquidation to **7711.75 at 13:10** — extension **down −14.75**. Total range **70.75 pts**
(the largest of the six; median daily range 44.0). Close 7722.75 — **below IB**, at **16%**
of the day's range. In Dalton's terms: **a failed upside extension that reversed** — the
market probed above the IB, found no buyer above value, and spent the afternoon auctioning
down to close on its low.

**2 · The label we gave it.** EOD classifier: **Neutral_Extreme** (`winner_side`) — "2-sided,
close at an extreme (one side won late)". `eod_continuation_tag = NE_CLOSE_DOWN`. That is
exactly the tape. The **live** label disagreed: `day_type_at_entry = Trend_Normal` on the
10:05 entry and `Variation` through midday; only the 14:40 trade (#862) carried
`Neutral_Extreme`. The classifier segment at 10:05 said `Normal`. **The EOD label matched
the tape; the live label was three hours late to it.**

**3 · What the day was worth.** Dominant move **SHORT**: bar close **7779.00 @ 11:25** →
**7711.75 @ 13:10** = **67.25 pts**, no 40% close-retrace until 15:55.
→ **$672.50 at 2 contracts · $1,681.25 at 5 contracts.**

**4 · What we took.** 8 live trades, 7 of 8 short (with the dominant move).

| time | # | sys | pattern | dir | ct | entry | exit | `pnl_sierra` | broker | exit reason |
|---|---|---|---|---|---|---|---|---|---|---|
| 10:05–10:18 | 838 | S4 | ZLR | SHORT | 3 | 7746.50 | — | *(null)* | +107.50 | phantom_reconcile |
| 10:10–10:18 | 840 | S4 | (scale-in child) | SHORT | 2 | 7738.75 | — | *(null)* | +56.25 | phantom_reconcile |
| 10:15–10:17 | 841 | S4 | (child) | SHORT | 2 | 7731.00 | 7738.75 | **−77.50** | −70.00 | STOP_FILL |
| 11:20–11:38 | 848 | S4 | ZLR | LONG | 2 | 7776.25 | — | *(null)* | — | MAE_SCRATCH |
| 11:55–12:53 | 851 | S2 | INITIATIVE_SHORT | SHORT | 3 | 7750.00 | — | *(null)* | +132.50 `!!` | manual |
| 12:01–12:52 | 853 | S2 | (child) | SHORT | 2 | 7736.00 | 7735.75 | **+60.00** | +131.25 `!!` | STOP_HIT |
| 13:00–13:10 | 859 | S4 | ZLR | SHORT | 3 | 7725.75 | — | **+155.00** | +143.75 | **T3_HIT** |
| 14:40–15:51 | 862 | S4 | TT | SHORT | 2 | 7720.50 | — | **+8.75** | +33.75 | phantom_reconcile |

Short sign check: #841 SHORT 7731.00 → 7738.75 = **−7.75 pts** × $5 × 2ct = **−$77.50** ✓
(equals `pnl_usd` and `pnl_sierra` exactly). Only one loser all day.
**Ratio: $348.75 ÷ $672.50 = 51.9% of the day's available money at 2 contracts** (20.7% of
the $1,681.25 the same move was worth at 5; we averaged 2.4 ct).

**5 · Journal.** *Sold the failed extension seven times and let one of them run to T3 —
the day the machine and the tape were reading the same book.*

---

# 2026-09-02 · +$270.00 · second best

**1 · The day, structurally.** Prior close 7644.00 → open 7650.50 (**gap +6.50**), opened
*in* value. Low **7643.25 in the 09:35 bar** — the low was in the second five-minute bar of
the session and was never revisited. IB 7643.25–7682.50 (**39.25 pts**, 61st pctile — the widest IB of the six).
High **7691.25 at 11:30**, RE up only **+8.75**, no downside extension at all. Range **48.00**.
Close 7678.50 — **inside IB**, at **73%** of range. Dalton: **an early one-sided drive that
then held** — the auction found its low immediately, extended modestly above the IB, and
spent five hours holding the upper half without giving it back.

**2 · The label we gave it.** EOD: **Normal_Variation** (`with_extension`, rib 1.2229) —
1-sided extension, Expanded Typical. Matches the tape. Live: `Normal` on #953 at 10:15 —
**agrees** with the classifier segment at that minute; `Variation` on the three later
trades, where the classifier said `Normal_Variation` — a naming mismatch of the old 3-type
engine, not a directional error.

**3 · What the day was worth.** Dominant move **LONG**: bar close **7647.00 @ 09:45** →
**7691.25 @ 11:30** = **44.25 pts** (40% close-retrace at 12:40).
→ **$442.50 at 2 contracts · $1,106.25 at 5 contracts.**

**4 · What we took.** 4 live trades, all at 5 contracts, 3 of 4 long.

| time | # | sys | pattern | dir | ct | entry | exit | `pnl_sierra` | broker | exit reason |
|---|---|---|---|---|---|---|---|---|---|---|
| 10:15–11:48 | 953 | S2 | INITIATIVE_LONG | LONG | 5 | 7668.75 | 7677.75 | **+187.50** | +162.50 | STOP_HIT (trailed) |
| 11:59–12:16 | 963 | S4 | ZLR | LONG | 5 | 7685.75 | — | *(null)* | — `!!` | MAE_SCRATCH |
| 12:40–13:04 | 968 | S4 | ZLR | SHORT | 5 | 7676.25 | — | *(null)* | +15.00 | MAE_SCRATCH |
| 13:10–14:41 | 971 | S4 | GHOST | LONG | 5 | 7673.25 | 7673.75 | **+82.50** | +76.25 | STOP_FILL (stop in profit) |

**Zero losing trades.** #953 is the day: LONG 7668.75 → 7677.75 = **+9.00 pts** on the
final leg, but the books say +$277.50 vs. `pnl_sierra` +$187.50 vs. broker +$162.50 — a
scale-in row, so points × contracts ≠ P&L. Note the books-vs-broker gap of **$115.00 on
this single trade**.
**Ratio: $270.00 ÷ $442.50 = 61.0% at 2 contracts.** At the 5 contracts we actually
traded, the same day offered $1,106.25 — so **24.4% of what our own size could have made.**

**5 · Journal.** *Bought the hold and left every stop where it belonged — no loser all day,
and still only a quarter of what five contracts were worth on a 44-point drive.*

---

# 2026-08-27 · +$123.75 · third

**1 · The day, structurally.** Prior close 7692.00 → open 7716.25 — **gap +24.25**, opening
**out of prior value but inside the prior range** (`OPEN_AUCTION_IN` / `out_value_in_range`).
The gap was immediately tested: low **7702.75 in the 09:35 bar** — the second five-minute bar
gave 13.50 points back. IB 7702.75–7730.50 (27.75, 35th pctile). Then **one-sided upside extension +25.25** to
**7755.75 at 13:10**; **no downside extension at all**. Range 53.00, close 7741.25 — **above
IB**, **73%** of range. Dalton: **a gap that was re-tested and then extended one-sided** —
the textbook "test the gap, accept it, extend" sequence.

**2 · The label we gave it.** EOD: **Normal_Variation** (`with_extension`, rib 1.9099).
Correct — 1-sided RE up, close above IB. Live carried `Trend_Normal` at 10:15 (segment said
`Normal`) and `Variation` later. **Classifier matched; live label disagreed on 3/3 labelled
trades.**

**3 · What the day was worth.** Dominant move **SHORT**: bar close **7753.75 @ 13:20** →
**7722.75 @ 14:55** = **31.00 pts** → **$310.00 at 2ct · $775.00 at 5ct.**
The best long was 27.50 pts — this is the one day where the two sides were nearly equal, so
the "dominant" reading is genuinely ambiguous. Both readings are stated; what separates
them is only 3.5 points, inside a single bar's range on this day (avg bar 5.70).

**4 · What we took.** 5 live trades, 1–2 contracts.

| time | # | sys | pattern | dir | ct | entry | exit | `pnl_sierra` | broker | exit reason |
|---|---|---|---|---|---|---|---|---|---|---|
| 09:55–09:57 | 822 | S2 | OPENING_ORR | LONG | 2 | 7723.50 | 7713.50 | **−100.00** | −95.00 | STOP_FILL |
| 10:15–10:27 | 824 | S4 | ZLR | LONG | 2 | 7719.00 | — | **+105.00** | +97.50 | **T2_HIT** |
| 12:02–12:37 | 828 | S4 | ZLR | LONG | 2 | 7739.75 | — | **+45.00** | +47.50 `!!` | **T2_HIT** |
| 14:00–14:29 | 830 | S2 | INITIATIVE_SHORT | SHORT | 2 | 7743.50 | — | *(null)* | +72.50 `!!` | phantom_reconcile |
| 14:05–14:29 | 831 | S2 | (child) | SHORT | 1 | 7736.50 | — | *(null)* | +52.50 | phantom_reconcile |

#822 LONG 7723.50 → 7713.50 = **−10.00 pts** × $5 × 2 = **−$100.00** ✓. It bought the gap
two minutes before the 09:35 low — the right idea 13.5 points too early; price later ran
32.25 points in its favour (MFE from that entry).
**Ratio: $123.75 ÷ $310.00 = 39.9% at 2 contracts.**

**5 · Journal.** *Bought the gap too early, paid $100 for it, then caught the acceptance
twice for two targets — a day saved by the second and third trade, not the first.*

---

# 2026-09-01 · −$236.25 · the worst day

**1 · The day, structurally.** Prior close 7698.00 → open 7647.00 — **gap −51.00**, the only
`OPEN_AUCTION_OUT` / **out_of_range** open of the six. IB 7638.50–7667.25 (28.75). The
market then went **both ways**: RE up +6.50 to **7673.75 at 11:50**, then RE down **−17.00**
to **7621.50 at 14:45**. Range 52.25. Close 7644.00 — **inside IB**, **43%** of range, i.e.
dead centre. Dalton: **balance that held after a violent gap** — a big gap out of range that
neither extended nor filled; two-sided rotation closing at the middle.

**2 · The label we gave it.** EOD: **Neutral_Center** (`fade_both`) — "2-sided, close at
center (balanced)". That is precisely the tape, and its prescribed direction is
**fade both edges**. The live label on all three trades was **`Trend_Normal` then
`Variation`** — the classifier segment at each entry said `Normal_Variation`. **We traded a
balanced fade-both day as if it were a trend day. Of the six, this is the day the label
gap cost the most.**

**3 · What the day was worth.** Dominant move **SHORT**: bar close **7672.50 @ 11:50** →
**7621.50 @ 14:45** = **51.00 pts**, 98% of the entire session range.
→ **$510.00 at 2ct · $1,275.00 at 5ct.**

**4 · What we took.** 3 live trades, 4–5 contracts — the largest average size of the six.

| time | # | sys | pattern | dir | ct | entry | exit | `pnl_sierra` | broker | exit reason |
|---|---|---|---|---|---|---|---|---|---|---|
| 10:20–10:58 | 942 | S2 | INITIATIVE_LONG | LONG | 4 | 7660.25 | 7660.50 | **+55.00** | +155.00 `!!` | STOP_FILL (BE) |
| 11:45–12:15 | 948 | S4 | GB100 | LONG | 5 | 7668.75 | 7661.25 | **−135.00** | −128.75 | STOP_FILL |
| 12:35–12:41 | 950 | S2 | INITIATIVE_SHORT | SHORT | 5 | 7643.75 | 7650.00 | **−156.25** | −312.50 `!!` | STOP_FILL |

Sign checks: #948 LONG 7668.75 → 7661.25 = −7.50 pts (blended −$135.00 over partial legs).
#950 **SHORT** 7643.75 → 7650.00 = **−6.25 pts** × $5 × 5ct = **−$156.25** ✓ — negative, as a
stopped short must be.
**3 of 3 trades exited on `STOP_FILL`**, two of them at a loss-side stop (#942's stop had
been moved to BE+0.25, so it is a win mis-coded as a stop-out). #942 bought 7660.25 and gave
it all back; #948 bought 7668.75, 5.00 points below the 11:50 high, on a day the
classifier had labelled fade-both. #950 then shorted 7643.75 — the right direction 28.75
points below the dominant entry — and was stopped for −6.25 before price reached 7621.50
(**MFE after the exit: 22.25 pts**).
**Ratio: −$236.25 ÷ $510.00 = −46.3% at 2 contracts.**

**5 · Journal.** *A 51-point gift on a balanced day, and I bought the high, sold the low,
and never moved a stop — three trades, three hard stops, and the one that was right got
stopped 22 points early.*

---

# 2026-08-31 · −$203.75 · second worst

**1 · The day, structurally.** Prior close 7722.75 → open 7701.25 — **gap −21.50**, an
`OPEN_TEST_DRIVE`. Low **7674.75 at 10:25**, then a grind higher for the rest of the session
to close **7698.00 — inside the IB**, at **69%** of range, **on the session high (7708.25 at
15:55)**. IB 7674.75–7704.25 (29.50). RE up only **+4.00**, RE down **0.00**. Range **33.50** —
the narrowest of the six against a 44.0 median. Dalton: **a gap-down that was rejected and
repaired** — the sell attempt failed at the IB low and the balance held all afternoon.

**2 · The label we gave it.** EOD: **Normal_Variation** (`with_extension`, rib 1.1356). Live:
`Normal` on both labelled trades (#936, #939) — and here **the live label matched the tape
better than the EOD label**: the day never really extended (RE up 4.00, RE down 0.00, closed
inside the IB), so "Variation/extension" overstates it. **This is the one day of the six
where the EOD classifier is the weaker read.** Flagged rather than smoothed over.

**3 · What the day was worth.** Dominant move **LONG**: bar close **7681.25 @ 14:40** →
**7708.25 @ 15:55** = **27.00 pts** → **$270.00 at 2ct · $675.00 at 5ct.**
The best short was 16.00 pts. Note the money was in the *last 75 minutes*; the morning's
short offered ~25 points less than the afternoon's long.

**4 · What we took.** 7 live trades — **6 of 7 SHORT**, on the day whose dominant move was
long. Only 1 of 7 aligned.

| time | # | sys | pattern | dir | ct | entry | exit | `pnl_sierra` | broker | exit reason |
|---|---|---|---|---|---|---|---|---|---|---|
| 09:35–09:35 | 873 | S4 | GB100 | SHORT | 2 | 7688.75 | 7688.50 | **+11.25** | −8.75 | STOP_HIT |
| 09:40–09:40 | 875 | S2 | OPENING_DRIVE | SHORT | 5 | 7689.50 | 7693.50 | **−100.00** | −100.00 | STOP_FILL |
| 10:00–11:09 | 877 | S2 | REACTIVE_SHORT | SHORT | 5 | 7689.50 | — | *(null)* | +116.25 | phantom_reconcile |
| 10:10–11:09 | 881 | S2 | (child) | SHORT | 2 | 7682.50 | — | *(null)* | +40.00 | phantom_reconcile |
| 10:35–10:36 | 885 | S2 | (child) | SHORT | 2 | 7676.50 | 7682.50 | **−60.00** | −57.50 | STOP_FILL |
| 14:15–14:33 | 936 | S4 | ZLR | LONG | 2 | 7695.00 | 7689.50 | **−55.00** | −55.00 | STOP_FILL |
| 15:05–15:10 | 939 | S4 | ZLR | SHORT | 2 | 7685.25 | — | *(null)* | — `!!` | SIERRA_FLAT |

#885 SHORT 7676.50 → 7682.50 = **−6.00 pts** × $5 × 2 = **−$60.00** ✓ — it shorted 1.75 points
above the day's low at 10:35. #936 was the one aligned trade and still lost: it bought
7695.00 at 14:15, **13.75 points above and 25 minutes before** the dominant long's entry,
and was stopped at 7689.50 before the actual launch.
**Ratio: −$203.75 ÷ $270.00 = −75.5% at 2 contracts** — the worst capture of the six.

**5 · Journal.** *Sold a gap-down that had already been rejected, six times, then finally
bought — 25 minutes early and 14 points high. Wrong side all morning, wrong location in the
afternoon.*

---

# 2026-08-14 · −$167.50 · third worst, and the most instructive

**1 · The day, structurally.** Prior close 7823.25 → open 7827.75 (**gap +4.50**), opening out
of prior value but inside the prior range. IB 7813.75–7830.75 — **17.00 pts, the 12th
percentile: the narrowest IB of the six** and a session range of only **34.25** against a
**66.5** median daily range. High **7830.75 at 10:05** = the IB high; **no upside extension at
all (RE up 0.00)**; RE down **−17.25** to **7796.50 at 13:35**. Close 7805.50 — **below IB**,
**26%** of range. Dalton: **a failed upside probe followed by one-sided downside extension**
on half the usual range — a slow, narrow selling day, not a drive.

**2 · The label we gave it.** EOD: **Normal_Variation** (`with_extension`, rib 2.0147) —
correct (1-sided extension down, close below IB). Live carried `Trend_Normal` on two trades
and `Variation` on two; the classifier segment said `Normal_Variation` all day.
**4/4 labelled trades disagreed. The classifier matched the tape.**

**3 · What the day was worth.** Dominant move **SHORT**: bar close **7828.00 @ 10:05** →
**7796.50 @ 13:35** = **31.50 pts** — 92% of the entire session range, with no 40%
close-retrace until 15:55. → **$315.00 at 2ct · $787.50 at 5ct.**

**4 · What we took.** 5 live trades, **4 of 5 SHORT — the highest alignment with the
dominant move of any of the six days.**

| time | # | sys | pattern | dir | ct | entry | exit | `pnl_sierra` | broker | exit reason |
|---|---|---|---|---|---|---|---|---|---|---|
| 10:35–10:37 | 668 | S4 | TREND_STEP | SHORT | 4 | 7811.25 | 7816.00 | **−95.00** | −95.00 | STOP_FILL |
| 10:55–12:15 | 670 | S4 | ZLR | SHORT | 4 | 7812.50 | — | *(null)* | +81.25 | manual |
| 11:14–11:30 | 673 | S4 | (child) | SHORT | 2 | 7806.50 | 7806.25 | **+11.25** | +72.50 `!!` | STOP_HIT |
| 12:37–12:41 | 680 | S4 | ZLR | LONG | 2 | 7808.00 | 7803.50 | **−45.00** | −42.50 | STOP_FILL |
| 13:00–13:11 | 682 | S4 | TREND_STEP | SHORT | 4 | 7799.25 | 7804.25 | **−83.75** | −78.75 | STOP_FILL |

Sign checks: #668 SHORT 7811.25 → 7816.00 = **−4.75 pts** × $5 × 4ct = **−$95.00** ✓ (matches
the broker to the cent). #682 SHORT 7799.25 → 7804.25 = **−5.00 pts** × $5 × 4ct = **−$100.00**
book-equivalent; `pnl_sierra` −$83.75 on partial legs.
The direction was right and the day still lost, because of **location**: #668 sold at 10:35
and was stopped in **two minutes**, after which price ran **14.75 points** its way; #682 sold
7799.25 at 13:00, only **2.75 points above the 13:35 low** — it sold the bottom. Mean
location score (1.00 = sold the high of the range so far) was **0.19** — we were selling the
lower fifth of the developing range on a day that had already extended down.
**Ratio: −$167.50 ÷ $315.00 = −53.2% at 2 contracts.**

**5 · Journal.** *Right about the direction four times out of five on a 31-point slide, and
still lost $167 — because I kept selling the bottom of it.*

---

# Across the six

## Availability vs. capture

| date | result | dominant move | avail @2ct | avail @5ct | took (headline) | capture @2ct | ct traded |
|---|---|---|---|---|---|---|---|
| 2026-08-28 | WIN | SHORT 67.25 pts | $672.50 | $1,681.25 | +$348.75 | **51.9%** | 2–3 |
| 2026-09-02 | WIN | LONG 44.25 pts | $442.50 | $1,106.25 | +$270.00 | **61.0%** | 5 |
| 2026-08-27 | WIN | SHORT 31.00 pts | $310.00 | $775.00 | +$123.75 | **39.9%** | 1–2 |
| 2026-09-01 | LOSS | SHORT 51.00 pts | $510.00 | $1,275.00 | −$236.25 | **−46.3%** | 4–5 |
| 2026-08-14 | LOSS | SHORT 31.50 pts | $315.00 | $787.50 | −$167.50 | **−53.2%** | 2–4 |
| 2026-08-31 | LOSS | LONG 27.00 pts | $270.00 | $675.00 | −$203.75 | **−75.5%** | 2–5 |

Six-day totals: available **$2,520.00 @2ct** / **$6,300.00 @5ct**; taken **+$135.00**.
**Capture across the six days: 5.4% of the 2-contract availability.**

## What does NOT separate the winners from the losers

Each of these was tested and each fails on at least one day — stated so the plausible
story is not mistaken for the true one.

- **Day type does not separate it.** `Normal_Variation` is the EOD label on two winners
  (08-27, 09-02) *and* two losers (08-14, 08-31). Winners: Normal_Variation,
  Neutral_Extreme, Normal_Variation. Losers: Normal_Variation, Normal_Variation,
  Neutral_Center.
- **Trading with the day's one-timeframe direction does not separate it.** 2026-08-14 had
  the **highest** alignment of all six (**4/5** trades on the side of a 31.5-point move) and
  lost $167.50. 2026-08-27 had **2/5** and won. Alignment counts: winners 2/5, 7/8, 3/4;
  losers 4/5, 1/7, 1/3 — the ranges overlap.
- **The first trade of the day does not separate it.** 08-27 won the day *after* a −$100
  opening loss; 09-01 lost the day *after* a first trade that made money (+$55 `pnl_sierra`,
  +$155 broker). Winners' first trades: −$100, +$107.50, +$187.50. Losers': −$95, +$11.25,
  +$55. Overlapping.
- **Gap direction separates 5 of 6, not 6 of 6.** All three winners gapped **up** (+24.25,
  +5.00, +6.50); the two heaviest losers gapped **down** (−21.50, −51.00) — but 08-14 gapped
  **+4.50 and lost**. Suggestive, insufficient.

## What DOES separate them — and the honest caveat

**The trade that never earned a stop move.** Two counts, and the second is the honest one.

| | 08-27 W | 08-28 W | 09-02 W | 08-14 L | 08-31 L | 09-01 L |
|---|---|---|---|---|---|---|
| `STOP_FILL` (any) | 1/5 | 1/8 | 1/4 | **3/5** | **3/7** | **3/3** |
| stopped at a **loss-side** stop | 1/5 | 1/8 | **0/4** | **3/5** | **3/7** | **2/3** |
| target hits (T2/T3) | 2 | 1 | 0 | **0** | **0** | **0** |

The raw `STOP_FILL` count splits every winning day at 1 and every losing day at 3, but it
is not a clean definition: `STOP_FILL` fires on *any* stop, including one already moved.
Checking `quality->>'initial_stop'` against `stop` per row, **2 of the 12 `STOP_FILL` rows
were at a stop already moved into profit** — 09-01 #942 (initial 7652.75 → 7660.50 vs entry
7660.25, i.e. BE+0.25) and 09-02 #971 (initial 7666.00 → 7673.75 vs entry 7673.25). Both are
*wins*, wrongly counted as stop-outs by the raw reason code.

Corrected to stops hit while still **beyond entry** — the trade never earned a stop move:
**winners 2/17 trades (12%), losers 8/15 (53%).** And **on all three losing days not one
trade reached a target**; on the winning days the money comes from trades that survived —
T2_HIT ×2 (08-27), T3_HIT (08-28, +$155.00 on 3ct), and the trailed STOP_HIT on 09-02 #953
(+$187.50 on 5ct).

**The caveat, stated plainly: this is partly tautological.** A losing trade must end
somewhere, and "hit its stop" is the usual place. The count alone cannot carry the claim.
The **non-tautological** part is the counterfactual: of the 11 stopped trades on the losing
days, **7 were later proven right** — after our exit, price travelled further in the trade's
own direction than the stop distance we had used:

- 08-14: #668 (stopped −4.75, then 14.75 pts our way), #673
- 08-31: #873, #875 (stopped −4.00, then 14.75 pts our way), #936
- 09-01: #942, #950 (stopped −6.25, then **22.25 pts** our way)

That is not "we lost because we lost". That is **entry location and stop placement**, and it
is measurable: the eight loss-side stops on the three losing days were **4.00–7.50 points**,
i.e. **0.75×–1.38× (median ≈1.16×) the day's average 5-minute bar range** (3.80 / 5.33 / 5.61
pts). We were risking roughly one bar of noise on entries taken in the lower fifth of the
developing range.

**Two readings fit, and here is what separates them.**
(a) *Volatility*: the losers were the narrow days — 08-14 range 34.25 (median 66.5) and
08-31 range 33.50 (median 44.0), while the winners ran 53.00 / 70.75 / 48.00.
(b) *Stop survival / entry location*, above.
Reading (a) fails on **2026-09-01**, which had a 52.25-point range — wider than two of the
three winning days — and still went 3-for-3 on hard stops for −$236.25. Reading (b) holds on
all six. **09-01 is the discriminating case, and it favours (b).** If a wide losing day had
shown a *low* STOP_FILL rate, (a) would have survived instead; it did not.

## Loss composition on the losing days

| date | headline | # losing trades | worst single trade | share of the day |
|---|---|---|---|---|
| 2026-08-14 | −$167.50 | 3 (of 5) | #668 −$95.00 (SHORT, 4ct, STOP_FILL) | **57%** |
| 2026-08-31 | −$203.75 | 3 (of 7) | #875 −$100.00 (SHORT, 5ct, STOP_FILL) | **49%** |
| 2026-09-01 | −$236.25 | 2 (of 3) | #950 −$156.25 (SHORT, 5ct, STOP_FILL) | **66%** |

**No losing day was a single blow-up.** Each is an accumulation, and on each the worst
trade is a `STOP_FILL` at 4–5 contracts. 09-01 is the most concentrated: #950 (−$156.25)
plus #948 (−$135.00) sum to −$291.25 — **123% of the day's loss** — with the day's only
winner (#942, +$55.00) covering the rest. Note also that the two largest single losses of
the six days (#950 −$156.25 and #948 −$135.00) are both 5-contract trades on 09-01, the day
with the largest average size and the worst label disagreement.

## Label disagreement (the ~7-of-15 problem, measured here)

**17 of 21** labelled live trades carried a `day_type_at_entry` that disagreed with the
canonical classifier's segment at the same minute. `day_type_at_entry` is the OLD 3-type
engine (`Trend_Normal` / `Variation` / `Normal`), and the 7-type classifier is the authority
per `docs/SOURCE_OF_TRUTH.md` §Day-type. Which one matched the tape:

| date | tape | EOD classifier | live label | who was right |
|---|---|---|---|---|
| 08-14 | 1-sided down ext., close below IB | Normal_Variation | Trend_Normal / Variation | **classifier** |
| 08-27 | 1-sided up ext., close above IB | Normal_Variation | Trend_Normal / Variation | **classifier** |
| 08-28 | 2-sided, closed on the low | Neutral_Extreme | Trend_Normal → Variation → NE | **classifier** (live 3 h late) |
| 08-31 | rejected gap-down, closed **inside** IB, RE 4.00/0.00 | Normal_Variation | Normal | **live** |
| 09-01 | 2-sided, closed dead centre | Neutral_Center | Trend_Normal / Variation | **classifier** |
| 09-02 | 1-sided up, held | Normal_Variation | Normal / Variation | **classifier** |

**Classifier 5, live label 1.** The single most expensive instance is **09-01**: the
classifier called `Neutral_Center` / **`fade_both`**, the live engine carried `Trend_Normal`
then `Variation`, and all three trades were taken as directional continuations into a
balanced day. That is a −$236.25 day where the canonical label prescribed the opposite
behaviour.

---

*Sources: `v9_bars_5min_woodies` (Q1, 78 RTH bars × 16 days, single symbol);
`v9_trades` mode='live' (Q2, 32 rows); `/api/v9/day_type/classify_replay` (Q3);
`scripts/sierra_activity_join.py --date <D>` dry-run (Q4).
IB cross-checked bars-vs-classifier: exact on 6/6 days. Analysis script:
`outputs/six_days_analyze.py`. Nothing was written to the DB, `.env`, or Sierra.*
