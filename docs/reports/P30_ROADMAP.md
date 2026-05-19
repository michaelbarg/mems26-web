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
| P30.9 | Sierra screen parity | **GREEN** | Numeric parity 7/7, 4-axis PASS, --workers 2 stable | IB deferred to RTH (G1) |
| P30.9b | CVD GET API | **GREEN** | GET live 1.3ms, 4-axis PASS | — |
| P30.9c | Chart Sierra alignment | **GREEN** | Autonomous browser UAT 2026-05-19: candles, CVD inline, TPO lines | IB lines only when Sierra `ib.found=true` (G1, RTH) |
| P30.SHADOW | SHADOW end-to-end | **PARTIAL** | mode=shadow, soak Day 6/30, gateway OK, chart loads | Redis/WS optional; P30.10 Woodies deferred |
| P30.10 | Woodies 5m panel | NOT STARTED | — | Needs bridge stream + panel |
| P30.11 | Full bridge stability | NOT STARTED | — | Michael approval needed |

## Next Single Thread

**P30.SHADOW soak** — CC/Michael: 10+ min heartbeat+bars5min <2s under live bridge push; then SHADOW soak go.

**G1 (RTH only):** When `ib.found=true` in Sierra `tpo.json`, re-run numeric parity + confirm cyan IB on chart.

**P30.10** — Woodies 5m panel (does not block SHADOW chart parity).
