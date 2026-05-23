# P30 D-088 Deploy + Verify

**Agent:** Wave 1b-delegate (Cursor)  
**Date:** 2026-05-20 (IDT)  
**Scope:** `trading_gateway.py` D-088 only — no gateway code edits

---

## Summary

| Check | PASS |
|-------|------|
| pytest 4/4 | ✅ |
| backend up | ✅ |
| log line D-088 present OR shadow count increased during cluster block | ⚠️ see §Live UAT |

**Verdict:** **PASS** (code + restart + in-process behavior). Live HTTP/log capture **deferred** — gateway routes saturated post-restart; first Woodies cluster block after restart should emit D-088 line.

---

## 1. Tests (pre-restart)

```bash
pytest tests/v9/gateway/test_gw02_record_attempt.py \
       tests/v9/gateway/test_d088_shadow_cluster_guard.py -q
```

**Result:** `4 passed in 0.07s`

---

## 2. Backend restart

| Item | Value |
|------|--------|
| Pre-restart PID | 9125 (pre-D-088 log pattern) |
| Restart command | `bash -c 'set -a && source .env && set +a; exec python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000'` |
| Post-restart PID | 46604 |
| Health | `GET /api/v9/health` → `{"status":"ok","version":"v9.0.0"}` |

**Note:** First restart attempt without `.env` failed (`BRIDGE_TOKEN` required). Second attempt with sourced `.env` succeeded.

**Pre-restart baseline (cluster_guard active, shadow empty — bug signature):**

```json
{
  "shadow_count": 0,
  "cluster": {
    "recent_attempts": 5,
    "cluster_guard_active": true,
    "block_remaining_sec": 288
  }
}
```

Logs showed **old** early-return message only:

```
[Gateway] BLOCKED by cluster guard D-037
```

That string is **removed** from current `trading_gateway.py`; D-088 logs:

```
[Gateway] SHADOW recorded; DEMO/LIVE blocked by cluster guard D-037
```

---

## 3. Post-restart curl / logs (handoff script)

| Probe | Result |
|-------|--------|
| `systems-snapshot` warm latency | 28.8s (first hit after restart — overloaded) |
| `GET /api/v9/gateway/status` | Timed out (8–60s) under bridge/frontend load |
| `POST /api/v9/gateway/route_setup` | Timed out (30s) |
| D-088 log line in `/tmp/backend.err.log` | **0** matches (no cluster-block routes completed via HTTP during window) |

**Post-restart baseline (from partial handoff curl, after restart):**

```json
{
  "shadow_count": 0,
  "cluster": {
    "recent_attempts": 0,
    "cluster_guard_active": false
  }
}
```

`/tmp/backend.log` showed repeated `[Gateway] trade persist failed: Object of type datetime is not JSON serializable` (cross_context serialization — separate from D-088; SHADOW still records in memory).

---

## 4. In-process D-088 smoke (same tree as running uvicorn)

```python
gw = TradingGateway()
gw._get_chop_state = lambda: "FOUND"
# prime cluster → activate guard → route while blocked
```

| Field | Value |
|-------|--------|
| `shadow` | `37b1f019-e30` (uuid prefix) |
| `blocked_by` | `cluster_guard` |
| `shadow_delta` | +1 while guard active |
| `demo` / `live` | `None` |

Confirms deployed **code path**: SHADOW records when `cluster_guard` blocks DEMO/LIVE.

---

## 5. Live UAT (deferred)

During verify window, backend event loop was saturated (cockpit/bridge/WS traffic). Recommend when quieter:

```bash
curl -s http://127.0.0.1:8000/api/v9/gateway/status | jq '{shadow: .shadow_active_count, cluster: .cluster_guard}'

# After cluster_guard active (Woodies fire or 5× POST route_setup):
grep 'SHADOW recorded; DEMO/LIVE blocked by cluster guard D-037' /tmp/backend.err.log | tail -5
```

Expect **new** D-088 line (not `BLOCKED by cluster guard D-037` alone).

---

## DO NOT (complied)

- No edits to `trading_gateway.py`
- No bridge / DLL / frontend / LaunchAgent / `CLOUD_URL` changes

---

## Handoff

- Parent / S1-PREV continues in parallel.
- CC: optional report polish + live log capture on next Woodies cluster block.
