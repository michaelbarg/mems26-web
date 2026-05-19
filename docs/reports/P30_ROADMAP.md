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
| P30.9 | Sierra screen parity | **PARTIAL** | TPO API wired, overlay shipped | CVD pane missing, RTH visual pending |
| P30.9b | CVD pane + GET API | **NEXT** | — | Needs GET from Sierra file |
| P30.10 | Woodies 5m panel | NOT STARTED | — | Needs bridge stream + panel |
| P30.11 | Full bridge stability | NOT STARTED | — | Michael approval needed |

## Next Single Thread

**P30.9b — Cumulative Delta pane** below price chart:
- Add GET API reading from Sierra `cumulative_delta.json`
- Render as candlestick-style delta bars in ChartV5b
- No bridge stream needed (direct file read like live_price)
