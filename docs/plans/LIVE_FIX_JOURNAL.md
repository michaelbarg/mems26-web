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
| L2 | **BE-after-T1 stop not moving on live** | Michael saw T1 hit but stop didn't move ("שוב פעם"); `_apply_smart_be_after_t1` (manager.py:386) exists — confirm it FIRES + emits MODIFY on live/demo, not just shadow | OPEN — root-cause | CC |
| L3 | **Monitor shows SHADOW as "live" + no P&L** | trade #301 = SHDW in table but "live" in the supervision monitor; +$0, "not monitoring" | OPEN — display/tracking bug | CC |
| L4 | **Live fill capture** — real fire → tracked trade + Sierra P&L | fallback (I-58) proven on demo #297; not yet on a real live fill | OPEN — verify on 1st live fill | CC/Cowork |
| L5 | **Day-type lag** (Normal held too long → misses Variation/Trend fires) | task #22 (B1/B2/B3); affects which LIVE patterns arm | OPEN — build+backtest | CC |
| L6 | **T1/T2 P&L from Sierra fill** (not bar-price) | task #17; live P&L accuracy | OPEN | CC |

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
