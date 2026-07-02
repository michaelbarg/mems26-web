# CC — Fire-Readiness Audit + Fix (S1/S2/S4 + Pipeline-5) — 2026-07-01

**Owner:** Michael · **Prepared by:** Cowork (live-verified, RTH open 15:0x ET)
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — Rule 5 (paste command + raw output), anti-tautological tests, NOT-DONE.
**Question to answer:** are S1, S2, S4 ready to FIRE, and can **Pipeline-5 (demo execution)** fire **3 contracts with full trade-management**? And a list of everything they still do NOT do.

---

## A · What Cowork already verified LIVE today (evidence — do NOT re-derive, just confirm still true)
| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Services + feed | ✅ backend:8000, frontend:3000, bridge up; feed fresh | `v9_bars_5min_woodies` MAX=22:05 vs now 22:05; both bar tables synced (no source-split) |
| 2 | S1 day-type | ✅ classifying, not UNKNOWN | `v9_day_type_state`: day_type=**Variation**, opening=OPEN_DRIVE, IB=WIDE, stage=B2, lock=LOCKED_LOW_CONF, **conf=0.18** |
| 3 | S2 firing | ✅ detects + emits | today's `[S2] T1Setup emitted`: BULL_FLAG_LONG, REACTIVE_S/L, INITIATIVE — the `'c'`-crash fix (d4363a1) is effective |
| 4 | S4 firing | ✅ detects + routes | `v9_trades` today: ZLR, HTLB, FAMIR, VEGAS; `[Woodies ZLR-TRACE] buf=50` (buffer warm) |
| 5 | Position gate | ✅ `DAYTYPE_POSITION_GATE=0` effective | last restart line 819291 (gate=0); **zero** `blocked_by=daytype_position_gate` in the 24k lines since — earlier blocks are all pre-restart |

**So the SIGNAL side (S1/S2/S4) is fire-ready and firing.** The gaps are all in **Pipeline-5 (execution/management)** + targets.

---

## B · CONFIRMED gaps — "what they still do NOT do" (root-caused, Rule 5)

### GAP-1 · 3 contracts is NOT what reaches Sierra (dead-wiring) 🔴 TRADING-CRITICAL
- **Observed:** emitted setups follow **tier**, not 3: `18:20 BULL_FLAG contracts=2 (tier=LOW)`, `19:55 REACTIVE contracts=2 (tier=MEDIUM)`, HIGH→3. So MED/LOW fires carry **2**.
- **Root cause (traced in code):** the command to Sierra reads `setup["contracts"]` — `backend/v9/services/sierra_command.py:160` (`_sz = setup.get("contracts") …`). For S2 that value is `T1Setup.sizing_contracts`, sourced from **`get_quality_tier_v2`** (Auth Table, tier-based 2/3) in `setup_emitter.py:56`. **`FIXED_CONTRACTS_3` only patches `compute_v2_sizing` (`stop_anchors/sizing.py:84-89`) — a DIFFERENT function that does NOT feed the emitted/executed contracts.** The flag is inert on the real path.
- **Fix:** force 3 at the **single choke point where the command qty is finalized** (`sierra_command.py:160` / the setup's `contracts`), gated by `FIXED_CONTRACTS_3`, for **both** S2 (get_quality_tier_v2 / sizing_contracts) and S4. Remove/keep the compute_v2_sizing patch but do NOT rely on it.
- **Verify (Rule 5):** fire a MED or LOW tier pattern → the written `trade_command.json` shows `"contracts":3`. Paste the JSON.

### GAP-2 · Demo slot never frees (runner never closes) 🔴  → `CC_DEMO_SLOT_RECONCILE_2026-07-01.md`
- **Observed:** only **2** demo trades all day (261 CLOSED, **267 still FILLED/open**); every fire after 267 fell back to `shadow`. `trade_fills.json` + `trade_command.json` are **empty**.
- **Root:** demo runner has no terminal close → single `demo_slot` held forever; `FillPoller` starved (no fills feedback). System can't tell active-vs-closed.
- **Fix:** backend runner-close → `on_trade_close` frees slot; boot + periodic reconcile (PARTIAL + Sierra-flat → close); repair Sierra→`trade_fills.json` feedback.

### GAP-3 · Targets are broken (not structural) 🔴  → `CC_STRUCTURAL_TARGET_RESOLVER_BUILD_2026-07-01.md`
- **Observed live:** ZLR (261) stop **0.25pt**, t1/t2/t3 = +4.75/+9.5/+14.25 (R off a 1-tick stop); HTLB (267) t1 = **−92pt** (unreachable). REACTIVE/INITIATIVE far.
- **Fix:** the structural resolver (swing-completion T1 + day-type C1/C2/C3 + hard caps), flag `STRUCTURAL_TARGETS_V2` OFF/SHADOW.

### GAP-4 · Full per-contract management not uniform across patterns 🔴
- BE-after-T1 (`smart_be`), trail, and runner-close are not proven end-to-end for every pattern (267 runner never closed; only 261 ran C1→C2→C3→BE). **This is the "ניהול עסקה מלא לכל התבניות" requirement** — depends on GAP-1+2+3 landing, then verify one CONT + one REV pattern fully.

### GAP-5 · Restart is not a proven full warm-start 🟡  → P4 in `CC_WORK_QUEUE_2026-07-01.md`
- Woodies buffer hydrates (`buf=50` seen ✓), but day-type/IB, TPO value-area, and **open-trade→slot** re-load on boot are unverified; the legacy malformed-SQLite `_hy_conn` check still errors on boot (noisy).

### GAP-6 · Signal-quality / observability 🟡 (note, not blocker)
- S1 confidence **0.18** (LOCKED_LOW_CONF), `classification` field empty — day-type is weak today; watch that gates keyed on day-type behave.
- Repeated `[StreamHealth] unknown stream: cvd_continuous` / `bars_5min_continuous` warnings — CVD/continuous streams unrecognized by StreamHealth; confirm CVD-dependent logic still gets data.
- Opposite-pattern exit (P3) not built.

---

## C · CC task — re-verify readiness + fix, in order
1. **Confirm A1–A5 still hold** (paste: feed MAX ts, `v9_day_type_state` row, today's `T1Setup emitted` lines, post-restart gate-block count=0).
2. **GAP-1 first (fastest, trading-critical):** wire `FIXED_CONTRACTS_3` to the real command qty (`sierra_command.py` / setup contracts) for S2+S4; test a MED/LOW fire → `trade_command.json` `"contracts":3`. Paste JSON.
3. **GAP-2** slot-reconcile → then >1 demo trade/session is possible.
4. **GAP-3** structural resolver (OFF/SHADOW).
5. **GAP-4** prove full management (3 contracts → C1/C2/C3 structural → BE-after-T1 → trailed runner that closes) end-to-end for one CONT + one REV pattern in SHADOW.
6. **GAP-5** restart warm-start; **GAP-6** notes.

Each: SHADOW + Rule-5 raw output; Cowork audits before any live enable. Nothing live without Michael sign-off. Do NOT revert `d4363a1`; `DAYTYPE_POSITION_GATE=0` stays until Michael says revert.

## NOT-DONE
- ❌ Don't claim "3 contracts" from the `compute_v2_sizing` patch or its `V2 sizing:` log line — that path is inert; prove it from the written `trade_command.json`.
- ❌ Don't widen the single demo slot to hide GAP-2 — fix the runner-close.
- ❌ Don't keep pattern-height measured-moves for reversals (GAP-3).
- ❌ Don't enable anything live without SHADOW + sign-off.
