# P30 System Gap Audit — 2026-05-20

**Purpose:** Map what each subsystem has vs what's missing for LIVE.
**Michael:** Review and mark priorities.

---

## 1. Sierra DLL (MES_AI_DataExport v9.4.2-p30.11)

### Has
- [x] CCI-14, CCI-6, EMA-34, LSMA, SWI, CZI from Sierra native studies
- [x] ProjHigh/ProjLow from Woodies Panel
- [x] CCIDiff from Sierra CCI values
- [x] TPO today (POC/VAH/VAL) with va_ok validation
- [x] TPO yesterday with 3000-10000 range validation
- [x] Initial Balance (IB High/Low)
- [x] Cumulative Delta with timestamps + output_interval
- [x] Live price export (200ms)
- [x] Trade command polling (shadow mode)
- [x] Woodies 5min + 30min history bars
- [x] Tick reversal 15/12
- [x] Footprint + volume profile + imbalance flags
- [x] Reversal cluster export

### Missing / To Verify
- [ ] CCI Predictor H/L — Sierra study SGs don't expose predicted values. Using computed fallback. **Is this accurate enough?**
- [ ] ZLR detection — reading from ID:13 SG2 only. **Does Sierra's ZLR match our detection?**
- [ ] HFE detection — computed, not from Sierra. **Should it come from Sierra?**
- [ ] Trend state (BLUE/RED/YELLOW/GRAY) — computed from CCI+SWI. **Does ID:1 (CCI Trend) expose trend color as a subgraph?**
- [ ] Session volume — placeholder (0) in TPO session block. **Need to sum?**

---

## 2. Bridge (json_bridge.py)

### Has
- [x] Polls all JSON exports every ~3 seconds
- [x] Pushes to localhost:8000 backend
- [x] 11/12 streams active
- [x] Error recovery + heartbeat

### Missing / To Verify
- [ ] Stream 12/12 — which stream is missing? **Check heartbeat**
- [ ] TPO push errors (312 errors logged). **Transient timeouts or persistent?**
- [ ] Stacked imbalances errors (298 errors). **Same question**

---

## 3. Backend (FastAPI)

### Has
- [x] All V9 API routes (bars, TPO, woodies, CVD, trades, etc.)
- [x] BarRouter dispatching to all systems
- [x] Woodies process_bar (touchpoints deadlock fixed)
- [x] TPO previous_day endpoint
- [x] SQLite persistence for bars + signals
- [x] Trade manager (shadow mode)

### Missing / To Verify
- [ ] Woodies process_bar — touchpoints skipped (empty dict). **Implement background cache?**
- [ ] TPO periods accumulation — backend builds periods from DB. **Enough granularity for continuity paths?**
- [ ] `/api/v9/tpo/continuous/history` — endpoint doesn't exist. **Needed for richer stepped paths?**
- [ ] Decision tree A4 (touchpoints) — always returns "degraded". **Acceptable for LIVE?**
- [ ] Gateway route_setup — shadow mode only. **When to enable LIVE?**

---

## 4. Frontend (ChartV5b + Cockpit)

### Has
- [x] 6 TPO lines (3 white from 18:00 ET, 3 pink from 09:30 ET)
- [x] Time-bounded lines (not infinite)
- [x] TPO continuity overlay (stepped paths)
- [x] SVG badges (white fill yesterday, pink fill today, black text)
- [x] Woodies CCI Panel (hydration fixed)
- [x] CVD pane (cumulative delta bars)
- [x] Killzone label
- [x] Live price tick updates

### Missing / To Verify
- [ ] Woodies panel — are all HUD values displaying correctly (CCIDiff, Predictor, etc.)?
- [ ] TPO continuity — only renders from periods data. **Enough stepping resolution?**
- [ ] Today pink lines — **verify they appear during RTH (Michael reported not seeing them)**
- [ ] Chart zoom/pan — do TPO lines stay correctly bounded?
- [ ] CVD alignment — does CVD pane align 1:1 with price candles?
- [ ] Mobile/responsive — any layout issues on smaller screens?

---

## 5. Woodies Trading System (System 4)

### Has
- [x] 9 pattern detectors (ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB, HFE)
- [x] Decision tree (21 stages, A1-A7 + B1-B14)
- [x] Direction change detector
- [x] Sizing logic (full/half/reject)
- [x] Gateway routing (shadow mode)

### Missing / To Verify
- [ ] Pattern detection accuracy — **do our detections match Sierra's ZLR/pattern alerts?**
- [ ] Decision tree A4 — touchpoints always empty. **Impact on routing quality?**
- [ ] Signal persistence — patterns written to v9_woodies_signals. **Query performance OK?**
- [ ] Fire setup validation — pre-fire validator active? **Check A7 stage**

---

## 6. TPO System (System 5)

### Has
- [x] Sierra TPO JSON import (session + previous_session + IB)
- [x] Hydration from DB
- [x] Period tracking

### Missing / To Verify
- [ ] Session type classification (opening type, profile shape) — always "NA". **Sierra doesn't export?**
- [ ] POC migration tracking — direction "UNKNOWN". **Need more data from Sierra?**
- [ ] IB width — always null. **Calculate from ib_high - ib_low?**

---

## 7. Other Systems

### Day Type (System 1)
- [ ] Classification accuracy — **last audit?**
- [ ] Mid-session restart seeding — **tested?**

### Footprint (System 3)
- [ ] Stacked imbalances — **rendering in cockpit?**
- [ ] Imbalance flags — **visible on chart?**

### Killzone (System 6)
- [ ] Zone transitions — **correct timing?**
- [ ] Edge classification — **matches expected schedule?**

### Veto
- [ ] Suffering side detection — **tested with real data?**

### Layer 0
- [ ] State machine — **SEARCHING vs other states correct?**

---

## Priority Matrix (Michael to fill)

| Item | Priority | Owner | Notes |
|------|----------|-------|-------|
| Pink lines not showing during RTH | 🔴 | CC | Debug isRthNow() in browser |
| Pattern detection vs Sierra | 🟡 | Cursor | Compare ZLR alerts |
| Touchpoints background cache | 🟡 | CC/Cursor | Replace empty dict |
| TPO continuity resolution | 🟢 | CC | Depends on backend periods |
| Gateway LIVE mode | 🔴 | Michael | Decision required |
| | | | |

### Cursor suggested additions (override / delete — not approved)

| Item | Suggested | Owner | Rationale |
|------|-----------|-------|-----------|
| **L4 risk audit** (#14 firewall, kill switch) | 🔴 LIVE blocker | Michael + Cursor | Inbox L5 WAIT on L4 |
| **Gateway `cluster_guard` blocks SHADOW** | 🔴 | Cursor | Tree green but no shadow trade; `trading_gateway.py` |
| **6-agent fire/spec audit** (#16) | 🟡 | 6 agents | `P30_ORCHESTRATION_FIRE_AUDIT` — read-only |
| **Bridge stream 12/12 + TPO push errors** | 🟡 | CC | Gap audit §2 |
| **Woodies A4 touchpoints empty/degraded** | 🟡 | CC/Cursor | Routing quality vs spec |
| **CCI Predictor / trend from Sierra vs computed** | 🟢 post-LIVE | CC | Protocol §1 — verify only unless drift in RTH |
| **DLL G2 `previous_session` in tpo.json** | 🟡 | CC | If yesterday lines wrong on chart |
| **Design / HUD layout changes** | ⚪ defer | — | Michael: no approval |

Aligns with: `P30_SIERRA_STUDY_PROTOCOL.md`, inbox §7a, `PROMPT30_10b_PLAN_LIVE_FULL_REPORT_HE.md`.

---

**Michael:** סמן מה דחוף, מה יכול לחכות, ומה לא רלוונטי ל-LIVE. שלח ל-CC/Cursor את הטבלה המעודכנת כשמוכן.
