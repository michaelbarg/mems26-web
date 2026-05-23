# CC Follow-up — `v9_tpo_to_json` reads zero/uninitialized subgraph values

**Issued:** 2026-05-19 23:45 ET
**For:** Claude Code
**Predecessor:** docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md §4-4 (G4 DLL writer)

## Status

`MES_AI_DataExport.cpp` version `v9.4.1-p30.10t` **deployed and writing
`tpo.json` every <1 s — major progress**. But values are wrong: most
subgraph reads return 0.0, and one returns `-78229.0` (uninitialized).
The frontend will render zeros or garbage if we don't fix this.

## Current API output (curl evidence, 2026-05-19 23:44 ET)

```json
{
  "session": {"poc": 0.0, "vah": 0.0, "val": 0.0,
              "session_high": 7433.0, "session_low": 7353.75,
              "total_volume": 0.0},
  "ib": {"found": false, "high": 0.0, "mid": 0.0, "low": 0.0},
  "previous_session": {"found": true, "poc": -78229.0, "vah": 7384.58, "val": 0.0}
}
```

## Ground truth (Sierra live at the same minute)

| Field | Sierra value | DLL emits | Δ |
|---|---|---|---|
| session.poc (TODAY developing POC from Study ID:3) | 7411.25 magenta | 0.0 | ❌ |
| session.vah (TODAY developing VAH from Study ID:3) | 7395.00 magenta | 0.0 | ❌ |
| session.val (TODAY developing VAL from Study ID:3) | 7359.75 magenta | 0.0 | ❌ |
| session.session_high | 7433.00 | 7433.0 | ✅ |
| session.session_low | 7353.75 | 7353.75 | ✅ |
| ib.high (Study ID:6) | 7378.75 | 0.0 | ❌ |
| ib.mid (Study ID:6) | 7366.25 | 0.0 | ❌ |
| ib.low (Study ID:6) | 7353.75 | 0.0 | ❌ |
| ib.found | true (10:30 ET passed) | false | ❌ |
| previous_session.poc (Study ID:1, Reference=1) | 7411.25 white | -78229.0 | ❌❌❌ uninitialized |
| previous_session.vah (Study ID:1) | 7395.00 white | 7384.58 | ⚠️ off by ~10 |
| previous_session.val (Study ID:1) | 7390.75 white | 0.0 | ❌ |

## Likely root causes

1. **Wrong subgraph indices for Studies ID:1 / ID:3 (TPO Value Area Lines)**.
   Sierra Chart's `TPO Value Area Lines - Period` study uses sg[0]=POC,
   sg[1]=VAH, sg[2]=VAL by convention, but the actual indices for the
   `v9.4.1-p30.10t` build are returning 0 or trash. Open the study's
   Subgraphs tab in Sierra and confirm the exact `Subgraph Index` for
   each of POC, VAH, VAL. Then update the DLL.
2. **No null/`SC_STUDY_ARRAY_NA` guard before assigning**. The `-78229.0`
   for `previous_session.poc` is the giveaway — `sc.GetStudyArrayFromChartUsingID`
   returns uninitialized values when the source array doesn't exist or
   has no data. Wrap each read:
   ```cpp
   SCFloatArray poc_arr;
   sc.GetStudyArrayUsingID(study_id_1, 0 /* POC subgraph */, poc_arr);
   double poc_val = (poc_arr.GetArraySize() > 0)
                    ? poc_arr[poc_arr.GetArraySize() - 1]
                    : 0.0;  // or skip the field
   if (poc_val == 0.0 || poc_val == FLT_MAX || !is_finite(poc_val)) {
     poc_val = SC_STUDY_ARRAY_NA;  // backend will treat as missing
   }
   ```
3. **IB study read returns 0 / found=false**. Initial Balance (Study ID:6)
   only fills its subgraphs *after* 10:30 ET. At 23:44 ET (post-RTH),
   IB is final and should be readable. If `sc.GetStudyArrayUsingID`
   returns empty, double-check:
   - Is Study ID:6 actually on the chart this DLL runs on?
   - Are you passing the right `chartNumber` (use `sc.ChartNumber`
     for the host chart, not 0).
   - The IB subgraph names in Sierra are usually `IB High`, `IB Low`,
     `IB Mid`. Confirm the indices via Sierra's Edit Study → Subgraphs.
4. **`total_volume = 0`**. Same fix — read from TPO study volume subgraph,
   not unset.

## Acceptance (re-test these after redeploy)

```bash
# All session.* must match Sierra's magenta TPO lines on the chart
curl -s http://localhost:8000/api/v9/tpo/current \
  | jq '.session.poc, .session.vah, .session.val'
# Expected (drifts with the day): three positive floats near current price
# Today at ~23:44 ET: ~7411 / ~7395 / ~7360

# IB.found must be true after 10:30 ET
curl -s http://localhost:8000/api/v9/tpo/current \
  | jq '.ib'
# Expected: { "found": true, "high": ~7378.75, "mid": ~7366.25, "low": ~7353.75 }

# previous_session.poc must NEVER be < 0 — that's the smoking gun
curl -s http://localhost:8000/api/v9/tpo/current \
  | jq '.previous_session'
# Expected: { "found": true, "poc": ~7411.25, "vah": ~7395.00, "val": ~7390.75,
#             "opened_ts": "...", "closed_ts": "...", "session_date": "2026-05-18" }
```

Backend already normalises these — no Cursor-side changes needed once
the DLL emits real numbers.

## What's already working — do not regress

- `tpo.json` mtime <1 s ✓
- `session.session_high`, `session.session_low` ✓
- `previous_session` block present ✓
- File schema matches `_parse_previous_session_block` in
  `backend/v9/api/v9/tpo_routes.py:87-100` ✓

Also: `cumulative_delta.json` is still missing the `t` field per point
and `output_interval` at top level (G3). Backend fills `t` from
`CVD_PERIOD_S=1500` as a fallback — but please add `t` and
`output_interval` (300 if the host chart is 5 min) to the DLL emit so
the backend can drop the guess.
