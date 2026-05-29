# CC Handoff — S4 `current_bar` Routing Fix · 2026-05-28

**Owner:** Claude Code
**Author of handoff:** Cursor agent
**Approved by:** Michael (verbal 2026-05-28 19:48 IDT)
**Mode:** code edit + restart + UAT 4 axes (`.cursor/rules/mems26-pre-live-protocol.mdc`)
**Estimated time:** 30–45 min total (5 min edit + restart, rest is UAT + soak)

---

## §0 · TL;DR

Apply a 1-block change to `backend/v9/api/v9/bars.py` so that the bar routed to S4
(`_route_bar("woodies_5min", last_flat)`) is built from `payload.current_bar` when
present, instead of `history[-1]` (which is frozen for the last ~13 bars per the
DLL "frozen-tail" bug — see §1). Add one regression test. Restart backend.
Run UAT 4 axes. Report results back to Michael.

**This is NOT a fix for the DLL frozen-tail itself** (that stays open as a
strategic Pipeline-3 item). This is the cheapest, lowest-risk path to get S4
firing TODAY by routing Sierra's live-direct-read `current_bar` instead of the
clamped `history[-1]`.

---

## §1 · Required reading (read in this order BEFORE editing)

1. `docs/reports/AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md` — Cursor forensic
   audit. Read **§3 (parity table)**, **§6 (ranked hypotheses — especially #1
   and #2)**, **§8 (bottom line)**.
2. `docs/handoff/MEGA_PROMPT_CLAUDE_DESKTOP_S2_S4_AUDIT_2026-05-28.md` — the
   critical-review prompt that CC (you, earlier today) already executed.
3. CC's own independent critical review (already delivered in chat, recorded
   in `STATUS_BOARD.md` under "INDEPENDENT CC REVIEW"). Particularly **Claim 2
   (Backend ignores current_bar — CONFIRMED)** and **Q5 / Q3** which establish
   that `current_state` is updated from the just-routed bar — so routing
   the live `current_bar` is the single point that unblocks A5 sizing.
4. `docs/reports/DIAGNOSIS_S2_S4_BLOCKED_2026-05-28.md` — your earlier "no
   patterns" diagnosis. Now **superseded**, but read it so you don't repeat
   the same process error (concluding "no patterns" without querying
   `v9_woodies_signals`).
5. `.cursor/rules/mems26-pre-live-protocol.mdc` — pre-LIVE discipline. Especially
   the **4-step verification ritual** (read code → audit surfaces → verify
   hypothesis with data → confirm fix not already there) and the **4 UAT axes**
   (Quality, Recency, Cardinality, Latency).

---

## §2 · The fix (apply EXACTLY this)

**File:** `backend/v9/api/v9/bars.py`
**Function:** `post_woodies_5min` (around line 788)
**Lines to change:** the `last_flat` construction at the end of the per-bar
loop (currently lines 842–849) and the routing call at 851–852.

### Current code (lines 799–853)

```python
bars = payload.all_bars
if not bars:
    return {"ok": True, "inserted": 0, "type": "woodies_5min"}
created = 0
last_flat = None
for bar in bars:
    ohlc = bar.get("ohlc", {})
    o = ohlc.get("o", bar.get("o", bar.get("open", 0)))
    h = ohlc.get("h", bar.get("h", bar.get("high", 0)))
    l = ohlc.get("l", bar.get("l", bar.get("low", 0)))
    c = ohlc.get("c", bar.get("c", bar.get("close", 0)))
    vol = ohlc.get("vol", bar.get("vol", bar.get("volume", 0)))
    # ...DB INSERT block unchanged...
    last_flat = {
        "ts": bar.get("ts"), "open": o, "high": h, "low": l, "close": c,
        "volume": vol, "cci_14": bar.get("cci_14"),
        "cci_6_tcci": bar.get("cci_6_tcci"), "ema_34": bar.get("ema_34"),
        "lsma_value": bar.get("lsma_value"), "swi_value": bar.get("swi_value"),
        "czi_value": bar.get("czi_value"), "trend_state": bar.get("trend_state"),
        "predictor_next_cci": bar.get("predictor_next_cci"),
    }
_record_push("woodies_5min")
if last_flat:
    _route_bar("woodies_5min", last_flat)
return {"ok": True, "inserted": created, "type": "woodies_5min"}
```

### Replace with

Keep the DB INSERT loop **exactly as-is** (200 history rows still get persisted
for replay/audit). Add a `_flat_from_bar()` helper and override `last_flat`
with `current_bar` when present, AFTER the loop:

```python
bars = payload.all_bars
if not bars:
    return {"ok": True, "inserted": 0, "type": "woodies_5min"}
created = 0
last_flat = None

def _flat_from_bar(bar: Dict) -> Dict:
    """Project a Woodies payload bar (history item OR current_bar) into the
    flat dict shape expected by _route_bar / WoodiesSystem.process_bar.

    Both shapes carry the same Sierra study fields; OHLC may live either at
    top level or under `ohlc.*`.
    """
    ohlc = bar.get("ohlc", {}) or {}
    return {
        "ts": bar.get("ts"),
        "open":   ohlc.get("o",   bar.get("o",   bar.get("open",   0))),
        "high":   ohlc.get("h",   bar.get("h",   bar.get("high",   0))),
        "low":    ohlc.get("l",   bar.get("l",   bar.get("low",    0))),
        "close":  ohlc.get("c",   bar.get("c",   bar.get("close",  0))),
        "volume": ohlc.get("vol", bar.get("vol", bar.get("volume", 0))),
        "cci_14":             bar.get("cci_14"),
        "cci_6_tcci":         bar.get("cci_6_tcci"),
        "ema_34":             bar.get("ema_34"),
        "lsma_value":         bar.get("lsma_value"),
        "swi_value":          bar.get("swi_value"),
        "czi_value":          bar.get("czi_value"),
        "trend_state":        bar.get("trend_state"),
        "predictor_next_cci": bar.get("predictor_next_cci"),
    }

for bar in bars:
    # ...keep the entire DB INSERT block exactly as it was, INCLUDING the
    # `last_flat = {...}` assignment at the end of the loop body — DO NOT
    # delete it. The post-loop override below is additive.
    ...

_record_push("woodies_5min")

# === BEGIN current_bar routing override (Cursor audit §6 rank-2 fix) ===
# `history[-1]` is FROZEN for the last ~13 bars per the DLL `GetContaining
# IndexForDateTimeIndex` clamp (see AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28
# §1 + §3). `current_bar` is read via direct `arr[idx]` in
# `MES_AI_DataExport.cpp:582-621` and carries LIVE Sierra study values
# (e.g. cci_14=47.21 vs frozen history[-1].cci_14=49.70 at the same instant).
# Prefer it for routing to S4 so calculate_size() sees live SWI/TCCI.
if payload.current_bar:
    last_flat = _flat_from_bar(payload.current_bar)
# === END override ===

if last_flat:
    _route_bar("woodies_5min", last_flat)
return {"ok": True, "inserted": created, "type": "woodies_5min"}
```

### Acceptance criteria for the diff

- DB INSERT behavior is **byte-identical** (same 200 history rows still
  persisted; sentinel-2099 issue is NOT in scope here).
- `last_flat` falls back to `history[-1]` when `current_bar` is `None`/missing
  (preserves legacy behavior).
- `_route_bar("woodies_5min", last_flat)` is called **exactly once** per
  request (no double-route).
- No new `try/except Exception: pass` blocks. Silent error handling is
  forbidden pre-LIVE.

---

## §3 · Regression test (REQUIRED)

**File:** `tests/v9/api/test_bars_woodies_routing.py` (new file)

```python
"""Regression: post_woodies_5min routes current_bar (live) over history[-1] (frozen).

Pinning the AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28 §6 rank-2 fix. If the override
is ever reverted, this test must fail loudly.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.main import app  # noqa: WPS433  (import here for test isolation)
    return TestClient(app)


@pytest.fixture
def bridge_headers():
    # If the route requires a token, look up the local fixture pattern used by
    # other bars tests (e.g. test_chart_bars5min_integrity.py).
    return {"X-Bridge-Token": "dev"}  # adjust to match the project's auth


def _frozen_history_bar(ts: str, cci: float = 49.70, swi: float = -78.17,
                       tcci: float = -21.09) -> dict:
    return {
        "ts": ts,
        "ohlc": {"o": 7570.0, "h": 7572.0, "l": 7569.0, "c": 7571.5, "vol": 1000},
        "cci_14": cci, "cci_6_tcci": tcci, "swi_value": swi, "czi_value": 54.0,
        "trend_state": "BLUE", "ema_34": 7559.8, "lsma_value": 7577.9,
        "predictor_next_cci": 50.0,
    }


def test_current_bar_overrides_frozen_history_tail(client, bridge_headers):
    """When current_bar is present, _route_bar must receive its LIVE study
    values, not the (potentially frozen) history[-1].
    """
    frozen_history = [_frozen_history_bar(f"2026-05-28T17:{i:02d}:00Z")
                      for i in range(5, 20, 5)]  # 5 identical bars
    live_current = {
        "ts": "2026-05-28T17:20:00Z",
        "ohlc": {"o": 7573.0, "h": 7575.0, "l": 7572.0, "c": 7574.5, "vol": 1500},
        "cci_14": 47.21,            # LIVE — NOT 49.70
        "cci_6_tcci": -94.66,       # LIVE — NOT -21.09
        "swi_value": 12.34,         # LIVE — NOT -78.17
        "czi_value": 60.0,
        "trend_state": "BLUE",
        "ema_34": 7560.0,
        "lsma_value": 7578.0,
        "predictor_next_cci": 50.5,
    }
    payload = {
        "type": "woodies_5min",
        "history": frozen_history,
        "current_bar": live_current,
    }

    with patch("backend.v9.api.v9.bars._route_bar") as mock_route:
        resp = client.post("/api/v9/bars/woodies_5min",
                           json=payload, headers=bridge_headers)
        assert resp.status_code == 200, resp.text
        mock_route.assert_called_once()
        topic, flat = mock_route.call_args[0]
        assert topic == "woodies_5min"
        # The critical assertions: live values, not frozen.
        assert flat["cci_14"] == pytest.approx(47.21), \
            f"S4 received frozen history value instead of live current_bar: {flat['cci_14']}"
        assert flat["swi_value"] == pytest.approx(12.34)
        assert flat["cci_6_tcci"] == pytest.approx(-94.66)
        assert flat["ts"] == "2026-05-28T17:20:00Z"


def test_no_current_bar_falls_back_to_history_tail(client, bridge_headers):
    """Legacy behavior: when current_bar is None, _route_bar gets history[-1].
    Prevents the fix from accidentally silencing pushes that never carry
    current_bar.
    """
    history = [_frozen_history_bar(f"2026-05-28T17:{i:02d}:00Z", cci=42.0 + i)
               for i in range(5, 20, 5)]
    payload = {"type": "woodies_5min", "history": history}  # no current_bar

    with patch("backend.v9.api.v9.bars._route_bar") as mock_route:
        resp = client.post("/api/v9/bars/woodies_5min",
                           json=payload, headers=bridge_headers)
        assert resp.status_code == 200
        mock_route.assert_called_once()
        _, flat = mock_route.call_args[0]
        # history[-1] has cci = 42 + 15 = 57.0
        assert flat["cci_14"] == pytest.approx(57.0)
```

### Test acceptance criteria

- Both tests pass after the fix is applied.
- The first test FAILS when the fix is reverted (proof of regression value).
- No new failures in `pytest tests/v9/api/ -q` beyond the pre-existing 11 from
  the day_type/IB work.

---

## §4 · Pre-restart checklist

Before kicking the backend, verify:

1. `pytest tests/v9/api/test_bars_woodies_routing.py -q` → both tests **PASS**.
2. `python -c "from backend.main import app; print('import ok')"` → no import errors.
3. `ReadLints` (or `ruff check backend/v9/api/v9/bars.py`) → no new lints.

---

## §5 · Restart backend (CC has terminal access; Cursor sandbox cannot)

```bash
# 1) Confirm current PID
ps -ef | grep -E "uvicorn.*backend.main" | grep -v grep
# Expected: PID 49483, started Thu May 28 18:34:51

# 2) Kill cleanly
kill -9 49483

# 3) Start fresh (matches the start_all.sh contract — local-only)
cd /Users/michael/Downloads/mems26_web_git
nohup python3 -m uvicorn backend.main:app \
    --host 127.0.0.1 --port 8000 \
    > /tmp/backend.log 2>&1 &
NEW_PID=$!
echo "new pid=$NEW_PID"
sleep 10
```

Sanity:

```bash
curl -s -o /dev/null -w "status=%{http_code}\n" http://localhost:8000/api/v9/status
# Expected: status=200

tail -50 /tmp/backend.log
# Expected: clean uvicorn startup, no traceback
```

---

## §6 · UAT — 4 axes (mandatory per pre-LIVE protocol)

Run all four. **Do NOT declare green unless all four PASS.** This is the
discipline P27.5a violated; do not repeat that mistake.

### Axis 1 — Quality (current_bar values reach the buffer)

```bash
# Snapshot the current woodies_5min export and the live S4 buffer
python3 << 'PY'
import json, os, urllib.request
exp_path = os.path.expanduser('~/SierraChart_Data/v9_export/woodies_5min.json')
exp = json.load(open(exp_path))
cur = exp.get('current_bar') or {}
print(f"DLL current_bar: cci_14={cur.get('cci_14')} swi={cur.get('swi_value')}"
      f" tcci={cur.get('cci_6_tcci')} ts={cur.get('ts')}")

# Compare to S4's in-memory state via cockpit snapshot
data = json.load(urllib.request.urlopen(
    'http://localhost:8000/api/v9/cockpit/systems-snapshot', timeout=5))
for sys in data.get('systems') or []:
    if sys.get('id') in ('woodies', 'woodies_5min', 's4'):
        state = sys.get('state') or {}
        print(f"S4 state: cci_14={state.get('cci_14')} swi={state.get('swi_value')}"
              f" tcci={state.get('cci_6_tcci')}")
PY
```

**PASS:** S4 state's `cci_14 / swi_value / cci_6_tcci` equal the DLL
`current_bar` values **±0.1** (and CRUCIALLY are NOT the frozen `49.70 / -78.17 /
-21.09` from the audit's snapshot).

**FAIL:** S4 state still shows the frozen values → fix didn't activate; check
for stale Python bytecode in `backend/v9/api/v9/__pycache__/bars.cpython-*.pyc`
(delete and restart) or verify the diff was saved.

### Axis 2 — Recency (newly routed bar feeds detectors within 5s of arrival)

```bash
# Watch bridge push and S4 last-process timestamp
for i in 1 2 3 4 5 6; do
  curl -s http://localhost:8000/api/v9/status | python3 -c "
import json, sys, time
d = json.load(sys.stdin)
print(f'now={time.time():.0f}  '
      f\"router.received={d.get('bar_router', {}).get('received')}  \"
      f\"sierra.last_write_age={d.get('sierra', {}).get('last_write_age_s')}\")"
  sleep 5
done
```

**PASS:** `router.received` increments at least every 10s during RTH;
`sierra.last_write_age_s` stays under 5s.

### Axis 3 — Cardinality (S4 actually fires when sizing is no longer frozen)

```bash
# Snapshot signals + trades BEFORE restart timestamp; then watch new entries
START_TS=$(date +%s)
echo "start=$START_TS"
sleep 600  # 10-minute soak window during RTH

sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db <<SQL
.headers on
.mode column
-- New signals since the fix
SELECT ts_unix, pattern_id, direction, confidence, cci_14
FROM v9_woodies_signals
WHERE ts_unix >= $START_TS
ORDER BY ts_unix DESC LIMIT 20;

-- New fired trades since the fix
SELECT id, ts_open, pattern_id, direction, status,
       json_extract(cross_context, '$.woodies_system.decision_tree.failed_stages') AS failed
FROM v9_trades
WHERE ts_open >= datetime($START_TS, 'unixepoch')
ORDER BY ts_open DESC LIMIT 20;
SQL
```

**PASS:** at least one new `v9_woodies_signals` row appears AND `failed`
includes patterns where `A5` is **no longer** in the failed list (or the
trade itself fires, status=`OPEN`/`SHADOW_OPEN`).

**FAIL (acceptable for one bar):** signals appear but A5 still rejects on
every fire — capture the `cross_context.woodies_system.swi_value/cci_6_tcci`
of one failing trade and report back; this likely means current_bar itself
carries stale values for that bar.

### Axis 4 — Latency

```bash
for ep in /api/v9/status /api/v9/cockpit/systems-snapshot \
          "/api/v9/woodies/chart?limit=20" /api/v9/key_levels; do
  curl -s -o /dev/null -w "  $ep  status=%{http_code}  time=%{time_total}s\n" \
       "http://localhost:8000$ep"
done
```

**PASS:** all endpoints under **300ms** (status / key_levels target <100ms;
chart endpoints may take up to 300ms with the parse).

---

## §7 · If something blows up — rollback

1. Restore `backend/v9/api/v9/bars.py` from `git restore` if you have a clean
   working tree, OR revert just the `# === BEGIN ... # === END ===` block.
2. Delete `tests/v9/api/test_bars_woodies_routing.py`.
3. Restart backend per §5.
4. Report what failed (with the 4-axes output) to Michael. **Do not iterate
   silently.**

---

## §8 · After UAT — what to update

If all 4 axes PASS:

1. Add an entry to `docs/plans/STATUS_BOARD.md` under the new
   `2026-05-28 · S4 current_bar Routing Fix (CC)` section: timestamp,
   diff summary, 4-axes results, new signals count, any A5 still-failing
   patterns observed.
2. Append the regression test name to `tests/v9/api/__init__.py`-style
   pytest collection if any (most projects auto-discover; skip if so).
3. Do **NOT** mark the DLL frozen-tail item as closed. That stays open per §9.

If any axis FAILS:

1. Capture the failing axis output verbatim.
2. Append to STATUS_BOARD as `🔴 BLOCKED`.
3. Do NOT keep trying. Strategic-stop and report to Michael.

---

## §9 · Remaining open work (after this fix)

See companion file `docs/handoff/OPEN_ITEMS_PRE_LIVE_2026-05-28.md` for the
full backlog. This fix closes **none** of those items on its own; it only
unblocks S4 from firing today. The DLL frozen-tail bug remains open as the
strategic root cause.
