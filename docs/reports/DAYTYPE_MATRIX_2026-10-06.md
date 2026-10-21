# DAYTYPE MATRIX — playbook phase C, all five day types (READ-ONLY)

**Order:** Michael 2026-10-06 11:24 IL — the stairs-above-VAH study is only the TREND cell; measure the other four on the same sessions. Companion to `STAIRS_2026-10-06.md` (written by the stairs agent in parallel; not read, not touched).
**Scope:** 65 sessions in `harness_out/t529/sessions.txt` (2026-06-15 … 2026-10-02). Window 17:30–20:00 IL. One contract, $5/pt, **no fees** (not modelled). No harness, no yaml, no `.env`, no restart, no commit.
**Sources (as ordered):** bars `v9_bars_5min_woodies` MES (`ts` = bar OPEN, IL via `AT TIME ZONE 'Asia/Jerusalem'`) · VA/IB `v9_tpo_sessions` `session_type='CASH'` (`vah_price/val_price/poc_price/ib_high/ib_low`, end-of-day row) · label = `v9_decision_vectors` `kind='DECISION'` `vector->>'day_type'`.
**Script:** `/tmp/daytype_matrix.py` (outside repo, read-only connection `set_session(readonly=True)`), raw output `/tmp/daytype_matrix.out`.

## 0 · The finding that bounds everything else: 54 of 65 sessions have no label

```
$ psql -d mems26 -c "SELECT min(ts), max(ts), count(*) FROM v9_decision_vectors WHERE kind='DECISION';"
             min              |              max              | count
------------------------------+-------------------------------+-------
 2026-09-17 14:00:35.18752+03 | 2026-10-05 22:38:09.289448+03 |  1444
```

`DECISION` rows start **2026-09-17**. Of the 65 sessions, only **11** (2026-09-18 … 2026-10-02) carry a bar-level day-type label from the ordered source; **54** (2026-06-15 … 2026-09-15) are **UNLABELED** and get no trade in any cell. `kind='BAR'` rows (163,821) carry no `day_type` (checked: 0 non-null). Bars + CASH TPO rows exist for all 65 except 07-16 (no CASH row). I did not substitute another label source (`v9_day_type_history` is one end-of-day row per date — a different thing from "label at the bar"); that is Michael's call, see §5.

So this matrix is **11 sessions, 2 weeks (09-18 → 10-02)**. Every Σ below is small-N and must be read as such.

## 1 · Summary matrix (cell × month)

| Day type (cell) | Month | Sessions labeled | Trades | Win % | Σ$ |
|---|---|---|---|---|---|
| **TREND** (`Trend_Normal`/`Trend_DD`) — overlaps STAIRS | 2026-09 | 2 | 2 | 100% (2/2) | **+168.75** |
| | 2026-10 | 0 | 0 | n/a | 0 |
| | **ALL** | **2** | **2** | **100%** | **+168.75** |
| **NORMAL** (`Normal`) — VAH/VAL fade → POC | 2026-09 | 2 | 2 | 0% (0/2) | **−20.00** |
| | 2026-10 | 0 | 0 | n/a | 0 |
| | **ALL** | **2** | **2** | **0%** | **−20.00** |
| **VARIATION** (`Variation`/`Normal_Variation`) — with first IB extension | 2026-09 | 5 | 5 | 20% (1/5) | **−92.50** |
| | 2026-10 | 2 | 2 | 0% (0/2) | **−43.75** |
| | **ALL** | **7** | **7** | **14%** | **−136.25** |
| **NEUTRAL** (`Neutral_Center`/`Neutral_Extreme`) — fade IB extreme → mid | ALL | **n=0** | 0 | n/a | 0 |
| **NONTREND** (`Nontrend`/`Nonconviction`) — stand down | ALL | **n=0** | 0 | n/a | 0 (naive fade: n=0, nothing to cost) |
| UNLABELED (no DECISION rows) | 06 / 07 / 08 / 09 | 8 / 17 / 20 / 10 = **54** (+07-16 also missing its CASH TPO row) | — | — | — |
| **Total scored** | | **11** | **11** | 27% (3/11) | **+12.50** |

June, July, August: **no labeled session** → every cell is n=0 there. `Trend_DD`, `Normal_Variation`, `Neutral_Center`, `Neutral_Extreme`, `Nontrend`, `Nonconviction` never appear as the dominant 17:30–20:00 label in the 11 sessions (`Nontrend` appears as a minority label on 09-22 only, `Neutral_Center` as a minority on 09-24 and 09-28).

## 2 · Session labels (mode of DECISION `day_type`, 17:30–20:00 IL)

| Date | Dominant label | n DECISION | Breakdown |
|---|---|---|---|
| 2026-09-18 | Normal | 21 | Normal=14 Variation=7 |
| 2026-09-21 | Trend_Normal | 25 | Trend_Normal=24 Normal=1 |
| 2026-09-22 | Variation | 44 | Variation=36 Nontrend=8 |
| 2026-09-23 | Trend_Normal | 14 | Trend_Normal=9 Normal=5 |
| 2026-09-24 | Variation | 26 | Variation=22 Trend_Normal=2 Normal=1 Neutral_Center=1 |
| 2026-09-25 | Normal | 42 | Normal=28 Variation=14 |
| 2026-09-28 | Variation | 20 | Variation=13 Trend_Normal=4 Neutral_Center=3 |
| 2026-09-29 | Variation | 45 | Variation=24 Normal=21 |
| 2026-09-30 | Variation | 46 | Variation=32 Normal=14 |
| 2026-10-01 | Variation | 41 | Variation=26 Normal=15 |
| 2026-10-02 | Variation | 42 | Variation=31 Normal=10 Trend_Normal=1 |

The label is not stable inside the window: on 09-29 it is `Variation` 24 vs `Normal` 21; 09-18 and 09-25 split Normal/Variation; 09-23 split Trend/Normal 9/5. The "dominant label" is a majority vote, and in 5 of 11 sessions the runner-up holds ≥ a third of the votes. That is the same problem as 10-05 (`Trend_Normal` → `Normal` → `Trend_Normal`) seen across the sample.

## 3 · Trade log (one row per fill)

Entry/stop/exit rules are in §4. Same-bar stop-and-target → **STOP** (conservative). All fills from raw 5-min bars; two of them (09-21, 09-28) re-checked by hand against the bar dump.

| Date | Label | Cell | Side | In | Entry | Stop | Target | Exit | At | pts | $ | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-18 | Normal | NORMAL | L | 17:30 | 7688.00 | 7686.00 | 7708.25 | STOP | 17:35 | −2.00 | −10.00 | VAL touch on the 17:30 bar; VAH 7718.25 never touched |
| 2026-09-21 | Trend_Normal | TREND | L | 18:30 | 7796.50 | 7795.50 | — | EOD | 20:00 | +24.75 | +123.75 | pullback low 7795.75 (18:25) held by 18:30; never revisited |
| 2026-09-22 | Variation | VARIATION | S | 17:40 | 7829.50 | 7831.50 | — | BACK_IN_IB | 17:45 | −4.25 | −21.25 | first close < ib_low 7831.5; next bar closed back inside |
| 2026-09-23 | Trend_Normal | TREND | S | 19:20 | 7777.75 | 7782.00 | — | EOD | 20:00 | +9.00 | +45.00 | pullback high 7781.75 (19:15) held |
| 2026-09-24 | Variation | VARIATION | S | 18:10 | 7726.50 | 7730.00 | — | BACK_IN_IB | 18:15 | −5.00 | −25.00 | |
| 2026-09-25 | Normal | NORMAL | L | 19:00 | 7801.50 | 7799.50 | 7804.50 | STOP | 19:00 | −2.00 | −10.00 | entry bar low 7794 → stopped same bar; VAH 7809.75 never touched |
| 2026-09-28 | Variation | VARIATION | S | 17:35 | 7753.75 | 7758.75 | — | BACK_IN_IB | 19:20 | −14.50 | −72.50 | stayed below IB 17:35→19:15 (low 7726), then 19:20 closed 7768.25 — gave back the whole move |
| 2026-09-29 | Variation | VARIATION | S | 18:00 | 7731.25 | 7731.75 | — | EOD | 20:00 | +12.50 | +62.50 | the one Variation winner |
| 2026-09-30 | Variation | VARIATION | L | 17:50 | 7780.00 | 7779.50 | — | BACK_IN_IB | 17:55 | −7.25 | −36.25 | |
| 2026-10-01 | Variation | VARIATION | S | 18:00 | 7680.25 | 7682.25 | — | BACK_IN_IB | 18:10 | −7.50 | −37.50 | |
| 2026-10-02 | Variation | VARIATION | S | 18:05 | 7773.25 | 7773.50 | — | BACK_IN_IB | 18:30 | −1.25 | −6.25 | |

What the 11 rows say, without a conclusion attached: both TREND pullbacks paid and ran to 20:00; both NORMAL fades were stopped at −2 pt (one on the entry bar); VARIATION's "with the first extension" lost 6 of 7 because the first close beyond the IB was followed within 1–5 bars by a close back inside — the stop-rule `BEYOND_LEG_EXTREME` in the yaml would have been tighter on some and looser on others, this run used *close back inside IB* as ordered.

## 4 · Rules as implemented (so the numbers can be reproduced)

- **Window / prices.** Bars with IL `ts ∈ [17:30, 20:00)` (30 bars; `ts` is bar open, so the 19:55 bar closes at 20:00). "17:30 price" = open of the 17:30 bar. "20:00 close" = close of the 19:55 bar.
- **Label.** Mode of `vector->>'day_type'` over `DECISION` rows with IL time in [17:30, 20:00]; nulls excluded; ties → first-seen. This uses the whole window to pick the row, i.e. it knows at 17:30 what the label will mostly be by 20:00 — a look-ahead, as ordered.
- **VA/IB.** End-of-day CASH row (`closed_ts` is NULL on all of them; `ib_locked=1`). VAH/VAL are the final values, not the 17:30 values — a second look-ahead, as ordered.
- **TREND.** Direction = sign(20:00 close − 17:30 open) (look-ahead, as ordered). Entry = close of the bar that *confirms* the first pullback: bar *i* with `low[i] < low[i−1]`, `low[i] > p17:30`, and `low[i+1] ≥ low[i]`; enter at `close[i+1]`; stop = `low[i] − 0.25`. Mirror for shorts. Exit at stop (fill at stop) or 20:00 close. No pullback → no trade (did not occur).
- **NORMAL.** SHORT: first bar with `high ≥ vah` and `low < vah` → fill at `vah`, stop `vah+2`, target `poc`. LONG: mirror at `val`. Entry bar's own range is checked (stop first). Each side at most once per session. If `poc` is not on the profit side of the entry (10-01: vah 7730.25 / val 7727.75 / poc 7727.75) the fill would be marked DEGENERATE at $0 — did not trigger because 10-01 was labeled Variation.
- **VARIATION.** First bar with `close > ib_high` or `close < ib_low` → enter at that close, with it. Stop = first subsequent **close** back inside the IB, exit at that close. Else 20:00 close. "Target poc if it returns": for a with-extension leg the POC is inside the IB, i.e. on the stop side of the entry — it cannot be reached before the stop, so it never acts as a target here. The VALUE_RETURN leg (fade back to POC after the stop-out) was **not** scored; it is a second trade the order did not ask for.
- **NEUTRAL.** SHORT at `ib_high` touch (stop +2, target `(ib_high+ib_low)/2`), LONG at `ib_low` touch (stop −2, target mid). Same touch/fill rules as NORMAL. n=0 sessions.
- **NONTREND.** Zero trades. Cost-of-standing-down = the NORMAL VAH/VAL fade scored but flagged NOT TRADED. n=0 sessions, so there is no number; nothing is recommended either way.
- **Money.** pts × $5 × 1 contract. No commission, no slippage, fills at level/close.

## 5 · Data notes (not conclusions)

1. **Label coverage is the blocker, not the playbook.** The 65-session sample Michael asked for exists in bars and TPO rows; it does not exist in `DECISION` labels before 09-17. Running this matrix on 54 more sessions needs a label source for June–mid-September — either a replay that writes `DECISION` rows (harness, out of scope today) or `v9_day_type_history` (one row per date, 107 rows, end-of-day label, no intra-session flip). I did not use the latter because the order named the source. If Michael rules "use `v9_day_type_history` for pre-09-17", the same script runs on all 65 in one pass.
2. **VA rows that look wrong.** 10-01: `vah 7730.25 / poc 7727.75 / val 7727.75` (2.5-pt value area, VAL = POC). 09-25: VA 7801.5–7809.75 sits entirely **above** IB 7752.75–7793.75, and the bar series jumps 7774.75 → 7799.25 between 18:50 and 18:55 (24.5 pt in one bar; check for a missing bar or a feed gap). 10-05: `val = poc = ib_low = 7778.25`. Rule 2 says verify before trusting — these three rows are flagged, not corrected.
3. **One CASH TPO row missing** (07-16). One duplicate CASH row (06-04, not in the session list).
4. Nothing was edited: no yaml, no `.env`, no harness run, no restart, no commit. Only this file was written.

## 6 · Verification quote (Rule 5)

```
$ python3 /tmp/daytype_matrix.py | tail -14
| cell | month | sessions | trades | wins | win% | Σ$ |
| TREND | 2026-09 | 2 | 2 | 2 | 100% | +168.75 |
| **TREND** | **ALL** | 2 | 2 | 2 | 100% | +168.75 |
| NORMAL | 2026-09 | 2 | 2 | 0 | 0% | -20.00 |
| **NORMAL** | **ALL** | 2 | 2 | 0 | 0% | -20.00 |
| VARIATION | 2026-09 | 5 | 5 | 1 | 20% | -92.50 |
| VARIATION | 2026-10 | 2 | 2 | 0 | 0% | -43.75 |
| **VARIATION** | **ALL** | 7 | 7 | 1 | 14% | -136.25 |
| **NEUTRAL** | **ALL** | 0 | 0 | 0 | n/a | +0.00 |
| **NONTREND_naive_fade** | **ALL** | 0 | 0 | 0 | n/a | +0.00 |

unlabeled sessions: 54  -> 2026-06-15 ... 2026-09-15
```

Hand check 09-21 TREND from the raw bar dump: 17:30 open 7788.00; 18:25 low 7795.75 < 18:20 low 7796.75 and > 7788; 18:30 low 7796.00 ≥ 7795.75 → entry 18:30 close 7796.50, stop 7795.50; no later low ≤ 7795.50; 19:55 close 7821.25 → +24.75 pt = +$123.75. ✓
Hand check 09-28 VARIATION: ib_low 7758.75; 17:35 close 7753.75 (first close below) → short 7753.75; closes stay < 7758.75 through 19:15 (7755.50); 19:20 close 7768.25 → −14.50 pt = −$72.50. ✓
