# CC Forensics Executive Summary
Date: 2026-05-21T15:00:00Z
Author: Claude Code
Phase: 6
Mode: READ-ONLY

## TL;DR בעברית

▪ **מה גילינו:** V9 עדיפה ארכיטקטונית ב-25 מתוך 26 מדדים על V8 (הגרסה הישנה ב-Netlify). הגרסה הישנה נמצאת בריפו נפרד (`Documents/GitHub/mems26-web`) — לא בהיסטוריה של Git. הקוד הישן עדיין שלם אבל אין סיבה לחזור אליו.

▪ **צוואר הבקבוק האמיתי:** הפרונטנד שולח 5.3 בקשות HTTP בשנייה מטאב בודד (28 טיימרים של `setInterval`). בנוסף, חיבור SQLite נפתח וננעל מחדש עבור כל בר בודד בלופ — 30+ חיבורים לכל push. הבאג הכי חמור (self-deadlock של Woodies) כבר תוקן.

▪ **האסטרטגיה המומלצת:** D — תיקון כירורגי של V9 (~265 שורות קוד), בלי לייבא קוד מ-V8.

▪ **הצעד הבא:** לאשר אסטרטגיה D ולהתחיל בתיקון ה-polling storm בפרונטנד (העברה ל-WebSocket push).

---

## Top 5 Findings

1. **V9 wins architecturally.** 25/26 comparison dimensions favor V9 over V8: modular components (118 files vs 1 monolithic Dashboard.tsx), 6 independent trading systems with server-side decision trees, 4-gate risk gateway, full SHADOW mode, 23K LOC test suite. V8 has none of these.

2. **Performance problems are implementation bugs, not architecture flaws.** The primary bottleneck is a frontend polling storm: 28 `setInterval` timers generating 5.3 HTTP req/s per browser tab, all serialized through a single-worker uvicorn. The backend already has 9 WebSocket endpoints — they just aren't wired to the frontend.

3. **The old V8 site lives in a separate repo** at `/Users/michael/Documents/GitHub/mems26-web`. It was never in V9's git history. Stack: Next.js 14 + Render + Netlify + Claude AI live scoring. Key difference: V8 used live Sonnet 4.5 for trade signal scoring (1-10); V9 uses deterministic rule-based systems.

4. **Three surgical fixes cover 95% of the performance gap:** (a) consolidate polling to WS push (~200 LOC), (b) batch sqlite3 connections in bars.py (~35 LOC), (c) replace BarRouter thread spawn with `call_soon_threadsafe` (~30 LOC). Total: ~265 LOC.

5. **The worst performance bug was already fixed.** Woodies `decision_tree.py` had a self-deadlock making 5 sync HTTP calls to localhost blocking the event loop for 10s+. It's been patched to return an empty dict. The remaining bottlenecks are less severe and easier to fix.

---

## Recommendation

**Strategy D: Surgical Fix.** V9's architecture is sound — the performance issues are isolated implementation inefficiencies. Fixing 28 polling timers, per-bar sqlite3 connections, and thread-per-publish in ~265 LOC will resolve the observed slowness. There is no need to port V8 code or run both versions. The one V8 advantage (WebSocket push) already exists as infrastructure in V9's backend; it just needs to be connected to the frontend.

---

## Required Michael Decisions

1. **Confirm Strategy D** — fix V9 in place (~265 LOC, 2-3 days) rather than porting V8 code
2. **Decommission V8?** — Is the Render backend (`mems26-web.onrender.com`) still running/costing money? Should `blasttt.com` / Netlify be shut down?
3. **Archive V8 repo?** — Should `Documents/GitHub/mems26-web` get a `v8-final` tag?
4. **Optional V8 panel ports** — QualityScorePanel, VegasTunnelPanel, PreEntryChecklist exist in V8 but not V9. Priority: now or post-LIVE?
5. **Uvicorn workers** — Confirm if running `--workers 1` (default). Multi-worker would multiply throughput immediately.

---

## Estimated Path Forward

**Day 1:** Frontend polling consolidation — replace 28 `setInterval` timers with WebSocket push for real-time data (price, bars, TPO, Woodies chart). Reduce remaining polls to 10-30s intervals. Expected impact: backend load drops from 5.3 to ~0.5 req/s.

**Day 2:** Backend fixes — batch sqlite3 connections outside the per-bar loop in `bars.py`, pool Redis `publish_event()` connections, replace BarRouter thread spawn with `call_soon_threadsafe`. Add regression tests.

**Day 3:** Verification — UAT the 4 fix axes (Quality, Recency, Cardinality, Latency). Monitor backend load during RTH. Confirm polling storm is resolved. Update reports.

---

## Risks

🔴 **Single-worker uvicorn** — If confirmed, this is the force multiplier for all other issues. Even after polling fixes, a single worker serializes all requests. Consider `--workers 2` or `--workers 4` as an immediate safety net.

🟡 **V8 still live** — If `blasttt.com` and the Render backend are still running, they may be costing money and could cause confusion if accessed during V9 trading.

🟢 **Fix blast radius is small** — All 4 fixes are isolated to specific files, don't touch trading logic, and are covered by the existing test suite.

---

## Reports Index

| # | Report | Description |
|---|--------|-------------|
| 00 | `00_EXECUTIVE_SUMMARY.md` | This file |
| 01 | `01_CURRENT_STATE.md` | V9 architecture: 90+ routes, 6 systems, 12 bridge streams, 15K LOC frontend |
| 02 | `02_OLD_VERSION.md` | V8 discovery: separate repo, Netlify/Render, Claude AI scoring, monolithic |
| 03 | `03_COMPARISON_MATRIX.md` | Side-by-side: 25 PRESERVE, 1 ADOPT, 4 GAP, 1 CONFLICT |
| 04 | `04_PERFORMANCE_RCA.md` | Root cause: polling storm (5.3 req/s), per-bar sqlite3, thread spawn |
| 05 | `05_STRATEGY_RECOMMENDATION.md` | Strategy D (Surgical Fix, ~265 LOC) recommended over A/B/C |

All reports at: `docs/reports/p30_forensics/`
