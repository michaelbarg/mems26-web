# P30.2 — Browser Visual Data Proof

**Date:** 2026-05-18  
**Status:** PARTIAL GREEN — cockpit data is visible; `/api/v9/status` latency is a blocker before full visual gate  
**No services started. Used already-running backend/frontend only. No SHADOW/DEMO/LIVE activation. No trade command writes.**

---

## Summary

P30.2 verified the existing MEMS26 cockpit in the browser at:

`http://127.0.0.1:3000/`

The cockpit is rendering real data:

- 5-minute historical candles are visible.
- Volume overlay is visible.
- TPO levels are visible on the chart.
- TopBar mode/day type/killzone/status elements are visible.
- Right side panel is visible with ActiveTradeCard, Switcher, Lens tabs.
- S1-S6 selectors are visible, split as firing/observing.
- Browser network evidence showed key system endpoints returning data.

However, this is **not a full clean GREEN** because direct probes of
`/api/v9/status` timed out at 5s, 10s, and 20s. The screen can render, but the
status endpoint is not reliable enough for the operator dashboard gate.

---

## Browser Evidence

Browser verification observed:

| Area | Result |
|---|---|
| URL loaded | PASS — `http://127.0.0.1:3000/` |
| Page title | PASS — MEMS26 V9 Dashboard |
| 5m chart | PASS — historical candles visible |
| Volume overlay | PASS — volume bars visible at chart bottom |
| TPO levels | PASS — IB H/L and VAH/VAL labels visible |
| Live price polling | PASS — `/api/v9/live_price` observed |
| TopBar | PASS — SHADOW mode, MES, day/status/killzone elements visible |
| Right panel | PASS — ActiveTradeCard, Switcher, Lens tabs visible |
| S1-S6 | PASS — selectors `2,3,4` and `1,5,6` visible |
| WebSockets | PASS — S1-S6 signal sockets observed connected |
| Console | WARN — React hydration warning, non-blocking but should be fixed |

Visual caveat:

- A React/Next hydration overlay partially obscured the lower chart area during
  the browser session. It did not prevent data rendering, but it blocks a clean
  operator-grade screenshot.

---

## Bars5min UAT Axes

Direct probe of `/api/v9/chart/bars5min?limit=240`:

| Axis | Result |
|---|---|
| Quality | PASS — `bad_count=0` |
| Recency | PASS — endpoint latest equals DB `MAX(ts)` |
| Cardinality | PASS — `count=240` |
| Latency | PASS — `30.4ms` |

Evidence:

```text
bars5min_status=200
bars5min_count=240
bars5min_bad_count=0
bars5min_latest_ts=2026-05-17 16:15:00.000000
db_max_ts=2026-05-17 16:15:00.000000
recency_match=true
latency_ms=30.4
```

---

## Endpoint Probe Evidence

| Endpoint | Result | Latency / Note |
|---|---|---|
| `/api/v9/live_price` | PASS | `200`, `2.32ms` |
| `/api/v9/tpo/current` | PASS | `200`, `2.58ms` |
| `/api/v9/killzone/current` | PASS | `200`, `1.04ms` |
| `/api/v9/day_type/v9/current` | PASS | `200`, `2.59ms` |
| `/api/v9/five_min/current` | PASS | `200`, `1.76ms` |
| `/api/v9/footprint/current` | PASS | `200`, `1.16ms` |
| `/api/v9/woodies/current` | PASS | `200`, `1.13ms` |
| `/api/v9/status` | FAIL | timed out at 5s, 10s, and 20s |

Browser network reportedly saw `/api/v9/status` respond, but direct probes
timed out repeatedly. Treat direct probe evidence as the operational blocker.

---

## What Michael Can See Now

Michael can now see:

- historical 5m bars on the cockpit chart;
- TPO levels;
- volume overlay;
- live price-driven forming bar behavior;
- TopBar mode/context;
- right-side S1-S6 cockpit structure;
- ActiveTradeCard area and system Lens tabs.

This is the first visual proof that the cockpit has a real data foundation.

---

## Not Yet Proven Clean

Before calling the screen operator-ready:

1. Fix or diagnose `/api/v9/status` timeout.
2. Remove/fix the React hydration warning/overlay.
3. Confirm rendered bar count from the chart UI, not only from endpoint data.
4. Confirm scroll-left loads older bars in the browser without duplicates.
5. Relabel Killzone UI so D-061 context does not look like a hard trade block.
6. Disable or gate existing `ActiveTradeCard` POST buttons before DEMO/LIVE work.

---

## Recommended Next Step

Open P30.3:

**P30.3 — Status Endpoint + Hydration Overlay Fix**

Scope:

- diagnose `/api/v9/status` timeout with data;
- fix only the smallest root cause;
- fix or suppress the React hydration mismatch by making TopBar SSR/client output stable;
- rerun P30.2 visual proof after fix.

Do not start SHADOW/DEMO/LIVE. Do not write `trade_command.json`.

