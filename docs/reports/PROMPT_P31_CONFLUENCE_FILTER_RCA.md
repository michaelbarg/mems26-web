# Confluence Filter — Root Cause Analysis + Fix Plan

**Discovered:** 2026-05-21 via the new `/trades` Confluence filter
**Status:** Investigation complete; no code changes yet.
**Owner:** Cursor agent (this thread); will hand to CC for the fix once Michael approves.

## The symptom

On the `/trades` page, applying `LIVE-eligible only` + `All systems agree`
returns **3 trades out of 200** (1.5%). All 3 lose. That cannot be the
real confluence rate of the shadow journal — it has to be a bug.

## What the data shows

Direct DB query on the latest 200 shadow trades (V9Trade.cross_context):

| SID | Name       | agree | disagree | neutral | firing |
|----:|------------|------:|---------:|--------:|-------:|
| 1   | Day Type   |   0   |     0    |  **200**|    0   |
| 2   | 5-Min      |   0   |     0    |  **200**|    0   |
| 3   | Footprint  |  89   |    61    |    50   |    0   |
| 4   | Woodies    | 184   |    16    |     0   |  200   |
| 5   | TPO        |   0   |     2    |  **198**|    0   |
| 6   | Killzone   |  46   |  **154** |     0   |    0   |

Two distinct problems, two roots.

## Root cause 1 — S6 (Killzone) `_system_agrees` ignores direction

`backend/v9/services/trade_context.py` lines 249–256:

```249:256:backend/v9/services/trade_context.py
    if sid == 6:
        cz = blob.get("current_zone") if isinstance(blob.get("current_zone"), dict) else blob
        edge = cz.get("edge_class") if isinstance(cz, dict) else None
        if edge == "high":
            return True
        if edge == "low":
            return False
        return None
```

This returns `True` / `False` **without looking at the trade direction**.
It just says: "high edge → agree, low edge → disagree" for every trade.

Distribution of the Killzone edge across the 200 shadow trades:

| edge | zone     | LONG | SHORT | Total |
|------|----------|-----:|------:|------:|
| low  | MIDDAY   |  73  |  82   |  155  |
| high | NY_OPEN  |  29  |  16   |   45  |

So all 155 trades with `edge=low` are forced to `disagree`, regardless of
direction — even though a LONG off the low edge is the classic fade
setup. That single bug accounts for **154 out of 154 S6 disagrees**.

### What the logic should be

In MEMS26's Killzone framework, edge = where price sits inside the active
killzone band. The natural fade-style alignment is:

| edge   | Expected trade direction | agree if |
|--------|--------------------------|----------|
| `low`  | LONG (bounce off support of the zone)    | `d == "LONG"`  |
| `high` | SHORT (rejection off resistance)          | `d == "SHORT"` |
| else   | unknown                                   | `None`         |

Confirm this matches the Killzone spec before patching — but the current
code clearly cannot be right, because it produces opposite verdicts for
LONG and SHORT trades at the same price level.

### Fix (single hunk, 4 lines)

```python
    if sid == 6:
        cz = blob.get("current_zone") if isinstance(blob.get("current_zone"), dict) else blob
        edge = cz.get("edge_class") if isinstance(cz, dict) else None
        if edge == "high":
            return d == "SHORT"
        if edge == "low":
            return d == "LONG"
        return None
```

That's the minimum-blast-radius change. Same return shape, same input,
direction-aware.

### Expected effect on the confluence filter

Before: 154 S6 `disagree` → most trades excluded by `All systems agree`.

After (mechanical projection):
- 73 LONG × `edge=low` → flip from disagree → agree
- 16 SHORT × `edge=high` → flip from disagree → agree
- 82 SHORT × `edge=low` → stay disagree
- 29 LONG × `edge=high` → stay disagree

→ S6 disagree drops from 154 to 111; S6 agree rises from 46 to 135.
The downstream `All systems agree` count should jump roughly 30–50×.

## Root cause 2 — S1 / S2 / S5 blobs are empty in cross_context

Same 200 shadow trades, sample blob from the newest 3 (id 1060–1062):

```
day_type_machine = {}
five_min_system = {}
tpo_system.poc_migration = MISSING
```

`cross_context[0].systems` is set by
`backend/v9/services/snapshot_service/snapshot.py::CrossSystemSnapshotService.capture`
at entry time. Three observer systems are not delivering their state into
that snapshot:

1. **S1 (Day Type machine)** — key `day_type_machine` or
   `day_type_system` exists but is `{}`. The day-type V9 endpoint
   (`/api/v9/day_type/v9/current`) works, so the data is computed —
   it's just not being plumbed into the gateway registry at fire-time.

2. **S2 (5-Min system)** — `five_min_system = {}`. Same root: the
   wrapper isn't publishing `mode`, `last_classification`, etc. to the
   registry.

3. **S5 (TPO)** — `tpo_system` is populated with `poc / vah / val /
   profile_shape`, but **not** `poc_migration`. The
   `_system_agrees(sid=5)` reads `blob.get("poc_migration").direction`,
   so it returns `None` until that field is added.

These are not RCA-2's blocker for the filter (S1/S2/S5 stay `neutral`,
which is fine for `All systems agree`), but they're why confluence
"agree" never reaches **strong** confluence (3+ systems explicitly
agreeing). Worth fixing right after RCA-1 but lower priority.

### Where to patch each (audit first, do not edit yet)

| System | File to inspect | What to verify |
|--------|-----------------|----------------|
| S1     | `backend/v9/systems/layer0/` + the gateway adapter that writes `day_type_machine` to registry | The publisher exists; check it actually writes `{day_type, state, probability, directional_certainty}` at fire-time |
| S2     | `backend/v9/systems/five_min/setup_wrapper.py` + `wrappers.py` | The wrapper should expose `mode`, `last_classification`, `last_pattern` to the registry |
| S5     | `backend/v9/systems/tpo/...` + the registry push | Add `poc_migration: {direction, distance_pts}` to the snapshot payload |

In each case the rule is **diagnose with a probe before touching code**
(per `.cursor/rules/mems26-pre-live-protocol.mdc`):
1. Find the publisher in the wrapper/system module.
2. Run a one-shot probe to confirm the system has the data locally.
3. Confirm only the registry write is missing.
4. Only then patch.

## Frontend follow-up (optional, low priority)

`frontend/v9/src/v9/lib/tradeAuxStatus.ts::classifyConfluence` currently
returns `'agree'` only when at least one system explicitly agrees AND no
system disagrees. Once RCA-1 is fixed and RCA-2 is partially landed, this
will surface enough trades that we may want a stronger bucket:

- `strong` — ≥ 3 explicit `agree`, no `disagree`
- `agree` — ≥ 1 explicit `agree`, no `disagree`
- `mixed` — at least one `agree` and one `disagree`
- `disagree` — ≥ 1 `disagree`, no `agree`
- `neutral` — all `null`

This would let Michael filter `Confluence ≥ strong` to see only the
genuine 3-of-4-firing-systems-aligned trades. **Do not implement until
RCA-1 + RCA-2 are landed and we see what the real distribution looks
like.** Otherwise we'll be reading noise.

## Acceptance test (mandatory before declaring fixed)

After RCA-1 ships:

1. Run the same DB diagnostic from this report. Expect:
   - S6 `agree` ≥ 100
   - S6 `disagree` ≤ ~120
   - Split correlates with direction (LONG dominates `low edge`,
     SHORT dominates `high edge`).
2. On `/trades`, `All systems agree` should return between **40 and 150
   trades**, not 3.
3. Add a regression test under `tests/v9/services/test_trade_context.py`:
   - Given a Killzone blob with `edge=low`, a LONG trade returns
     `agree=True`, a SHORT trade returns `agree=False`. Mirror for `high`.

If 1 + 3 pass but 2 still returns ≤ 10, that points to RCA-2 being the
remaining gate — escalate to fixing S1/S2/S5 publishers next.

## Why this matters before LIVE

The systems_agreement field is also displayed in:
- `ActiveTradeCard.tsx` (cockpit)
- `TradesTable.tsx` Systems column (`S1·S2·S3✓S4*✓S5·S6✗`)
- `TradeDetailsModal.tsx` recognition panel
- Any LIVE-time veto logic that consults this field

A direction-blind S6 means **every cockpit display shows the wrong
agreement** for the killzone observer right now, and any future LIVE
veto built on top of `agree=False` would block half the legit fades. The
fix has to land before LIVE.

## Estimated work

- RCA-1 patch + regression test: **30–45 min** by CC. Minimum-correct,
  surgical, with the existing test infra under
  `tests/v9/services/test_trade_context*.py`.
- RCA-2 investigation (S1 publisher): **1–2 hours** including the probe
  step. Separate prompt.
- RCA-2 patches (S1/S2/S5): scope-dependent, likely **1–3 hours each**,
  one prompt per system.

Do not bundle. One thread, one P-ID, one report.
