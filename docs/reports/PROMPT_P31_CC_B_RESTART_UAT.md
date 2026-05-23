# P31 CC-B — Backend Restart + Journal UAT

**Date:** 2026-05-21 ~14:00 ET  
**Owner:** Cursor (Michael approved)  
**Scope:** Backend reload only — no bridge/DLL/LaunchAgent changes

---

## Actions

| Step | Result |
|------|--------|
| Kill stale uvicorn (PID 15775) | ✅ |
| Start `uvicorn backend.main:app` on `127.0.0.1:8000` | ✅ **PID 45069** |
| Migration `016_v9_trades_journal_index.sql` | ✅ `ix_v9_trades_mode_entry_ts` present |
| Bridge | Untouched — still running (`json_bridge.py`) |

---

## UAT (four axes where applicable)

| Endpoint | Quality | Recency | Cardinality | Latency |
|----------|---------|---------|-------------|---------|
| `GET /api/v9/health` | HTTP 200 | — | — | **0.005s** |
| `GET /trades/log?types=shadow&limit=50` | 21 rows JSON | DB-backed | `len=21` ≤ 50 | **0.04s** ✅ (&lt;5s gate) |
| `GET /api/v9/cockpit/systems-snapshot` | 6 systems | live | count=6 | **&lt;12s** |
| `GET /api/v9/five_min/current` | `running=True` | — | — | **&lt;8s** |
| `GET /api/v9/trades/active` | trade **696** open | — | 1 active | **&lt;3s** |
| `GET /api/v9/gateway/status` | Not probed | — | — | Known slow under load (P30) |

---

## P31-01 — waiting on Michael

1. Cockpit side panel → **Exit** on active trade **696** (or let BarLevelDetector close in RTH).
2. Verify:
   ```bash
   sqlite3 data/mems26_local.db \
     "SELECT id,state,exit_reason,pnl_usd,pnl_r FROM v9_trades WHERE id=696;"
   curl -s "http://127.0.0.1:8000/trades/log?types=shadow&limit=5" | python3 -c "import sys,json; print(json.load(sys.stdin)[0].get('pnl_usd'), json.load(open('/dev/stdin'))[0].get('close_reason'))"
   ```
3. Journal UI `/journal` — same `pnl_usd`, C1/C2/C3 columns visible.

**Smart BE note:** After T1, stop moves to entry; `initial_stop` in `quality` preserves risk denominator.

---

## Bridge note

`grep -c "Connection refused" /tmp/bridge.err.log` → **88** (historical). Pushes to `:8000` observed in `/tmp/backend.log` after restart. CC may trim err log baseline if Michael wants.

---

## Next

| ID | Owner | Task |
|----|-------|------|
| P31-01 | Michael | Exit + P&L visual UAT |
| P31-PAT | Michael+CC | RTH pattern vs `active_patterns` |
| P31-02 | CC | S2 fire log in RTH (`CC-C`) |
| P-S0 | Michael | After P0 green |
