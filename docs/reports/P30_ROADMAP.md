# P30 Roadmap — Cockpit Visual Parity

**Last updated:** 2026-05-19

| P-ID | Title | Status | Evidence | Blocker |
|------|-------|--------|----------|---------|
| P30.0 | Design spec ingestion | GREEN | Spec ingested, component map done | — |
| P30.1 | Cockpit data path audit | GREEN | All GET endpoints verified | — |
| P30.2 | Browser visual proof | GREEN | Screenshot captured | — |
| P30.3 | Status endpoint hardening | GREEN | Parallel checks, 0.9s budget cap | — |
| P30.4 | Frontend polling fix | GREEN | WebSocket price, in-flight guards | — |
| P30.5 | Cockpit heartbeat | GREEN | `/api/v9/cockpit/heartbeat` <20ms | — |
| P30.6-7 | Chart history + rendering | GREEN | 600 bars, scroll-back, 4-axis UAT | — |
| P30.8 | Sierra 5min.json export | GREEN | DLL v9.4.0-p30.9, live OHLCV | — |
| P30.9 | Sierra screen parity | **PARTIAL** | TPO API + overlay shipped | RTH visual pending for full GREEN |
| P30.9b | CVD GET API | **GREEN** | GET live 1.3ms, 4-axis PASS | — |
| P30.9c | Chart Sierra alignment | **GREEN** | CVD inline, TPO today+yesterday, stepped POC, cyan IB (when found) | RTH visual pending |
| P30.10 | Woodies 5m panel | NOT STARTED | — | Needs bridge stream + panel |
| P30.11 | Full bridge stability | NOT STARTED | — | Michael approval needed |

## Next Single Thread

**P30.9 RTH sign-off** — During market hours:
1. Verify `ib.found=true` in `/api/v9/tpo/current`
2. Compare POC/VAH/VAL/IB values to Sierra screenshot (±0.25)
3. Visual check: ChartV5b overlay + CVD pane vs Sierra
4. If pass → P30.9 → GREEN

Then **P30.9c** (VAH/VAL stepped) or **P30.10** (Woodies panel) — Michael decides.
