# P30.SHADOW — GREEN Checklist

**Date:** 2026-05-19  
**Branch:** `stabilize/mems26-local-truth-2026-05-16`  
**Replay head (G1):** `2026-05-18 10:30:00 ET`  
**Verdict:** **GREEN** — SHADOW soak go

---

## Evidence summary

| Check | Result | Evidence |
|-------|--------|----------|
| Backend heartbeat | PASS | `mode=shadow`, `alive=true`, &lt;2ms typical |
| bars5min 4-axis | PASS | 600/600, recency=DB max, bad_count=0, 91ms |
| TPO/CVD APIs | PASS | `sierra_tpo_json`, parity poc/vah/val ±0.25 (3/3) |
| systems-snapshot | PASS | HTTP 200, 3ms |
| shadow/soak_progress | PASS | Day 6/30 |
| gateway/status | PASS | HTTP 200, no LIVE slots armed |
| 11m live soak | PASS | 22 probes @ 30s, 0 failures; max latency hb=149ms br=575ms |
| pytest regression | PASS | 11 API + 36 shadow gateway/schema |
| Browser UAT | PASS | TopBar SHADOW (not LIVE), chart+candles+CVD+TPO, Day 6/30 strip |
| Bridge | PASS | `json_bridge.py --bars-5min-only`, `CLOUD_URL=localhost:8000` |

**Soak log:** `/tmp/p30_shadow_soak_20260519_120447.log`

---

## Browser checklist (autonomous 2026-05-19)

| Item | PASS |
|------|------|
| Chart visible without Max click (default height) | ✓ |
| CVD inline (same chart pane) | ✓ |
| Stepped POC + VAH/VAL dashed | ✓ |
| TopBar SHADOW highlighted, LIVE greyed | ✓ |
| Shadow tab + OVERNIGHT MODE + Day 6/30 footer | ✓ |
| No LIVE arm / gateway live_slot null | ✓ |
| Cyan IB | **PASS** (G1 2026-05-19: `ib.found=true`, ib 7454.25/7415.25, chart cyan line) |

**Note:** One transient `ChartV5b load error: Failed to fetch` on stale tab during HMR; fresh load at `http://127.0.0.1:3000` rendered chart. WS price reconnects are non-blocking (live_price poll).

---

## Deferred (not SHADOW blockers)

- **G1 IB** — **GREEN** (replay 2026-05-18 session; see `PROMPT30_9_SIERRA_SCREEN_PARITY.md` G1 row).
- **P30.10 Woodies** — CCI panel needs `woodies_5min` stream.
- **P30.11** — full 12-stream bridge.
- **Redis/WS** — optional; document if DISCONNECTED appears with stale poll.

---

## Michael morning commands

```bash
REPO=/Users/michael/Downloads/mems26_web_git
# Verify listeners
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:3000 -sTCP:LISTEN
curl -m 2 http://127.0.0.1:8000/api/v9/cockpit/heartbeat
open http://127.0.0.1:3000
# If bridge down:
pgrep -fl "json_bridge.py --bars-5min-only" || (cd $REPO/bridge && set -a && source ../.env && set +a && \
  export CLOUD_URL=http://localhost:8000 V9_DISABLE_WATCHDOG=1 V9_SKIP_HISTORY=1 && \
  nohup python3 json_bridge.py --bars-5min-only >> /tmp/bridge_bars_only.log 2>&1 &)
```

---

*SHADOW soak go — 2026-05-19 Cursor autonomous UAT.*
