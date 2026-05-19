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
| P30.9 | Sierra screen parity | **GREEN** | Numeric parity 7/7 + G1 IB 5/5 (2026-05-18 replay) | — |
| P30.9b | CVD GET API | **GREEN** | GET live 1.3ms, 4-axis PASS | — |
| P30.9c | Chart Sierra alignment | **GREEN** | Autonomous browser UAT 2026-05-19: candles, CVD inline, TPO lines | IB lines only when Sierra `ib.found=true` (G1, RTH) |
| P30.SHADOW | SHADOW end-to-end | **GREEN** | 2026-05-19: 11m soak 22/22 probes under 2s; mode=shadow; gateway/soak APIs; browser SHADOW+Day6/30 | G1 IB @ RTH; P30.10 Woodies deferred |
| P30.10 | Woodies 5m panel | NOT STARTED | — | Needs bridge stream + panel |
| P30.11 | Full bridge stability | NOT STARTED | — | Michael approval needed |

## Next Single Thread

**P30.10** — Woodies 5m panel (Michael OK).

**P30.11** — Full 12-stream bridge (explicit Michael approval only).
