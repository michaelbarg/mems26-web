# Final-HEAD forward harness — decisive test before tonight's restart · 2026-09-10

Run by: cowork-dev agent (this session). Live tree read-only throughout — no edit, no `.env` change, no
restart, no flag change. HEAD tested: `7eba412d` "channel: dalton{} display block reported" (contains
fixes 1-7, fix 5b, §8 golden gate, dalton{} display block). Machine: `MacBarg.local` (Darwin 24.5.0),
local Postgres (`postgresql://localhost/mems26`), same machine that trades. All commands below ran via
Desktop Commander against the real Mac shell — not the Cowork Linux sandbox (verified first: sandbox has
no reachable Postgres and is a different kernel; this task requires the real local DB + live venv).

---

## TASK A — six-session harness run

Worktree: `git worktree add /tmp/mems26_final HEAD` → `7eba412d` (same as live HEAD). Harness copied to
`/tmp/mems26_final/scripts/fwd_harness.py` (its `ROOT` is two `dirname()` calls above its own path, so it
must live at `<repo>/scripts/` to resolve correctly — confirmed against `fwd_run_batch.sh`'s own layout
from this morning's run). `fwd_apply_fixes.py` was **not** run (HEAD already has the fixes — running it
would double-apply). Env: `set -a && . .env && set +a`, plus explicit `export DALTON_PLAYBOOK_V1=1
DAYTYPE_RECLASS_STABILITY_V1=1`.

Command per session (`--variant finalhead --stability 1 --push-mode firstpush`):
```
nice -n 10 python3 scripts/fwd_harness.py --session <S> --variant finalhead --stability 1 \
  --push-mode firstpush --out /tmp/fwd_out_final/<tag>_finalhead_s1_firstpush.json \
  2>/tmp/fwd_out_final/<tag>_finalhead_s1_firstpush.log
```
One operational note: the first batched run (all 6 sessions in one shell loop) hit a Desktop-Commander
round-trip timeout after ~99s; the parent bash process died between iterations, but the 5 sessions it had
already spawned finished cleanly (orphaned children keep running after a killed parent on Unix). Session
2026-09-01 never started under that parent and was re-run individually (succeeded, exit=0). All 6 `.json`
outputs are confirmed present and structurally valid (checked below).

### T1 — verdict table (push=firstpush, stability=1 — live cadence, $=harness tape score 5$/pt)

| session | routes | fires / T1-first / $ (final HEAD) | HEAD+fixes this morning (s=1) | Δ vs this morning | must-rule | verdict |
|---|---|---|---|---|---|---|
| 2026-08-28 | 64 | 0 / 0 / **$0.00** | 1 / 1 / +107.50 | **−107.50 (WORSE)** | phase_a_standaside | PASS |
| 2026-08-03 | 38 | 3 / 3 / **+257.50** | 1 / 1 / +332.50 | **−75.00 (WORSE)** | must_approve #593 (with-drive 17:10) | **FAIL — now blocked** |
| 2026-09-02 | 49 | 1 / 1 / **+70.00** | 3 / 0 / −180.00 | +250.00 (better) | phase_a_standaside | PASS |
| 2026-08-04 | 20 | 0 / 0 / **$0.00** | 1 / 1 / +427.50 | **−427.50 (WORSE)** | must_approve #612 (REACTIVE_LONG 17:05) | **FAIL — now blocked** |
| 2026-09-09 | 49 | 0 / 0 / **$0.00** | 3 / 0 / −290.00 | +290.00 (better) | must_block #1328 + #1343 | PASS (both blocked) |
| 2026-09-01 | 36 | 1 / 0 / **−156.25** | 3 / 2 / +110.00 | **−266.25 (WORSE)** | phase_a_standaside | PASS |

**4 of 6 sessions score worse than this morning's HEAD+fixes $ column** (08-28, 08-03, 08-04, 09-01).
Only 09-02 and 09-09 improved. This violates the task's explicit acceptance rule ("no session worse than
the morning's HEAD+fixes $ column").

### Must-rule detail (exact reason strings, from the harness JSON)

**09-09 must block #1328 (VEGAS LONG 19:05) and #1343 (BULL_FLAG LONG 20:55):**
```
19:05:04 S4 [INJECTED live#1328 STOP_HIT $-40.0] VEGAS LONG e=7643.25 st=7639.25 t1=7652.25
  | ot=OPEN_DRIVE dt=Variation hint=SHORT bias=SHORT kinds=['BREAK','VALUE_RETURN'] sf=1.0
  | dalton_intent:bias bias=SHORT rejects LONG (phase=C cond=day_type in [Variation, Normal_V...
20:55:07 S2 [INJECTED live#1343 STOP_HIT $-137.5] BULL_FLAG_LONG LONG e=7652.5 st=7647.25 t1=7657.0
  | ot=OPEN_DRIVE dt=Variation hint=SHORT bias=SHORT kinds=['BREAK','VALUE_RETURN'] sf=1.0
  | dalton_intent:bias bias=SHORT rejects LONG (phase=C cond=day_type in [Variation, Normal_V...
```
Both blocked, both carry `bias=SHORT` as required. **Note:** the task text anticipated a
`dalton_intent:kind` reason; the actual verdict code is `dalton_intent:bias` (a bias mismatch, not a kind
mismatch). `config/forward_gate_golden.yaml`'s own `must_block` assertion does not specify a reason code,
only that the trade be blocked — so this is a PASS against the actual golden contract, with the caveat
that the reason category differs from what was anticipated. (Bonus: trade #1337 DOUBLE_BOTTOM_EE_LONG —
the T-290 phantom win — is also now blocked the same way, not a required assertion but consistent.)

**08-03 must approve the with-drive 17:10 entry (golden `must_approve trade_id: 593`):**
```
17:10:03 S2 INITIATIVE_LONG LONG e=7587.5 st=7538.75 t1=7660.625 | ot=OPEN_DRIVE dt=Trend_Normal
  hint=None bias=BOTH kinds=['PULLBACK','WITH_DRIVE'] sf=1.0
  | dalton_intent:kind counter-bias entry_kind=BREAK not in ['PULLBACK','WITH_DRIVE'] (phase...
17:10:03 S2 [INJECTED live#593 T2_HIT $71.25] REACTIVE_LONG LONG e=7588.0 st=7588.25 t1=7594.25
  | ot=OPEN_DRIVE dt=Trend_Normal hint=None bias=BOTH kinds=['PULLBACK','WITH_DRIVE'] sf=1.0
  | dalton_intent:kind counter-bias entry_kind=EDGE_FADE not in ['PULLBACK','WITH_DRIVE'] (phase...
```
**FAIL.** This morning's HEAD+fixes run had `hint=LONG` at this timestamp (from fix 1's bar-3 canonical
opening direction); this run has `hint=None`, so `bias=BOTH` instead of `LONG`, so BREAK/EDGE_FADE fall
outside the allowed kinds and both routes are blocked. Trade #593 itself is directly blocked.

**08-04 must approve REACTIVE_LONG 17:05 (golden `must_approve trade_id: 612`):**
```
17:05:03 S2 [INJECTED live#612 T3_HIT $158.75] REACTIVE_LONG LONG e=7690.75 st=7691.0 t1=7697.5
  | ot=OPEN_DRIVE dt=Trend_Normal hint=None bias=BOTH kinds=['PULLBACK','WITH_DRIVE'] sf=1.0
  | dalton_intent:kind counter-bias entry_kind=EDGE_FADE not in ['PULLBACK','WITH_DRIVE'] (phase...
```
**FAIL.** Same mechanism: `hint=None` where this morning it was `LONG`. 08-04 finishes at $0.00 instead
of the morning's +427.50 — the entire session's result depended on this one admission.

**Phase-A stand-aside, 6/6:** confirmed — no `LIVE→CMD`/`LIVE CMD` route has `il < 16:45` in any of the
six JSONs (every phase-A route is either `dalton_intent:stand_down` or a `dalton_intent:kind`/
`entry_location_quality` block). PASS on 6/6.

### Exception scan (Traceback / dalton_playbook failed / fail-closed / dalton_intent:error / ImportError / KeyError / TypeError)

```
0828: 0   (log 1695 lines)
0803: 0   (log 1006 lines)
0902: 0   (log 1449 lines)
0804: 0   (log 607 lines)
0909: 0   (log 1581 lines)
0901: 0   (log 1216 lines)
grep exit code: 1 (no matches in any log)
```
**0 exceptions across all six sessions.** Fix 5b's `ext_up`/`ext_dn` code does **not** fail-closed; the
zero-fire sessions (08-28, 08-04, 09-09) are zero because every candidate was individually blocked by a
gate verdict (`dalton_intent:kind`/`dalton_intent:bias`/`entry_location_quality`), not because the
playbook crashed. JSON sanity (session id, routes/trades counts, `flags.DALTON_PLAYBOOK_V1=1`,
`flags.DAYTYPE_RECLASS_STABILITY_V1=1`) checked and correct on all 6 files.

### Golden-gate cross-check — important divergence

`python3 scripts/forward_gate.py` (run from the live tree, read-only) reports:
```
✅ 2026-08-28: 8t 1A ot=OPEN_AUCTION_IN Σ$+0.00 | phase_a_standaside: PASS (0 fires)
✅ 2026-08-03: 9t 7A ot=OPEN_DRIVE Σ$+172.50 | must_approve #593: PASS
✅ 2026-09-02: 4t 2A ot=OPEN_AUCTION_IN Σ$+76.25 | phase_a_standaside: PASS (0 fires)
✅ 2026-08-04: 5t 5A ot=OPEN_AUCTION_IN Σ$+477.50 | phase_a_standaside: PASS (0 fires) · must_approve #612: PASS
✅ 2026-09-09: 2t 0A ot=OPEN_AUCTION_IN Σ$+0.00 | phase_a_standaside: PASS (0 fires) · must_block #1328: PASS · must_block #1343: PASS
✅ 2026-09-01: 3t 1A ot=OPEN_AUCTION_IN Σ$-128.75 | phase_a_standaside: PASS (0 fires)

FORWARD_GATE: PASS — 6 sessions   (exit=0)
```
This is a **full PASS, including #593 and #612 — directly contradicting the harness above.** Reading
`scripts/forward_gate.py` explains why: it does **not** call `backend/v9/gateway/trading_gateway.py` at
all. It replays real `v9_trades` rows through `dalton_playbook.intent()/evaluate_gate()` directly, using
its **own separate, inline reimplementation** of opening-type detection, day-type classification, and the
direction hint (including its own copy of "5b: IB extension direction", `forward_gate.py:119-130`) — and
that reimplementation still gives phase-B (`il_hhmm < 17:30`) a hint straight from the opening-type
detector's direction (`forward_gate.py:131-132`, `elif ot_dir: dir_hint = ...`), i.e. it still behaves
like **this morning's** fix 1, not like the current `trading_gateway.py`. The two code paths have
diverged. This is not new information invented here — commit `45aa3034` (this morning, before 5b shipped)
already flagged it in its own message: *"§8 rejected (forward_gate imports prove it is the replay, golden
has no must_block)"*. That caution was not carried forward into the later commits
(`c42df62d`/`7c2b17e2`) that shipped 5b and declared "golden gate PASS 6/6" as supporting evidence — and
`forward_gate.py`'s PASS is exactly the false signal that caution warned about. The harness in this report
is the one that runs the actual `trading_gateway.py` code (`TradingGateway.route_setup`, the real hot
path); its FAIL on #593/#612 is the one that reflects what will actually happen on a restart.

### Full per-setup detail (routes + trades, all 6 sessions)

Rendered with `fwd_show.py <json> all`. Format per route: `IL system classification direction
e=entry st=stop t1=t1 | ot=<_dp_ot> dt=<_dp_day_type> hint=<_dp_dir_hint> bias=<playbook bias>
kinds=<allowed kinds> sf=<size_frac> | blocked_by reason [exec/shadow]`.

```
############################################
== 2026-08-28 finalhead push=firstpush stability=1 bars=78 pd_ctx={'pd_high': 7755.75, 'pd_low': 7702.75, 'pd_close': 7732.75, 'pd_context_status': 'OK'} prev_tpo={'found': True, 'poc': 7736.75, 'vah': 7746.5, 'val': 7736.75}
-- routes --
  16:30:03 S4 GB100                  SHORT e=7746.25 st=7750.25 t1=7731.5 | ot=UNKNOWN dt= hint=None bias=NONE kinds=[] sf=0.0 | dalton_intent:stand_down phase=A cond=default bias=NONE
  16:30:03 S2 DALTON_EDGE_LONG       LONG  e=7746.25 st=7740.75 t1=7751.75 | ot=UNKNOWN dt= hint=None bias=NONE kinds=[] sf=0.0 | dalton_intent:stand_down phase=A cond=default bias=NONE
  16:35:03 S2 FAILED_BREAK_LONG      LONG  e=7749.5 st=7741.25 t1=7757.75 | ot=UNKNOWN dt= hint=None bias=NONE kinds=[] sf=0.0 | dalton_intent:stand_down phase=A cond=default bias=NONE  [shadow_only]
  16:39:58 S4 ZLR                    LONG  e=7751.5 st=7736.5 t1=7774.0 | ot=UNKNOWN dt= hint=None bias=NONE kinds=[] sf=0.0 | dalton_intent:stand_down phase=A cond=default bias=NONE
  16:44:58 S4 GB100                  LONG  e=7754.75 st=7739.75 t1=7777.25 | ot=OPEN_DRIVE dt= hint=None bias=BOTH kinds=['WITH_DRIVE'] sf=0.5 | dalton_intent:kind counter-bias entry_kind=BREAK not in ['WITH_DRIVE'] (phase=A cond=open
  16:50:03 S2 DALTON_EDGE_SHORT      SHORT e=7750.75 st=7760.0 t1=7741.5 | ot=OPEN_DRIVE dt= hint=None bias=BOTH kinds=['PULLBACK', 'WITH_DRIVE'] sf=1.0 | dalton_intent:kind counter-bias entry_kind=REVERSAL not in ['PULLBACK', 'WITH_DRIVE']
  16:54:58 S4 FAMIR                  SHORT e=7746.25 st=7758.25 t1=7731.5 | ot=OPEN_DRIVE dt= hint=None bias=BOTH kinds=['PULLBACK', 'WITH_DRIVE'] sf=1.0 | dalton_intent:kind counter-bias entry_kind=BREAK not in ['PULLBACK', 'WITH_DRIVE']
  16:55:03 S2 FAILED_BREAK_SHORT     SHORT e=7746.25 st=7758.25 t1=7734.25 | ot=OPEN_DRIVE dt= hint=None bias=BOTH kinds=['PULLBACK', 'WITH_DRIVE'] sf=1.0 | dalton_intent:kind counter-bias entry_kind=EDGE_FADE not in ['PULLBACK', 'WITH_DRIVE']  [shadow_only]
  16:59:58 S4 HTLB                   LONG  e=7747.0 st=7727.5 t1=7776.25 | ot=OPEN_DRIVE dt= hint=None bias=BOTH kinds=['PULLBACK', 'WITH_DRIVE'] sf=1.0 | dalton_intent:kind counter-bias entry_kind=BREAK not in ['PULLBACK', 'WITH_DRIVE']
  17:04:58 S4 ZLR                    SHORT e=7746.0 st=7761.0 t1=7731.5 | ot=OPEN_DRIVE dt=Trend_Normal hint=None bias=BOTH kinds=['PULLBACK', 'WITH_DRIVE'] sf=1.0 | dalton_intent:kind counter-bias entry_kind=BREAK not in ['PULLBACK', 'WITH_DRIVE']
  17:05:03 S4 [INJECTED live#838 phantom_reconcile $107.5] ZLR SHORT e=7746.5 st=7746.5 t1=7738.25 | ot=OPEN_DRIVE dt=Trend_Normal hint=None bias=BOTH kinds=['PULLBACK', 'WITH_DRIVE'] sf=1.0 | dalton_intent:kind counter-bias entry_kind=BREAK not in ['PULLBACK', 'WITH_DRIVE']
  17:09:58 S4 GB100                  SHORT e=7738.75 st=7753.75 t1=7716.25 | ot=OPEN_DRIVE dt=Trend_Normal hint=None bias=BOTH kinds=['PULLBACK', 'WITH_DRIVE'] sf=1.0 | dalton_intent:kind counter-bias entry_kind=BREAK not in ['PULLBACK', 'WITH_DRIVE']
  17:10:03 S4 [INJECTED live#840 phantom_reconcile $56.25] SCALE_IN SHORT e=7738.75 st=7738.5 t1=7726.5 | ot=OPEN_DRIVE dt=Trend_Normal hint=None bias=BOTH kinds=['PULLBACK', 'WITH_DRIVE'] sf=1.0 | dalton_intent:kind counter-bias entry_kind=BREAK not in ['PULLBACK', 'WITH_DRIVE']
  17:15:03 S4 [INJECTED live#841 STOP_FILL $-70.0] SCALE_IN SHORT e=7731.0 st=7738.62 t1=7719.57 | ot=OPEN_DRIVE dt=Trend_Normal hint=None bias=BOTH kinds=['PULLBACK', 'WITH_DRIVE'] sf=1.0 | dalton_intent:kind counter-bias entry_kind=BREAK not in ['PULLBACK', 'WITH_DRIVE']
  17:24:58 S4 ZLR                    LONG  e=7744.5 st=7729.5 t1=7760.5 | ot=OPEN_DRIVE dt=Trend_Normal hint=None bias=BOTH kinds=['PULLBACK', 'WITH_DRIVE'] sf=1.0 | dalton_intent:kind counter-bias entry_kind=BREAK not in ['PULLBACK', 'WITH_DRIVE']
  17:29:58 S4 ZLR                    SHORT e=7742.0 st=7757.0 t1=7726.5 | ot=OPEN_DRIVE dt=Variation hint=None bias=BOTH kinds=['PULLBACK', 'WITH_DRIVE'] sf=1.0 | dalton_intent:kind counter-bias entry_kind=BREAK not in ['PULLBACK', 'WITH_DRIVE']
  17:30:03 S2 DOUBLE_TOP_AA_SHORT    SHORT e=7742.0 st=7764.5 t1=7734.25 | ot=OPEN_DRIVE dt=Variation hint=None bias=BOTH kinds=['BREAK', 'VALUE_RETURN'] sf=1.0 | entry_location_quality expensive_stop: rr=2.28 > 1.50 (stop 22.5 vs ATR 9.9); beyond_value
  17:39:58 S4 ZLR                    LONG  e=7752.25 st=7737.25 t1=7774.75 | ot=OPEN_DRIVE dt=Variation hint=LONG bias=LONG kinds=['BREAK', 'VALUE_RETURN'] sf=1.0 | entry_location_quality expensive_stop: rr=1.52 > 1.50 (stop 15.0 vs ATR 9.9)
  18:30:03 S2 REACTIVE_LONG          LONG  e=7779.0 st=7734.0 t1=7846.5 | ot=OPEN_DRIVE dt=Variation hint=LONG bias=LONG kinds=['BREAK', 'VALUE_RETURN'] sf=1.0 | entry_location_quality expensive_stop: rr=4.57 > 1.50 (stop 45.0 vs ATR 9.9); beyond_value
  18:40:03 S2 VA_FADE_SHORT          SHORT e=7765.75 st=7777.0 t1=7754.5 | ot=OPEN_DRIVE dt=Variation hint=LONG bias=LONG kinds=['BREAK', 'VALUE_RETURN'] sf=1.0 | dalton_intent:bias bias=LONG rejects SHORT (phase=C cond=day_type in [Variation, Normal_V  [shadow_only]
  18:55:03 S2 INITIATIVE_SHORT       SHORT e=7750.0 st=7786.5 t1=7695.25 | ot=OPEN_DRIVE dt=Variation hint=LONG bias=LONG kinds=['BREAK', 'VALUE_RETURN'] sf=1.0 | dalton_intent:bias bias=LONG rejects SHORT (phase=C cond=day_type in [Variation, Normal_V
  19:00:03 S2 INITIATIVE_SHORT       SHORT e=7739.75 st=7786.5 t1=7669.625 | ot=OPEN_DRIVE dt=Variation hint=LONG bias=LONG kinds=['BREAK', 'VALUE_RETURN'] sf=1.0 | dalton_intent:bias bias=LONG rejects SHORT (phase=C cond=day_type in [Variation, Normal_V
  19:01:14 S2 [INJECTED live#853 STOP_HIT $60.0] SCALE_IN SHORT e=7736.0 st=7735.5 t1=7724.25 | ot=OPEN_DRIVE dt=Variation hint=LONG bias=LONG kinds=['BREAK', 'VALUE_RETURN'] sf=1.0 | dalton_intent:bias bias=LONG rejects SHORT (phase=C cond=day_type in [Variation, Normal_V
  (... 64 routes total; full 87-line dump in /tmp/fwd_out_final/0828_finalhead_s1_firstpush.json / re-render with fwd_show.py for the complete list)
  counts: {'dalton_intent:stand_down': 20, 'dalton_intent:kind': 24, 'entry_location_quality': 11, '-': 2, 'dalton_intent:bias': 7}
-- harness trades (scored vs tape) --
  (none fired)
  daily_pnl_harness: 0.0
  ** KEY REGRESSION: 19:01:14 SCALE_IN SHORT (injected live#853, the day's actual +$107.50 live winner) is
  now blocked by dalton_intent:bias (bias=LONG rejects SHORT) — this morning's HEAD+fixes admitted it
  (LIVE CMD) and scored +107.50. bias=LONG is now sticking all the way to 19:01 on an OPEN_DRIVE/UP day
  that reversed intraday — the same 5+5b mechanism that correctly locks bias=SHORT for 09-09 also locks
  a stale bias=LONG here for 2.5 hours past when the drive reversed.
############################################
== 2026-08-03 finalhead push=firstpush stability=1 bars=78
-- routes (16:30-17:15 excerpt; hint=None throughout where this morning's HEAD+fixes had hint=LONG from 16:45:09) --
  16:35:21 S4 [INJECTED live#588 T2_HIT $83.75] HTLB LONG e=7563.5 st=7563.75 t1=7568.75 | ot=UNKNOWN hint=None bias=NONE | dalton_intent:stand_down phase=A
  16:45:09 S4 [INJECTED live#591 STOP_HIT $-20.0] ZLR LONG e=7569.5 st=7565.75 t1=7572.5 | ot=OPEN_DRIVE hint=None bias=BOTH kinds=['PULLBACK','WITH_DRIVE'] | dalton_intent:kind counter-bias entry_kind=BREAK not in [...]
  17:05:03 S2 DALTON_EDGE_SHORT SHORT e=7585.75 st=7593.25 t1=7578.25 | ot=OPEN_DRIVE hint=None bias=BOTH | dalton_intent:kind counter-bias entry_kind=REVERSAL not in [...]
  17:10:03 S2 INITIATIVE_LONG  LONG  e=7587.5  st=7538.75 t1=7660.625 | ot=OPEN_DRIVE hint=None bias=BOTH | dalton_intent:kind counter-bias entry_kind=BREAK not in [...]   <-- golden #593-equivalent, BLOCKED
  17:10:03 S2 [INJECTED live#593 T2_HIT $71.25] REACTIVE_LONG LONG e=7588.0 st=7588.25 t1=7594.25 | ot=OPEN_DRIVE hint=None bias=BOTH | dalton_intent:kind counter-bias entry_kind=EDGE_FADE not in [...]   <-- golden #593, BLOCKED
  18:20:06 S4 [INJECTED live#601 T2_HIT $53.75] GB100 LONG e=7606.0 | ot=OPEN_DRIVE dt=Trend_Normal hint=LONG bias=LONG kinds=['BREAK','PULLBACK'] | - LIVE→CMD n=5 tgt=7609.0 t2=7608.75 t3=7628.5
  19:20:03 S4/S4 CONFLUENCE_RI_ZLR LONG e=7614.0 | hint=LONG bias=LONG | - LIVE→CMD n=2 tgt=7618.0
  20:15:03 S2 INITIATIVE_LONG LONG e=7616.75 | hint=LONG bias=LONG | - LIVE→CMD n=5 tgt=7619.75 t2=7620.25 t3=7639.25
  counts: {'dalton_intent:stand_down': 12, 'dalton_intent:kind': 5, '-': 6, 'entry_location_quality': 10, 'dalton_intent:bias': 2, 'entry_not_confirmed': 1, 'live:live_slot_occupied': 2}
-- harness trades (scored vs tape) --
  FWD-live-4 GB100 LONG fired=18:20:06 e=7606.0 n=5 -> WIN $28.75 t1_first=True
  FWD-live-7 CONFLUENCE_RI_ZLR LONG fired=19:20:03 e=7614.0 n=2 -> WIN $20.0 t1_first=True
  FWD-live-10 INITIATIVE_LONG LONG fired=20:15:03 e=7616.75 n=5 -> WIN $208.75 t1_first=True
  daily_pnl_harness: 257.5
############################################
== 2026-09-02 finalhead push=firstpush stability=1 bars=78
-- routes (excerpt) --
  16:30:03 S2 DALTON_EDGE_SHORT SHORT e=7650.25 | ot=UNKNOWN hint=None bias=NONE | dalton_intent:stand_down phase=A
  16:44:58 S4 GB100 LONG e=7654.25 | ot=OPEN_DRIVE hint=None bias=BOTH kinds=['WITH_DRIVE'] | dalton_intent:kind counter-bias entry_kind=BREAK not in ['WITH_DRIVE'] (phase=A)
  17:30:04 S2 [INJECTED live#955 SIERRA_FLAT] SCALE_IN LONG e=7679.5 | ot=OPEN_DRIVE dt=Trend_Normal hint=LONG bias=LONG kinds=['BREAK','PULLBACK'] | rr_entry_gate T1_dist=3.00 < stop_dist=6.25 x min=0.65
  20:50:03 S2 REACTIVE_LONG LONG e=7676.5 st=7666.0 t1=7692.25 | ot=OPEN_DRIVE dt=Variation hint=LONG bias=LONG kinds=['BREAK','VALUE_RETURN'] | - LIVE→CMD n=5 tgt=7679.5 t2=7681.5 t3=7682.5 t4=7690.5
  counts: {'dalton_intent:stand_down': 9, 'dalton_intent:kind': 7, 'rr_entry_gate': 3, 'entry_location_quality': 12, 'dalton_intent:bias': 12, 'entry_not_confirmed': 3, '-': 3}
-- harness trades --
  FWD-live-5 REACTIVE_LONG LONG fired=20:50:03 e=7676.5 n=5 -> WIN $70.0 t1_first=True
  daily_pnl_harness: 70.0
############################################
== 2026-08-04 finalhead push=firstpush stability=1 bars=41
-- routes (excerpt) --
  16:30:03 S4 GB100 LONG e=7657.5 | ot=UNKNOWN hint=None bias=NONE | dalton_intent:stand_down phase=A
  17:05:03 S2 [INJECTED live#612 T3_HIT $158.75] REACTIVE_LONG LONG e=7690.75 st=7691.0 t1=7697.5 | ot=OPEN_DRIVE dt=Trend_Normal hint=None bias=BOTH kinds=['PULLBACK','WITH_DRIVE'] | dalton_intent:kind counter-bias entry_kind=EDGE_FADE not in [...]   <-- golden #612, BLOCKED
  17:10:03 S2 INITIATIVE_LONG LONG e=7695.5 | ot=OPEN_DRIVE hint=None bias=BOTH | dalton_intent:kind counter-bias entry_kind=BREAK not in [...]
  17:35:00 S2 [INJECTED live#615 T3_HIT $170.0] REACTIVE_LONG LONG e=7700.75 | ot=OPEN_DRIVE dt=Variation hint=LONG bias=LONG kinds=['BREAK','VALUE_RETURN'] | - LIVE→REJECTED(ValueError: PLACE refused for trade FWD-live-3: effective contracts=0)
  counts: {'dalton_intent:stand_down': 1, 'dalton_intent:kind': 4, '-': 1, 'entry_location_quality': 12, 'entry_not_confirmed': 1, 'structural_targets_wrong_side': 1}
-- harness trades --
  (none fired)
  daily_pnl_harness: 0.0
  ** Note: the one route that DID get hint=LONG (17:35 REACTIVE_LONG, injected live#615) was admitted by
  dalton_intent but rejected downstream by command_from_setup with "effective contracts=0" — a sizing-path
  rejection, not a golden-gate item, logged for completeness only.
############################################
== 2026-09-09 finalhead push=firstpush stability=1 bars=78
-- routes (excerpt around the two must-block trades) --
  16:30:03 S4 GB100 LONG e=7660.5 | ot=UNKNOWN hint=None bias=NONE | dalton_intent:stand_down phase=A
  17:34:58 S4 ZLR LONG e=7657.75 | ot=OPEN_DRIVE dt=Variation hint=SHORT bias=SHORT kinds=['BREAK','VALUE_RETURN'] | dalton_intent:bias bias=SHORT rejects LONG (phase=C cond=day_type in [Variation, Normal_V...
  19:05:04 S4 [INJECTED live#1328 STOP_HIT $-40.0] VEGAS LONG e=7643.25 st=7639.25 t1=7652.25 | ot=OPEN_DRIVE dt=Variation hint=SHORT bias=SHORT kinds=['BREAK','VALUE_RETURN'] | dalton_intent:bias bias=SHORT rejects LONG (phase=C ...)   <-- BLOCKED, bias=SHORT present
  20:15:07 S2 [INJECTED live#1337 BRACKET_EXIT_ACTIVITY $30.0] DOUBLE_BOTTOM_EE_LONG LONG e=7651.25 | hint=SHORT bias=SHORT | dalton_intent:bias bias=SHORT rejects LONG   <-- also blocked (T-290 phantom win, not a golden item)
  20:55:07 S2 [INJECTED live#1343 STOP_HIT $-137.5] BULL_FLAG_LONG LONG e=7652.5 st=7647.25 t1=7657.0 | ot=OPEN_DRIVE dt=Variation hint=SHORT bias=SHORT kinds=['BREAK','VALUE_RETURN'] | dalton_intent:bias bias=SHORT rejects LONG (phase=C ...)   <-- BLOCKED, bias=SHORT present
  counts: {'dalton_intent:stand_down': 15, 'dalton_intent:kind': 12, 'dalton_intent:bias': 12, '-': 2, 'entry_location_quality': 8}
-- harness trades --
  (none fired)
  daily_pnl_harness: 0.0
############################################
== 2026-09-01 finalhead push=firstpush stability=1 bars=78
-- routes (excerpt) --
  16:34:58 S4 ZLR SHORT e=7646.5 | ot=UNKNOWN hint=None bias=NONE | dalton_intent:stand_down phase=A
  19:35:03 S2 [INJECTED live#950 STOP_FILL $-156.25] INITIATIVE_SHORT SHORT e=7643.75 st=7650.0 t1=7638.5 | ot=OPEN_DRIVE dt=Variation hint=SHORT bias=SHORT kinds=['BREAK','VALUE_RETURN'] | - LIVE→CMD n=5 tgt=7640.75 t2=7638.5 t3=7638.0 t4=7541.75
  counts: {'dalton_intent:stand_down': 8, 'dalton_intent:kind': 7, 'dalton_intent:bias': 6, 'entry_location_quality': 14, '-': 1}
-- harness trades --
  FWD-live-3 INITIATIVE_SHORT SHORT fired=19:35:03 e=7643.75 fill=7643.75 stop=7650.0 n=5 -> STOP $-156.25 exit=19:40 t1_first=False amb=0
    L1..L5: STOP@7650.0(-6.25) x5
  daily_pnl_harness: -156.25
```
(Full un-truncated routes list for every session is reproducible with `fwd_show.py <json> all` against
`/tmp/fwd_out_final/*.json` while that scratch directory exists on the Mac — it was left in place, only
the two git worktrees were removed per instructions.)

---

## TASK B — boot smoke on HEAD (live repo root, env loaded)

```
$ python3 -c "import backend.main; print('boot-import OK')"
[env_loader] applied 0 vars from .../.env | HFE_DISABLED=1 NONTREND_DISABLE_ALL=1 DIRECTION_LSMA_VETO=1 S1_NEW_CLASSIFIER=1 ZLR_SPEC_V2=1 VEGAS_SPEC_V2=1 DAYTYPE_POSITION_GATE=0 DAYTYPE_PLAYBOOK=1
2026-09-10 12:39:03 [INFO] [Pkg8/auth_table_v1] loaded 84 cells from auth_matrix.yaml
2026-09-10 12:39:03 [INFO] [targets_table] loaded 7 day_types from targets.yaml
boot-import OK

$ python3 -c "import backend.v9.api.v9.mobile_monitor, backend.v9.gateway.trading_gateway, backend.v9.services.dalton_playbook; print('modules OK')"
modules OK

$ python3 -m py_compile backend/v9/gateway/trading_gateway.py backend/v9/services/dalton_playbook.py backend/v9/api/v9/mobile_monitor.py scripts/forward_gate.py
py_compile OK (0 errors)
```
**TASK B: PASS.**

---

## TASK C — mutation on fix 5b (does the test bite?)

Fresh worktree `/tmp/mems26_mut` (`7eba412d`). Smallest mutation applied at
`backend/v9/gateway/trading_gateway.py:1174` (right after `_dp_ext_up`/`_dp_ext_dn` are computed):
```python
_dp_ext_up = max(0, _dp_sh - _dp_ibh)
_dp_ext_dn = max(0, _dp_ibl - _dp_sl)
_dp_ext_up = _dp_ext_dn = 0  # MUTATION TEST 2026-09-10: revert 5b hint to None
if _dp_ext_up > _dp_ext_dn and _dp_ext_up > 0:
```
`py_compile` OK on the mutated file.

**Test files used** ("playbook/gateway tests cc added"): the literal `git log --name-only -3 -- backend/v9/tests
tests/v9` only surfaced 4 files, none obviously playbook-related (the last 3 commits touching those paths
were unrelated housekeeping). Widened to the commits that actually touched `trading_gateway.py` /
`dalton_playbook.py` (`git log --name-only -8 -- backend/v9/gateway/trading_gateway.py
backend/v9/services/dalton_playbook.py | grep test` → **empty** — neither the fix-5b commit `c42df62d`
nor the fixes-1-7 commit `f285ee28` touched any test file; `c42df62d`'s full diff is
`trading_gateway.py + forward_gate_golden.yaml + forward_gate.py + replay_dalton_playbook.py` only). Ran
the full named + grep-discovered playbook/gateway/day-type regression set (21 files: `test_dalton_playbook.py`,
`test_elq_gateway_wiring.py`, all of `tests/v9/gateway/`, `test_dalton_edge_compass_exempt.py`,
`test_dalton_ib_break_variation_7501.py`, `test_dalton_playbook_identity.py`,
`test_dalton_require_day_direction_vah.py`, `test_dalton_t2_t3_structural_variation.py`,
`test_dedup_fire_gateway.py`, `test_gateway_block_reason_precise.py`, `test_gateway_decisions_feed.py`,
`test_opening_dalton_gaps.py`, `test_opening_type_gate_gateway.py`, `test_s2_gateway_t3_passthrough.py`,
`test_forward_gate.py`, `test_opening_entry_production_path.py`, `test_re_acceptance_production_path.py`,
`test_daytype_reclass_stability.py`, `test_trading_gateway.py`, `test_s1_dalton_p0.py`,
`test_daytype_playbook_gateway.py`).

**Mutated tree** (`/tmp/mems26_mut`):
```
29 failed, 153 passed, 70 warnings in 5.75s
```
**Baseline — identical command against the unmutated worktree** (`/tmp/mems26_final`, still available
from Task A at the time):
```
29 failed, 153 passed, 70 warnings in 5.91s
```
**The FAILED test list is byte-for-byte identical in both runs** (same 29 test IDs, e.g.
`test_d088_shadow_cluster_guard.py::test_shadow_recorded_when_cluster_guard_active`,
`test_s1_dalton_p0.py::test_p0_1_flag_off_is_not_trend_baseline`, etc. — all pre-existing
fixture/environment failures, unrelated to direction-hint logic). **The mutation added zero new
failures.** No test in the playbook/gateway/day-type suite exercises the code path this mutation touches.

**Replay script:**
```
$ python3 scripts/replay_dalton_playbook.py 2>/dev/null | grep -E "^  2026-09-09|1328|1343"
  2026-09-09: 2t 0A/2R broker=$-177.50 app_broker=$0.00 ot=OPEN_AUCTION_IN(db=OPEN_AUCTION_IN) dt@lock=Normal_Variation
```
Still 0A/2R (both still blocked) **even with the mutation** — the opposite of the task's expectation
("the replay re-approves #1328/#1343"). Investigated why: `scripts/replay_dalton_playbook.py` **never
imports `trading_gateway`** — `grep -n "trading_gateway"` on it returns nothing. It has its **own** inline
copy of the extension-direction logic at `replay_dalton_playbook.py:196-200` (`ext_up = max(0, sess_h -
ib_h)` etc., a third independent reimplementation alongside `trading_gateway.py`'s real one and
`forward_gate.py`'s). Mutating `trading_gateway.py` cannot change `replay_dalton_playbook.py`'s output —
the script is structurally incapable of detecting this mutation, not because the mutation is harmless.

**TASK C verdict: the guard does NOT bite.** Neither the regression-test suite nor the replay script
exercises the mutated code path in `trading_gateway.py`. The only tool that does is `fwd_harness.py`
(Task A above) — and that one shows the un-mutated code already regressing two golden `must_approve`
items relative to this morning's verified baseline. Worktree removed.

---

## Root cause (supporting evidence, not asked for but load-bearing for the verdict)

`trading_gateway.py:1150` unconditionally resets `_dp_dir_hint = None` at the start of the block that
also contains fix 5b (comment at 1144-1149: *"Fix 5+5b (10.09): direction_hint for phase C... Fallback 5b:
IB extension direction... Needed because Normal_Variation (74% of C) has dir_bias=None, which gave BOTH
and let #1328/#1343 through"*). Its only two direction sources are `_resolve_live_cls()`'s `dir_bias`
(from `classify_session`, generally unavailable before IB lock ≈17:30 IL) and the new IB-extension
fallback (needs `cross_context["tpo_system"]` IB high/low populated and nonzero — also generally
unavailable before IB lock). This morning's fix 1 used to feed `_dp_dir_hint` from the canonical
opening-detector's direction as early as bar 3 (~16:45); that assignment is gone from the current
`_dp_ot` block (lines 1094-1136 now only set `_dp_ot`, not `_dp_dir_hint`, for non-`OPENING_*`
classifications) — hence `hint=None` persisting through 16:44-17:20 on 08-03/08-04/08-28/09-01 in this
run, where this morning it was `LONG`. Fix 5+5b closed the phase-C gap (09-09) by design, and — as an
apparently unintended side effect of the same rewrite — reopened the phase-B gap fixes 1-4 had closed
this morning for 08-03/08-04. `forward_gate.py` and `replay_dalton_playbook.py` cannot see this because
both carry their own separate, now-diverged copies of the hint logic.

---

## HARNESS: FAIL — real production-path harness shows 2 golden `must_approve` regressions (#593 08-03, #612 08-04, both now blocked) and 4/6 sessions worse than this morning's HEAD+fixes $ baseline (08-28 −107.50, 08-03 −75.00, 08-04 −427.50, 09-01 −266.25); the 09-09 must-block fix works (0 exceptions, #1328/#1343 correctly blocked with bias=SHORT), but no test or replay tool guards the regression it introduced elsewhere — `forward_gate.py`'s "PASS 6/6" and `replay_dalton_playbook.py`'s clean re-run both come from independent reimplementations that never call the actual `trading_gateway.py` code path, so neither would have caught this before a restart.
