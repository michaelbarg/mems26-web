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
| L2 | **Stop-move is RECORDED but doesn't happen in Sierra + wrong target** | Monitor/DB shows stop→BE 7544.75 after T1, but in REALITY the Sierra stop did NOT move (display≠Sierra — the recurring "records ≠ reality"). (a) confirm `_emit_modify_stop` (manager.py:437) actually reaches Sierra (sc.ModifyOrder) on live, not just the DB record; (b) **DESIGN: after T1 the stop must trail toward STRUCTURE (nearest structural level), NOT to entry/BE** (Michael) — `_apply_smart_be_after_t1` currently sets entry∓1tick | OPEN — bug + design | CC |
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
| Order path to Sierra (2c fill, no GENERAL_ERROR) | DLL 9d314d0 | evidence_2026-07-07 P0 |
| P1.2 orphan-fill → CRITICAL | 9363d4a | live: order_id 8411/8418 flagged |
| P1.3 reconcile-live wired | 5019a7b | 4 tests |
| P2.4 System6 per-bar + reconcile feed | 1b66813 · 65dff60 | 18 tests |
| P1.1 EOD auto-flatten | 1b66813 | 4 tests |
| Phantom 297 cleaned | — | 297 CLOSED, slots free |
