# CC Work Queue — 2026-07-01 (organized handoff / index)

**Owner:** Michael · **Prepared by:** Cowork · **Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` (Rule 5 raw output · anti-tautological tests · NOT-DONE).
One entry point for all pending CC work, in priority order. Each item points to its full spec.

---

## ✅ Shipped this session — VERIFY, do NOT redo
| Change | Commit / state | Verify |
|---|---|---|
| S2 `'c'` KeyError crash fix (normalize b1-b4 OHLC) | `d4363a1` | S2 process_bar no longer throws; `v9_bars_5min` flows |
| `FIXED_CONTRACTS_3` — 3 contracts on every fire (S2+S4), reject preserved | `34d6354` · `.env FIXED_CONTRACTS_3=1` | `compute_v2_sizing` returns 3 when firing; 3 tests pass |
| `DAYTYPE_POSITION_GATE=0` — family gate OFF (validation) | `.env` (snapshot `20260701T140209Z`) | ⚠️ **temporary** — revert to `=1` after validation (REV-on-trend = −34.6R) |
| First DEMO trade → Sierra (261 ZLR, T1→BE MODIFY_STOP_OK) | `v9_trades` 261 | pipeline detect→route→demo→Sierra confirmed |

---

## P1 · Structural Target Resolver (the main build) 🔴
**Full spec:** `docs/handoff/CC_STRUCTURAL_TARGET_RESOLVER_BUILD_2026-07-01.md`
**Design refs:** external research result (per-day-type AMT/fractal/caps) · `docs/spec_authority/RESOLVER_TARGETS_BY_DAYTYPE.html` (targets by day-type) · `docs/spec_authority/PATTERN_PLAYBOOK_CANDLES.html` (all 16 patterns: geometry + structure + volume). **Michael may edit the two HTML docs — build from his edited versions.**
**Cowork-verified numbers (use these, not the research priors):** `ATR₅ₘ=7.07pt` · VA-width today 38 · measure RTH `dATR` live.
**Problem:** targets are broken — ZLR +4.75 (too close), HTLB/REACTIVE −92/−140 (unreachable), 267 "no target."
**Build order (flag `STRUCTURAL_TARGETS_V2`, default OFF, SHADOW):**
1. **T1 = first swing-completion** (Williams K=2, close-confirmed) · floor `0.5×ATR₅ₘ≈3.5` · cap `min(2×ATR₅ₘ,0.30×dATR)≈14` (place at cap if farther).
2. **C2/C3 per day-type table** — **Michael's split:** C2 = nearest structure **closer than** the VA edge (POC/IB-center/next-swing); **C3 = VA edge (VAH/VAL), the runner** (trail). Route EVERY pattern through the table.
3. **Hard-cap post-processor** — target > cap → snap to nearest structure inside cap. runner-cap `min(1.5×dATR,3×IBw)`.
4. **Reversal patterns: DELETE pattern-height measured-moves** → nearest opposing structure / POC, capped.
5. **Calibrate [K]** on our bars (order in the spec).
**Verify (Rule 5, SHADOW):** replay today — ZLR +4.75→swing/cap · HTLB −92→capped structure. Paste before/after.

## P2 · Demo-slot reconcile (runner never closes → slot stuck) 🔴
**Full spec:** `docs/handoff/CC_DEMO_SLOT_RECONCILE_2026-07-01.md`
**Problem:** after the first demo trade the single demo slot is held forever (runner never reaches a terminal close; `trade_fills.json` empty → `FillPoller` starved). Only one demo trade per session.
**Do:** (A) backend runner-close (trail/LSMA/time-stop/EOD → `on_trade_close` → `demo_slot=None`); (B) boot + periodic reconcile (PARTIAL trade + Sierra flat → close + free slot); (C) fix the Sierra→`trade_fills.json` fill-feedback. Immediate release = restart (verified).

## P3 · Opposite-pattern exit (Michael's rule) 🟡
**Goal:** when a trade is ACTIVE and **≥2 patterns detect the OPPOSITE direction** (within a short window) → **close the existing trade** (don't wait for stop/target).
**Do (flag `OPPOSITE_EXIT_V1`, default OFF, SHADOW):**
- Track the active trade's direction (per system / global). On each bar, count fresh pattern detections in the opposite direction (any system, e.g. 2× short-signals while long).
- On reaching the threshold (default **2**, tunable) → issue a close (market exit + Sierra `write_exit`) of the active trade; log the reason `OPPOSITE_2X`.
- Do NOT flip into a new trade automatically (close only) unless Michael approves the flip.
**Tests:** 2 opposite detections with an open trade → close fires; 1 opposite → no close; same-direction detections → no close; flag OFF → unchanged.

## P4 · Restart = full warm-start (Michael's rule) 🔴
**Goal:** a restart must NOT degrade anything — on boot, **every system hydrates ALL required data from the DB** so behavior is identical before/after the restart. No cold windows (we hit this: woodies buffer cold, day-type re-forming, slot lost).
**Do — confirm each hydrates on boot + add any missing:**
- S4 Woodies: `hydrate()` loads ≥50 bars from `v9_bars_5min_woodies` → CCI/trend warm immediately (not GRAY for 6 bars).
- S1 day-type: opening-type + IB + day_type restored from `v9_day_type_state`/history (not UNKNOWN post-restart).
- TPO value-area: VAH/VAL/POC current from `v9_tpo_history`.
- S2 FiveMin: buffer + current_day_type hydrated.
- Gateway: **open DEMO/LIVE trades re-loaded into their slot** (so a restart doesn't orphan an active trade — ties to P2 reconcile), OR reconcile-close if Sierra is flat.
- Kill the legacy malformed-SQLite `_hy_conn` startup check (`main.py:805`) — it errors "database disk image is malformed" (harmless but noisy; read.py is Postgres).
**Verify (Rule 5):** restart mid-RTH → within 1 bar: trend≠GRAY, day_type≠UNKNOWN, buffer=50, VA present, any open demo trade still managed. Paste the boot state.

## P5 · Full 3-contract management for ALL 16 patterns (Michael's rule) 🔴
**Goal:** every pattern that fires runs the **same complete management**: **3 contracts** (✅ shipped `FIXED_CONTRACTS_3`) + **C1/C2/C3 structural targets** (P1 resolver — route ALL 16 patterns, no pattern uses its own measured-move) + **BE-after-T1** (`smart_be`, verify live→Sierra) + **trail/runner-close on C3** (P2). No pattern is left with partial or ad-hoc management.
**This is the union of P1+P2 applied uniformly** — the deliverable is: pick any of the 16 patterns, it gets 3 contracts, structural C1/C2/C3, BE after T1, trailed runner that actually closes. Test one CONT + one REV pattern end-to-end in SHADOW.

---

## NOT-DONE (applies to all)
- ❌ Nothing live-enabled without SHADOW validation + Michael sign-off (trading-risk).
- ❌ Do NOT revert the shipped fixes (`d4363a1`, `34d6354`); `DAYTYPE_POSITION_GATE` stays 0 until Michael says revert.
- ❌ Do NOT trust research point-priors over our measured ATR (7.07) — calibrate live.
- ❌ Reversal targets = structure, never pattern-height measured-move.
- ❌ One demo slot (one-at-a-time) is intentional — fix the runner-close, don't widen the slots.

## Order
**P4** (restart warm-start — foundational + independent + quick; every session begins with a restart) → **P1** (resolver — biggest P&L lever, feeds P5) → **P2** (slot-reconcile — unblocks >1 demo trade/session, feeds P5) → **P5** (verify all-16 get the full 3-contract management — the union of P1+P2) → **P3** (opposite-exit — standalone).
Report + SHADOW-verify each before the next; Cowork audits each (Rule 5) before any live enable.
