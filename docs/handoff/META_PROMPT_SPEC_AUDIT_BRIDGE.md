# META-PROMPT · SPEC AUDIT · Bridge Data Routing
**Version:** 1.0 · 2026-05-27
**For:** Claude Desktop → send to Claude Code (CC)
**Owner audit:** Cursor (verifies CC report)
**Scope:** Bridge — all 12 streams, field completeness, routing to all components

---

## CONTEXT

The bridge reads DLL JSON exports from `~/SierraChart_Data/v9_export/` and
pushes data to `http://localhost:8000` (local backend). It must:
1. Send ALL required fields per stream
2. Route to ALL relevant backend endpoints
3. Never push to cloud/remote URLs (Bridge Local-Only Rule)

**Source of truth:**
- `bridge/v9_streams/` — 12+ stream files
- `bridge/v9_streams/base_stream.py` — shared push logic, Chicago-TS fix
- `~/Library/LaunchAgents/com.mems26.bridge.plist` — LaunchAgent config

---

## YOUR TASK (CC)

Run the following 6 checks. Report PASS/FAIL/WARN for each.

---

### CHECK 1 · Stream Inventory — All Streams Present

List all stream classes and their target endpoints:

```bash
grep -r "api_path\s*=" bridge/v9_streams/*.py | grep -v "__pycache__"
```

Expected streams (at minimum):
| Stream name | File | Endpoint |
|---|---|---|
| woodies_5min | woodies_5min_stream.py | /api/v9/bars/woodies_5min |
| woodies_30min | woodies_30min_stream.py | /api/v9/bars/woodies_30min |
| bars_5min | bars_5min_stream.py | /api/v9/bars/5min |
| tpo | tpo_stream.py | /api/v9/tpo/... |
| footprint | footprint_stream.py | /api/v9/footprint/... |
| cumulative_delta | cumulative_delta_stream.py | /api/v9/... |
| volume_profile | volume_profile_stream.py | /api/v9/... |
| imbalance_flags | imbalance_flags_stream.py | /api/v9/... |
| stacked_imbalances | stacked_imbalances_stream.py | /api/v9/... |
| tick_reversal_12 | tick_reversal_12_stream.py | /api/v9/... |
| tick_reversal_15 | tick_reversal_15_stream.py | /api/v9/... |
| live_price | live_price_stream.py | /api/v9/... |

**PASS criteria:** All 12 streams exist and have non-empty `api_path`.

---

### CHECK 2 · woodies_5min Field Completeness (Critical)

**Spec (D-074):** The DLL exports these fields for each bar:
`ts · o · h · l · c · vol · cci_14 · cci_6_tcci · lsma_value · swi_value · czi_value ·
ema_34 · trend_state · predictor_next_cci · zlr_detected · zlr_direction`

Plus HFE divergence fields (added in Pipeline 2):
`hfe_detected · hfe_direction · hfe_extreme_bars_ago`

**Verify:**
```bash
# Check what fields the stream pushes
cat bridge/v9_streams/woodies_5min_stream.py

# Check that backend endpoint accepts HFE fields
rg "hfe_detected\|hfe_direction\|hfe_extreme_bars_ago" \
    backend/v9/api/ -r | head -20

# Check a real export file if Sierra is running
ls -la ~/SierraChart_Data/v9_export/woodies_5min.json 2>/dev/null && \
    python -c "
import json
data = json.load(open('/Users/michael/SierraChart_Data/v9_export/woodies_5min.json'))
bars = data.get('history', data.get('bars', []))
if bars:
    print('Fields in last bar:', list(bars[-1].keys()))
else:
    print('No bars in export file')
"
```

**PASS criteria:** Export file contains all DLL fields including HFE fields.
`woodies_5min_stream.py` pushes to correct endpoint.

---

### CHECK 3 · Chicago-TS Fix Status

**Spec:** Until DLL timestamp fix is deployed (Sierra Remote Build), the bridge
must re-interpret bar.ts as Chicago-local-time and convert to UTC.
Flag `V9_DISABLE_CHICAGO_TS_FIX` controls this.

```bash
# Check current env flag in LaunchAgent
grep -A 5 "CHICAGO" ~/Library/LaunchAgents/com.mems26.bridge.plist 2>/dev/null || \
    echo "Flag not in plist — check .env"
grep "CHICAGO_TS" bridge/.env 2>/dev/null || echo ".env not found"
# Check the fix code is still active
grep "_DISABLE_CHICAGO_TS_FIX\|_fix_chicago_ts" \
    bridge/v9_streams/base_stream.py | head -10
```

**PASS criteria:** Fix is ACTIVE (flag not set to 1) unless DLL has been
rebuilt and verified to output correct UTC timestamps.

**WARN:** If `V9_DISABLE_CHICAGO_TS_FIX=1` but DLL fix not confirmed, this is a
**LIVE blocker** — bars will arrive 5-6h behind real UTC.

---

### CHECK 4 · CLOUD_URL Local-Only Guard

**Spec (CLAUDE.md):** Bridge must refuse to start if `CLOUD_URL` is not localhost.
The guard is in `base_stream.py` lines 39-44.

```bash
python -c "
import os
os.environ['CLOUD_URL'] = 'https://mems26-web.onrender.com'
try:
    import bridge.v9_streams.base_stream
    print('ERROR: guard did not fire!')
except RuntimeError as e:
    print('PASS: guard fired:', str(e)[:80])
"
```

**PASS criteria:** `RuntimeError` is raised when non-local CLOUD_URL is set.

---

### CHECK 5 · All Streams Registered in Bridge Main

```bash
cat bridge/bridge_main.py 2>/dev/null || cat bridge/main.py 2>/dev/null || \
    find bridge/ -name "*.py" | xargs grep -l "Woodies5MinStream\|start()" | head -5
```

Confirm that every stream class from Check 1 is instantiated and `.start()`-ed
in the main bridge entry point.

**PASS criteria:** All 12 streams are started. No stream is defined but never started.

---

### CHECK 6 · Live Push Verification (if services running)

If the bridge is currently running:
```bash
tail -50 /tmp/bridge.err.log 2>/dev/null | grep -E "FAILED|ERROR|push" | tail -20
tail -20 /tmp/bridge.out.log 2>/dev/null
```

Check for any `API push FAILED` messages (these indicate routing failures).

**PASS criteria:** No `FAILED` messages in last 50 lines. Push counts incrementing.
**FAIL criteria:** Any `API push FAILED to https://...` = config drift — stop immediately.

---

## REPORT FORMAT

```
## Bridge Data Routing — Spec Audit Results · [DATE]

| Check | Title | Result | Notes |
|-------|-------|--------|-------|
| 1 | Stream Inventory (12) | ✅ / ⚠️ / ❌ | X/12 streams found |
| 2 | woodies_5min Fields | ... | missing: [...] |
| 3 | Chicago-TS Fix | ... | enabled/disabled |
| 4 | CLOUD_URL Guard | ... | ... |
| 5 | All Streams Started | ... | ... |
| 6 | Live Push Health | ... | ... |

## Missing fields (if any):
[List fields missing from export vs spec]

## Streams not started (if any):
[List stream names]

## LIVE blockers:
[List anything that must be fixed before LIVE]
```

---

## STOP SIGNALS

Stop immediately if:
- `CLOUD_URL` guard does NOT fire with remote URL (Check 4 FAIL) — critical bug
- Any `API push FAILED to https://...` in logs — bridge is pushing to cloud
- `V9_DISABLE_CHICAGO_TS_FIX=1` but DLL fix not confirmed (Check 3)
- Any stream is missing from the started list (Check 5)
