# CC Session Report — 2026-06-03 (Full Day)

## Tasks Completed

### 1. DB Root Fix (4 phases) — Commits `d38444d`, `edab3c0`, `9255bfa`

**Root cause closed:** concurrent unserialized ORM + raw sqlite3 writes to mems26_local.db.

| Phase | Status | Key metric |
|-------|--------|------------|
| 1 — bars.py ORM→safe_writer | DONE | 0 ORM writes (excl. disabled tick_reversal/footprint). 8 endpoints converted. |
| 2 — mode=ro on all reads | DONE | 17 raw connects → `file:...?mode=ro`. 0 raw-write connects outside safe_writer. |
| 3 — Journal isolation | NOT-DONE | Too complex (ORM readers). Plan documented. Root cause already closed. |
| 4 — Rebuild + integrity soak | DONE | 2 tables rebuilt (woodies/cvd). 21,726 pushes / 600s / 0 errors → `integrity_check = ok`. |

**Corruption repaired:**
- `v9_bars_5min_woodies`: 13,631 → 30,167 rows (hidden rows recovered)
- `v9_bars_cumulative_delta`: 51,803 → 492 rows (51,289 duplicates removed from corruption)

---

### 2. sc_study v9.4.5-wc-fix — Diagnose + Commit — `816dd1a`

**Finding:** v9.4.5-wc-fix already LIVE since June 2 (deployed + built). Mappings verified correct:
- TrendUp: SG4 (was SG1=CCI value — fixed)
- SWI: local-computed (Study 6 has no numeric SWI subgraph)
- Bars-from-chart12: direct OHLC read (eliminates frozen-tail)

Comment "SWI SG4" corrected to "SWI local-computed" in v9_types.h. Committed.

---

### 3. B4 Volume Artifact — Diagnose + Fix — `0ece0fa`

**Root cause:** RTH chart and continuous chart both wrote to `v9_bars_5min` via INSERT OR REPLACE. After 16:00 ET, RTH chart exported cumulative session volume (up to 1M), overwriting correct per-bar data.

| Fix | Detail |
|-----|--------|
| RTH time-gate | `/5min` + `/cumulative_delta` only write bars within 09:30–16:00 ET (DST-safe) |
| Continuous disabled | `/5min_continuous` returns `disabled: true` (RTH is sole source today) |
| is_synthetic cleanup | 19 inflated bars marked `is_synthetic=1`. MAX(vol) 1,000,000 → 71,832 |
| VSA filter | FiveMin hydration filters `is_synthetic=0` — rolling_avg clean |

---

### 4. Study-field Verification (per-system, read-only)

| System | Fields | Status |
|--------|--------|--------|
| S1 (day-type) | IB (Study 6 SG6/8), POC/VAH/VAL (Study 1/3 SG0-2), CVD | ✓ All connected, sane values |
| S2 (five-min/VSA) | 5-min OHLCV, rolling_avg, CVD enrichment | ✓ Clean after B4 fix |
| S3 (footprint) | BidVol/AskVol (Study 5) | ✓ Disabled, not breaking others |
| S4 (Woodies) | CCI-14/6, EMA34, LSMA25, SWI, CZI, trend_state, ProjHL | ✓ All populated, correct SG mapping |

**Version:** All exports = `v9.4.5-wc-fix`. Chart display name "v9.4.3-chart5" is cosmetic (Sierra persists from first add). No version mismatch.

**Input defaults:** In:17 (ProjHL) and In:19 (Woodies Chart) differ from Michael's live settings — no runtime impact (Sierra persists per-chart).

---

### 5. Feed Bring-Up (#10)

**Root cause of stale feed:** Sierra study stopped processing new 5-min bars. Tick feed (live_price) was alive; bar export was frozen.

**Resolution:** Michael reloaded study in Sierra UI. Bars started flowing.

**Current state (10:35 ET):**
```
RTH bars today in DB:
  09:30 ET  vol=12,419  o=7594.75  c=7593.0
  09:35 ET  vol=   460  o=7593.25  c=7593.5
MAX(ts) = 2026-06-03T13:35:00Z (09:35 ET) — advancing
MAX(volume) clean = 71,832
is_synthetic=1 count = 19
```

Feed is live. RTH time-gate working (pre-09:30 bars rejected, 09:30+ bars accepted).

---

## Commits Today

| Commit | Description |
|--------|-------------|
| `d38444d` | Phase 1: bars.py ORM → safe_writer |
| `edab3c0` | Phase 2: mode=ro on all read connects |
| `9255bfa` | Phase 4: rebuild + integrity soak (21K pushes, ok) |
| `816dd1a` | sc_study v9.4.5-wc-fix adopted + SWI comment fix |
| `0ece0fa` | B4: RTH time-gate + is_synthetic cleanup |

---

## Open Items

| Item | Priority | Owner |
|------|----------|-------|
| Phase 3 journal isolation | Low | Future session (defense-in-depth, root cause closed) |
| Dedicated continuous 24h table | Medium | Future session (enables overnight/pre-market data) |
| DLL defaults In:17=12, In:19=12 | Low | Future sc_study commit (cosmetic) |
| Integrity check (backend-down) | Before SHADOW | After feed confirmed stable for full session |
| SHADOW day | Next | Blocked on: full RTH session with clean feed + backend-down integrity=ok |
