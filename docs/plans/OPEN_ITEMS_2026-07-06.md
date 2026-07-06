# Open Items — consolidated (2026-07-06, live-session)

One clean list of everything to work on, pulled from MICHAEL_ISSUES_LEDGER.md,
STATUS_BOARD.md, the task list, and today's live findings. Priority order.

## A. LIVE real-money blockers (close before real orders)
| # | Item | Why it matters | Owner |
|---|------|----------------|-------|
| A1 | **SIM proof** — one `mode:live` order round-trips Sierra (order→fill→P&L==Sierra to the cent) | Live-account routing has NEVER executed once; the mechanism is only proven on demo | CC/Michael (Mac) |
| A2 | **Wire item-20 reconcile to the poll loop** | Built (`reconcile.py`) but not running → orphan / naked-stop AUTO-detection is OFF (the I-62 class) | CC |
| A3 | **T1/T2 fill-price gap** — demo/live T1/T2 close on bar-price, not Sierra fill | Not strict "P&L only from Sierra" (STOP+T3 already Sierra-only via I-62) | CC — task #17 |
| A4 | **22:15 hard-stop flatten wiring** | Today it only ALERTS (scheduled task); no auto-flatten of an open position | CC |
| A5 | **Feed watchdog + halt-on-death (D22/D34)** | Feed-death mid-session → orphan positions (recurred 06-19, 06-25); spec'd, never built | CC |

## B. Day-type classifier — TODAY'S live findings (cost 3 conf-0.80 INITIATIVE_LONG)
| # | Item | Why it matters | Owner |
|---|------|----------------|-------|
| B1 | **Faster Variation recognition** — the 8%-vol + 2-consecutive-close confirmation lag | Kept the day Normal until ~18:00 → 3 conf-0.80 LONG auth-SKIP'd while price rallied 7567→7584 | CC — task #22 |
| B2 | **Volume-acceptance methodology** — typical-price all-or-nothing under-counts straddle-bar above-IB volume (ignored 12,262 vol today); full-session denominator too large | This is the specific mechanism that delayed the confirmation; refine to volume-at-price + rolling denominator | CC — task #22 (needs backtest) |
| B3 | **Intra-bar reclass on close-confirmed IB break** | Reclass is bar-close gated; Dalton says day-type updates continuously through C–E periods | CC — task #22 |

## C. Pattern / gate tuning (blocked-but-should-have-fired)
| # | Item | Why it matters | Owner |
|---|------|----------------|-------|
| C1 | **cont_trend_filter on Variation days** vetoes with-trend entries on a bounce ("UP vs sustained NEUTRAL/DOWN") | Uses a local LSMA(K=3) that flips on a bounce; may need extension-direction instead (ledger #20) | Michael ruling + CC |
| C2 | **Auth table INITIATIVE on Normal/low-tier = SKIP** | The gate that skipped today's longs; tied to B1/B2 (day-type accuracy) | review after B |

## D. System 6 completion
| # | Item | Why it matters | Owner |
|---|------|----------------|-------|
| D1 | **Timer-button** (press / auto-decide after 2 min) | Michael's design; depends on live path + AUTOCORRECT | CC — task #20 |
| D2 | **Wire System 6 (+ item-20) into the poll loop** | Currently advisory via endpoint only | CC |
| D3 | **SYSTEM6_AUTOCORRECT** — enable after advisory proves out | Auto-applies to live trades → gate carefully | Michael |

## E. Deferred profitability package (until a profitable validated baseline)
| # | Item | Owner |
|---|------|-------|
| E1 | Economics-package items 12 / 13 (P/b filter) / 16 / 17 / 7 / 8 | CC |
| E2 | Shallow S4 patterns (TT / FAMIR / HTLB) | CC |
| E3 | Mechanism-C behavioral test (replace tautological string-check) | CC |

## F. Tech-debt / cleanup (close before LIVE)
| # | Item | Why it matters | Owner |
|---|------|----------------|-------|
| F1 | Remove SQLite hydration fallback in `main.py` | 16× "database disk image is malformed" noise each boot (Postgres is the real DB) | CC |
| F2 | Full ts-TEXT→timestamptz migration (cumulative_delta, tpo) | I-53 fixed pointwise; full conversion open | CC |
| F3 | Retire runtime `INSERT OR REPLACE`→`ON CONFLICT` shim (per-table explicit) | Postgres-era cleanup | CC |

---
**Canonical trackers:** `docs/plans/MICHAEL_ISSUES_LEDGER.md` (issues) · `docs/plans/STATUS_BOARD.md`
(source of record) · task list. Keep this file refreshed at EOD or when an item closes.
