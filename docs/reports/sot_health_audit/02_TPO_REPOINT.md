# SOT_HEALTH Audit — 02 — TPO source (sessions vs history)
Run: 2026-05-29 13:00 IL · 06:00 ET · market: OFF-HOURS (Globex overnight)
Verdict: FALSE-ALARM

## What was checked
Whether `sot_health.py`'s 🔴 on `v9_tpo_sessions.opened_ts` is a real alert or a false alarm caused by monitoring a legacy table. Traced the canonical data path for S5 (TPO) through code, DB, snapshotter logs, and the `/key_levels` API.

## Evidence

### Code (tpo_routes._load_tpo_periods)
`tpo_routes.py:189-204` — `_load_tpo_periods()`:
- Line 200: **prefers** `v9_tpo_history` (B1 snapshotter path)
- Line 204: **falls back** to `v9_tpo_sessions` only when history is empty
- Docstring (line 192): *"Prefers v9_tpo_history (per-30-min snapshots from TPOHistorySnapshotter — Sierra Study ID:3 fidelity). Falls back to the legacy daily v9_tpo_sessions."*

`key_levels_routes.py:28` — uses `_load_sierra_tpo()` (direct DLL read from `tpo.json`), does NOT read from either DB table.

### DB — v9_tpo_history vs v9_tpo_sessions

| Table | ts_col | Count | Last row | Age | Status |
|-------|--------|-------|----------|-----|--------|
| `v9_tpo_history` | `ts` (DATETIME) | 50 | `2026-05-28 19:30:00 UTC` (= 15:30 ET) | 11.6h | **LIVE** — last RTH snapshot from yesterday, legitimate off-hours gap |
| `v9_tpo_sessions` | `opened_ts` (DATETIME) | 28 | `2026-04-29 14:30:00 UTC` | **30 days** | **LEGACY** — last written April 29, not updated since B1 rollout |

`v9_tpo_history` schema: `id, ts, poc, vah, val, ib_high, ib_low, profile_shape, poc_migration_direction, created_at`

Sample last 2 rows:
```
id=92 | ts=2026-05-28 19:30:00 | poc=7581.75 | vah=7583.0 | val=7557.0
id=91 | ts=2026-05-28 19:00:00 | poc=7576.5  | vah=7583.0 | val=7556.0
```

### Snapshotter (log lines)

```
[tpo_snapshotter] task started — tpo.json=~/SierraChart_Data/v9_export/tpo.json db=data/mems26_local.db interval=30min
2026-05-29 10:00:05 [INFO] [tpo_snapshotter] boundary snapshot: {'skipped': 'not_rth', 'reason': 'boundary', 'et': '2026-05-29T03:00:05-04:00'}
```

Snapshotter is **running** and correctly **skipping** off-hours boundaries. Wired in `main.py:464-472`.

### /key_levels (http + sample + source table)

```
HTTP 200
today.poc: 7586.0
today.vah: 7592.75
today.val: 7579.5
today.ib_high: None
today.ib_low: None
```

Source: `_load_sierra_tpo()` → reads directly from `tpo.json` (DLL export). Does NOT read from `v9_tpo_sessions` or `v9_tpo_history`. IB is None because Sierra `ib.found=false` (post-lock behavior — IB study writes 0 to JSON after the lock window).

## Finding

**`sot_health.py`'s 🔴 on `v9_tpo_sessions` is a FALSE ALARM.**

- `v9_tpo_sessions` is **legacy** — last written 2026-04-29 (30 days ago). It was replaced by the B1 snapshotter (`v9_tpo_history`) as part of P31.
- `v9_tpo_history` is the **canonical** per-30-min snapshot table. It has 50 rows, last from yesterday's RTH (2026-05-28 19:30 UTC = 15:30 ET). This is correct — no RTH has occurred yet today.
- `/key_levels` reads from **Sierra DLL export directly** (`tpo.json`), not from either DB table. The DB tables are for historical replay/charting, not for live key levels.
- The `--strict` mode would fail every morning on `v9_tpo_sessions` because that table is permanently stale. This is a monitoring config error, not a data error.

### Off-hours behavior
`v9_tpo_history` will be empty/stale until the first 30-min RTH boundary (~09:30 ET = 13:30 UTC). The snapshotter correctly skips off-hours (`'skipped': 'not_rth'`). This means **any freshness check on `v9_tpo_history` will show 🔴 before ~13:30 UTC daily**. The script needs an "empty-until-first-boundary" rule for TPO.

## Recommendation (for Cursor/Michael — DO NOT execute)

1. **Repoint** `sot_health.py` S5/TPO check from `v9_tpo_sessions.opened_ts` to `v9_tpo_history.ts`
2. **Add off-hours rule**: if current time < 09:30 ET, treat `v9_tpo_history` stale/empty as 🟡 (expected) not 🔴
3. **Demote** `v9_tpo_sessions` to informational-only in the health check (or remove entirely — it's a 30-day-dead legacy table)
4. **Do NOT** add `/key_levels` as a freshness source — it reads from DLL file, not DB; its freshness is the DLL mtime, already covered by the Sierra JSON health check

Proposed tuple for `sot_health.py`:
```python
("S5_tpo_history", "v9_tpo_history", "ts"),  # replaces v9_tpo_sessions
```

With off-hours guard:
```python
if system == "S5_tpo_history" and not is_rth_now():
    status = "🟡 OFF-HOURS (expected)"
```

## Open questions

1. **Should `v9_tpo_sessions` be dropped entirely?** It's used as a fallback in `_load_previous_cash_session()` (line 236-252 of `tpo_routes.py`) for yesterday's POC/VAH/VAL reference lines. If the DLL `previous_session` block is reliable, this fallback can be removed.

2. **50 rows in `v9_tpo_history`** — is that the expected count? At 2 snapshots/hour × 6.5h RTH = ~13/day. 50 rows ≈ 4 days. If the table is never pruned, it will grow indefinitely. Consider an archival policy.

3. **`v9_tpo_history` has no `trading_date` column** — the `ts` column carries the snapshot timestamp. Filtering by trading day requires `WHERE date(ts) = ?`. Adding a `trading_date` column (like `v9_tpo_sessions` has) would simplify queries.
