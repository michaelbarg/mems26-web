# LIVE Fix Journal — permanent protocol (Michael 2026-07-07)

**Priority rule (Michael):** we are on **REAL MONEY**. 🔴 **LIVE** issues are the ONLY thing that
matters. ⚪ **SHADOW** is nice-to-have — deprioritized. Never let a shadow item delay a live fix.

## Protocol — runs EVERY trading day (mandatory, every agent: Cowork · Claude Code · Cursor)
1. **EOD review** — Cowork + CC list the day's issues that touched the **LIVE** path (fires,
   fills, stop/target management, P&L, monitoring). Each gets a row below: 🔴/⚪ · status · owner.
2. **Fix** — CC executes the 🔴 fixes in code (tests + raw verification, Rule 5). Cowork verifies
   from repo/DB. A7 + any new live issue are worked here until closed.
3. **STATUS_BOARD sync** — fold the same items into `docs/plans/STATUS_BOARD.md` (done vs todo,
   dated log line with finding + fix + evidence). This journal + STATUS_BOARD stay in lockstep.
4. **Journal update** — move closed items to DONE with the commit + evidence; carry open items.
No item is "done" without raw verification on the **live/SIM** path (shadow proof does not count).

---
## 🔴 LIVE — open (real money — fix first)
| # | Issue | Evidence / why | Status | Owner |
|---|-------|----------------|--------|-------|
| L1 | **A7 fire_setup routing** — ZLR/GHOST must route (no `failed_stages=['A7']`) | fallback in code (woodies_system.py:668-679), NOT verified on a live fire | OPEN — verify live | CC |
| L2 | **✅ Stop-move reaches Sierra — VERIFIED** | Drill 07-09: MODIFY_STOP_OK error=3 (all 3 stops moved). Bug found: DLL read stale persistent slots → fixed (stop_ids from command JSON, 13ae491). Also MODIFY_TARGET_OK + exit CANCEL_OK flatten. Structure-trail design (STOP_STRUCTURE_TRAIL_V1) already ON. | **DONE** — drill 07-09 | CC |
| L3 | **Monitor shows SHADOW as "live" + no P&L** | trade #301 = SHDW in table but "live" in the supervision monitor; +$0, "not monitoring" | OPEN — display/tracking bug | CC |
| L4 | **Live fill capture** — real fire → tracked trade + Sierra P&L | fallback (I-58) proven on demo #297; not yet on a real live fill | OPEN — verify on 1st live fill | CC/Cowork |
| L5 | **Day-type lag** (Normal held too long → misses Variation/Trend fires) | task #22 (B1/B2/B3); affects which LIVE patterns arm | OPEN — build+backtest | CC |
| L6 | **T1/T2 P&L from Sierra fill** (not bar-price) | task #17; live P&L accuracy | OPEN | CC |
| L7 | **2-contract SYMMETRY** — the whole system must recognize contracts=2 everywhere | Michael: sizing knows 2 (FIXED_CONTRACTS_2) but the bracket still shows **3 targets** (C1/C2/C3) for a 2-contract trade ("1/3 hit"); audit bracket/targets + per-contract P&L + R + Sierra command + display all read the LIVE contract count symmetrically | OPEN — symmetric audit | CC |
| **L8** | 🚨 **URGENT — Sierra-sourced LIVE ledger + detect MANUAL intervention** | Michael: (a) build a LIVE trade record that reflects **only what Sierra actually EXECUTED**, imported from Sierra (real fills / stops / P&L) — *what actually happens, NOT what the backend records*; separate from backend-synthesized/shadow. (b) **If Michael manually intervenes** (moves a stop / closes a trade in Sierra), the system must **detect it from Sierra, update its record to match, and LOG it as a MANUAL action** (distinct from system actions) so we can learn from it. Ground-truth ledger for real money | OPEN — URGENT build | CC + Cowork |

## ⚪ SHADOW / nice-to-have (do NOT block live)
| # | Issue | Status |
|---|-------|--------|
| S1 | Clickable recent-trade rows → show entry/stop/targets + distance-to-T1 | OPEN (UI) |
| S2 | Shadow-trade analytics / benchmark | OPEN |

## ✅ DONE (with evidence)
| Issue | Commit | Evidence |
|-------|--------|----------|
| **Trade 310 P&L reconciled from Sierra TradeActivityLog** | DB UPDATE (no code change) | evidence_2026-07-09/trade_310_reconcile.md — DB had entry=7514/exit=7518.5/pnl=$45; Sierra truth: entry=7515.50/exit=7517.75/pnl=$22.50. Root cause: L4 class — entry_price came from setup not fill. Audit trail in quality JSON. |
| Order path to Sierra (2c fill, no GENERAL_ERROR) | DLL 9d314d0 | evidence_2026-07-07 P0 |
| P1.2 orphan-fill → CRITICAL | 9363d4a | live: order_id 8411/8418 flagged |
| P1.3 reconcile-live wired | 5019a7b | 4 tests |
| P2.4 System6 per-bar + reconcile feed | 1b66813 · 65dff60 | 18 tests |
| P1.1 EOD auto-flatten | 1b66813 | 4 tests |
| Phantom 297 cleaned | — | 297 CLOSED, slots free |

---
## Cowork verification — 2026-07-07 ~18:45 IDT (repo + CC artifacts, no live access)
Source: `docs/reports/evidence_2026-07-07/` (CC raw, Rule 5) + code read. Sandbox can't reach live
PG/backend → live-fire proofs still owed by CC.

**✅ WORKING (verified):**
- **P0 2-contract order path → Sierra.** `p0_command.json` contracts=2 / mode=live / acct 37138283 →
  `p0_result.json` `ORDER_SUBMITTED` error=0 → `p0_msglog.txt` Sierra order 8418, sim fill @7580.25,
  Flatten shows *"Current Position quantity: 2"*. DLL binary `Jul 7 13:42` **>** source `06:42`
  (sha256 in `p0_dll_mtime.txt`) → the SendOrders fix IS in the deployed binary. Supersedes the stale
  `GROUND_TRUTH_2026-07-07.md` (had 2c = TIMEOUT / study-not-loaded).
- **L1 A7 fallback present in code** — `woodies_system.py:668-690` reconstructs the stop from V2
  `stop_price` / `risk_points` → fire_setup no longer None when V2 owns the stop. ⚠ NOT verified on a
  live ZLR/GHOST fire.
- **Preflight flags live** (`p1_preflight_flags.txt`): RISK_HALT_V1=1 · CAP=400 · FIXED_CONTRACTS_2=1 ·
  EOD_FLATTEN_V1=1 · RECONCILE_LIVE_V1=1 · SYSTEM6_SUPERVISOR=1 · CONT_TREND_FILTER=1.

**🔴 FAULTY / UNVERIFIED:**
- **L2(a) — why the Sierra stop didn't move (code-verified; this is the "records ≠ reality").** The BE
  arithmetic `_apply_smart_be_after_t1` (manager.py:391) is correct and it calls `_emit_modify_stop`
  (:442). But `_emit_modify_stop` (manager.py:119-125) has **two SILENT `return`s** *before it ever
  writes to Sierra*: (1) `_is_demo_mode` → for `mode=="live"` needs `LIVE_EXECUTION_V1` truthy;
  (2) `_get_sierra_order_id` must be non-None — set only by `set_sierra_order_ids` from the ENTRY-fill
  map. A live trade captured via the **I-58 fallback (L4)** never had its order_id mapped →
  `sierra_order_id` absent → the MODIFY silently drops → **DB records BE, Sierra never moves.** ⇒
  **L2 and L4 share one root** (missing live order-id map) and both fail silently. CC: (a) confirm
  `LIVE_EXECUTION_V1` live; (b) the I-58 fallback must also call `set_sierra_order_ids`; (c) turn both
  `return`s into rate-limited warnings. *(L2(b) structure-trail is a separate design change — below.)*
- **L4 capture — fallback-only, DEMO, not live.** `p1_capture_fillpoller.txt`: order_id 8424 unmapped
  → fallback to demo 297 (`p1_capture_db.txt`: mode=demo, PENDING). Not proven on a real live fill.
- **L7 symmetry — evidence inconclusive.** The 3-target setup in `p1_capture_gateway_fire.json`
  (t1/t2/t3) is a **SIM_TEST** injection, not the live woodies path (`_s4_t2 = _s4_t3 = None`,
  woodies_system.py). The "3 targets for a 2c trade" is a **display / command-structure** issue — CC
  audit bracket/targets/P&L/R to read contracts=2 symmetrically.
- **⚠ FLAT-STATE UNCONFIRMED.** `p2_clean_verify.txt` reconcile = `MISMATCH_ORPHAN_DB`
  `db_open=[401,402,403,404,405]` with the gateway slot flat + `trades_today=0`. The CLI can't see the
  live gateway slot/TM (DB + trade_result.json only). **Cannot confirm we are flat from the sandbox** →
  no restart / no code change until CC confirms flat.

**Notes:** L2(b) structure-trail-after-T1 (not entry/BE) is a real design change → belongs with the
config-tunable stop/target work; build flag-OFF + backtest, not mid-live. **L8 (Sierra-sourced live
ledger + manual-intervention detection)** — Cowork co-owns; blocked on flat-state + a short spec.
Proposed first step: a Sierra→ledger import keyed by Sierra order_id (real fills / stops / P&L) as the
single source, separated from backend-synthesized / shadow rows; each poll, diff Sierra state vs the
system record — when they diverge with **no** system-issued command, log it as a **MANUAL** action
(distinct from system actions) so we can learn from it. The L4 order-id map is the shared prerequisite.

---
## Cowork build — 2026-07-07 ~19:55 IDT (BLOCKER-1 resolved · L8 engine + UI built)
- **BLOCKER-1 RESOLVED** — Michael: **2 live trades executed, BOTH succeeded.** Real-money order path
  works (the earlier 303 `GENERAL_ERROR_OR_NOT_ENABLED` was live-account arming, not our code). The
  remaining gap Michael flagged: **the frontend is NOT synced with Sierra** — it shows backend records,
  not what Sierra executed. This is L8, now **investor-critical**.
- **L2 fix landed** (`eb4bc6f`) — `_is_demo_mode` now returns True for `mode="live"` (was demo-only) →
  MODIFY_STOP/TARGET reaches Sierra on live. Verified in the diff; matches my L2(a) diagnosis above.
  **Residual (still open):** the second silent guard — `_get_sierra_order_id` None → MODIFY dropped —
  is unchanged; a fallback-captured live trade (L4) has no order_id → still silent. CC: store the
  order_id in the I-58 fallback + make both returns warn. Also `ea868cc` fixed a DB crash (42-char
  exit_reason overflowed varchar(30) → stuck 299).
- **L8 built (Cowork, flag-OFF `LIVE_LEDGER_V1`):**
  - `backend/v9/services/sierra_ledger.py` — reconstruct each trade from **Sierra fills alone**
    (entry/exits/contracts/realized-P&L from fill prices), `reconcile()` vs the backend DB row (entry ·
    **stop** · exit · P&L · state · contracts → CRITICAL divergences), `detect_manual()` (MANUAL_CLOSE +
    MANUAL_STOP_MOVE, MANUAL vs SYSTEM). **7/7 tests green** —
    `python3 backend/v9/tests/services/test_sierra_ledger.py`.
  - `backend/v9/api/v9/live_ledger_routes.py` — `GET /api/v9/live_ledger` (wired in `app.py`), reads
    `trade_fills.json`, joins live DB rows by `sierra_order_id`, returns rows + divergences + manual tags.
  - Frontend `LiveLedgerPanel.tsx` on **/board** (top) — real Sierra trades, divergences + MANUAL flagged.
  - **CC to close (deploy + Rule 5):** enable `LIVE_LEDGER_V1` → restart **when flat** → feed the Sierra
    **TradeActivityLog** (`sierra_stop` + stop-move history) so L2/manual-**stop** detection is live (fills
    alone give entry/exits/P&L; the stop-MODIFY history needs the activity log) → verify V1–V5 against the
    2 real live trades. Confirm both appear in the ledger with correct fills/P&L.
- **Frontend board shipped (Cowork, no backend change):** `/board` = Live Ledger + System 6 supervisor
  (`/api/v9/system6/diagnose`) + prioritized task board (`public/task_board.json`, both agents edit).
  Needs :3000 up. Tomorrow's sequenced plan: `docs/plans/WORK_PLAN_2026-07-08.md`.

---
## Cowork build — 2026-07-08 ~15:45 IDT (N2-prep committed · N3 + N4/L7 FIXED IN CODE · N5 done)
**State check (repo):** no CC commits overnight (HEAD was `86c4cdc`); the entire 07-07 L8 build was
sitting UNCOMMITTED in the working tree → committed `6bb25ce` (engine+endpoint+7/7 tests+docs) +
`9f0a64a` (board components). All work below is code+unit-verified in the sandbox; **live/SIM
verification owed by CC after ONE restart** (which also flips `LIVE_LEDGER_V1`).

- **N3 · L2-residual FIXED (`d999698`)** — root: `register_order` was defined but never called; every
  ENTRY resolved via the I-58 "most recent active" fallback, and a trade with no `sierra_order_id`
  dropped MODIFY **silently**. Fix: (a) `_register_submitted_order` — on the DLL's `ORDER_SUBMITTED`
  ack (`parent_id`/`target_id`/`stop_id` in `trade_result.json`), map all three ids AND persist
  `sierra_order_id` at submit time (before/without the ENTRY fill line); (b) ENTRY also maps the
  parent id itself; (c) `_emit_modify_stop`/`_emit_modify_target`/`_emit_exit` skips now WARN
  (rate-limited 60s; shadow stays silent by design). Proof: `test_fill_order_map.py` **5/5**; on OLD
  code **4/5 FAIL**.
- **N4 · L7 2-contract symmetry FIXED (`d999698`)** — audit found the DB had NO per-trade contract
  count at all (`accept_setup` dropped `setup["contracts"]`), and FIVE hard-3 consumers:
  `on_target_hit` (only T3 closed → **a 2c trade stayed PARTIAL forever after T2**),
  `_calculate_pnl` (**a 2c stop-out was counted 3× = 150% of the real loss**; R denominator 3×),
  `/trades` active payload (phantom C3 row + "x/3 hit" — Michael's "1/3"), `fill_poller`
  (slot freed only on T3/STOP → 2c T2-close left the slot stuck), `setup_emitter` opening floor
  (ignored `FIXED_CONTRACTS_2`). Fix: `effective_contracts()` single source (verbatim choke-point
  logic) → persisted as `quality.contracts` at accept → `trade_contract_count()` read by close/P&L/
  display/slot-release; close-at-last-target (2c→T2, 1c→T1); P&L legs `[:n]` + R `n×`; "N/n hit".
  Bonus root-fix: the close-time recalc also fixes the **3c T3-close undercount** (final P&L was
  missing the c3 leg — pnl stayed at the 2-leg PARTIAL value). Already symmetric (verified, no
  change): DLL OCO groups (`>=2`/`>=3`), System 6 expected_contracts, sizing sources, bar_level_detector.
  Proof: `test_l7_two_contract_symmetry.py` **6/6**; on OLD manager/poller **1/6** (−$60 vs −$40
  stop-out, T2 left PARTIAL, no slot release, T3 undercount). Regression: `tests/v9/regression`
  **830 passed / 12 failed == the identical pre-existing fixture set** (diffed vs old-code baseline).
- **N5 · Index + flag registry (`b275165`)** — `gen_index.py` 762 files/113 dirs (sierra_ledger +
  live_ledger_routes + board traceable); FLAG_REGISTRY documented `EOD_FLATTEN_V1`,
  `RECONCILE_LIVE_V1`, `LIVE_LEDGER_V1`, `TRADE_FILLS_PATH` → FLAG_INDEX **99 flags, --check PASS**.
- **⚠ Restart note:** N3+N4 change `manager.py`/`fill_poller.py` — **not live until the backend
  restarts**. The N2 deploy restart (LIVE_LEDGER_V1) covers everything; CC confirms FLAT first.
- **CC today:** `docs/handoff/CC_CONTINUATION_2026-07-08.md` — N1 snapshot/health → N2 deploy+V1–V5 →
  T1–T5 gate evidence (arming · L2 live MODIFY · A7 route · L4 capture · L7 2c SIM fire).

---
## Cowork — 2026-07-08 LIVE session (evening) · trade 310 post-mortem + the evening fixes
**The day:** Michael armed live. ZERO system trades all session; one live fire (310) he closed
manually. Every blocker found was diagnosed from logs and root-fixed the same evening (all
committed; deployed via the 21:43 post-session restart, verified: flag_guard 31/31 + fire-drill 🟢).

**🔴→✅ Closed tonight (live/SIM verification owed to CC per Rule 5 — `CC_MORNING_2026-07-09.md`):**
| Root | Live evidence | Fix |
|---|---|---|
| L1/A7: compute_stop_v2 floor 4-ticks < MEMS_MIN 2pt → doomed 1pt stops, 3 ZLR dropped | 17:25–17:30 `FIRE DROPPED ['A7']` | band floor 0.5×ATR (`15de2c4`+`0107a12`) — **verified live: zero drops after 19:02** |
| Entry-confirm blocked SHORT on a 3-tick counter-close (~10pt candles) | 18:00 block | tol = 0.10×ATR (`ce3045d`, ruling #6) |
| **AUTH-KEY-BYPASS: the LOCKED auth table silently bypassed** — lookup ('Reactive',day) vs keys 'REACTIVE_LONG/…' → "using max" everywhere; `INITIATIVE×Neutral_Extreme=SKIP` would have blocked trade 310 | "no auth cell" warnings all day; 310 fired | `_auth_cell` normalization (`51d531c`) |
| ORDER_FAILED after submit-ack cancelled the live row → naked orphan position; Michael flattened manually; NAKED_STOP screamed correctly | 308/310, ~19:40–19:50 | no-cancel-after-ack + NAKED-BRACKET critical (`f51f8b7`) |
| Cockpit /exit didn't release the gateway slot → live_slot stuck on 310, all fires blocked | gateway/status after manual close | exit→on_trade_close (`f51f8b7`) |
| Shadow 313 rendered as the "active trade", masking live 310 → Michael's manual close invisible; ledger showed 0 trades (poller cleared fills before the ledger read) | /active + ledger 19:50–20:00 | /active LIVE→DEMO→none + fills journal (`a44ee90`) |
| Day was NEUTRAL per Dalton (both-side IB ext: 7501.75/7524.75, −32.5/+3.75) — classifier lagged, then a restart WIPED intraday S1 state (Neutral 0.48→Variation 0.18) | 20:44 | S1-STATE-PERSIST P1 (S1-chat) + ops rule: no mid-session restarts |

**Michael rulings → flags (all in RULED_FLAGS, guard 31/31):** `NEUTRAL_RESPONSIVE_V1=1` (REV exempt
from direction_context on Neutral days) · `TARGET_STRUCTURE_CLAMP_V1=1` (TP-1: no targets beyond IB
unless Neutral/Trend — the 310 geometry now clamps, tests 5/5) · `STOP_STRUCTURE_TRAIL_V1=1`
(after-T1 stop parks at structure, not BE — tests 5/5) · entry-confirm tol 0.10×ATR.
**Also shipped:** TRADING_SPEC.yaml (16 rules) · flag_guard/fire_drill/morning_briefing/s6_eod
(scheduled 15:55/23:05) · Dalton doctrine + S1 executor prompt · trade 310 recorded MANUAL_CLOSE
+$45 (approx price — CC reconciles vs the real fill via TradeActivityLog tomorrow).
**Open (new):** S4-RUNNER-T2-SIGN (short runner t2 wrong side, sanitized away) · stale-bar source
(exports clean → bridge stream suspect) · full TP audit needs psql (v1 harness committed).
