# CC Round 3 Report — 2026-06-02 Night

| FIX | Status | Commit | Evidence |
|-----|--------|--------|----------|
| FIX-A (B1 commit) | **DONE** | `825972f` | Already committed. `grep lookback_quiet = True` = 2 instances. 4/4 tests pass |
| FIX-B (sc_study) | **DIAGNOSED** | — (not committed) | 3 files uncommitted (v9.4.5-wc-fix). Deployed source matches repo. Not touching — Michael's decision |
| FIX-C (D1) | **PARTIAL** | documented | Only trend_relabel uses flag(). Others frozen at import — safe (plist exports before python). Risk: flip-at-runtime only |
| FIX-D (chart session) | **DONE** | `361e5bd` | ET session filter (Globex 18:00 ET). Bars now show current session only |
| FIX-E (B4 artifact) | **DOCUMENTED** | — | DB 930K vs Sierra 72K = ingestion artifact. VSA rolling_avg contaminated |
| **NEW: 30min_woodies disable** | **DONE** | `361e5bd` | `WOODIES_30MIN_DISABLED=true` — same corruption pattern as tick_reversal |

## NOT DONE
- Chart visual verification: market closed, only 5 bars visible. **Deferred to RTH tomorrow**
- CVD alignment: depends on session filter working — verify in browser during RTH
- CLAUDE.md §DB Write-Safety: outdated (describes lock removed). Needs Michael decision

## Open
- **Residual ORM writers:** CVD, imbalance, bars_5min still write via ORM without lock. Lower frequency than tick_reversal/30min_woodies — monitoring
- **Volume artifact fix:** ingestion inflates volumes at close. Needs investigation of `bars.py` ingest path
- **D1 remaining flags:** 11 frozen imports — latent risk, not blocking

91/91 tests pass. DB integrity=ok (backend off).
