# P30.10b — TPO POC / VAH / VAL position & values fix

**Date:** 2026-05-19 · **L0 sign-off:** 2026-05-20 (Michael, inbox #9 + G4 round 2)  
**Status:** CODE GREEN — **Sierra `tpo.json` must be fresh** (&lt;30s) for live parity. **No further frontend POC/TPO edits** unless Michael reopens.

---

## Root cause (Michael screenshot vs Cockpit)

| Issue | Cause |
|-------|--------|
| Wrong **prices** (POC≈VAH≈VAL ~7392) | `tpo.json` stale → API fell back to **in-memory TPOSystem** with collapsed value area |
| Wrong **horizontal position** | Session `opened_ts` from DB was normalized as UTC; chart bars use `YYYY-MM-DD HH:MM:SS` wall time |
| White **prior** lines wrong | `previous_day` endpoint used wrong DB row; now `previous_session` on `/tpo/current` (DB CASH interim) |

Sierra reference (your screenshot):

- **White:** TPO VAH 7428.50, POC 7411.25, VAL 7390.75 (prior completed profile)
- **Magenta stepped:** developing session ~7373 / 7382 / 7356
- **Green/cyan IB:** 7378.75 / 7366.25 / 7353.75

---

## Fixes shipped

1. **`tpo_routes.py`** — Always serve Sierra export when file exists; `stale: true` if age &gt; 30s; **no TPOSystem fallback**.
2. **`session_va_ok`** — Suppress bogus full-width lines when VA collapsed.
3. **`previous_session`** on `/api/v9/tpo/current` (optional Sierra `previous_session` block; else last CASH DB row).
4. **ET wall-clock** for period `opened_ts` / `closed_ts` from unix DB rows.
5. **`SierraLevelsOverlay.tsx`** — White lines use `previous_session` X-range when timestamps present; IB when `ib_found`; no duplicate full-width magenta when `periods[]` exist.
6. **`ChartV5b.tsx`** — Single `/tpo/current` fetch (includes `previous_session`).

---

## Verify

```bash
curl -s http://127.0.0.1:8000/api/v9/tpo/current | jq '{source,stale,poc,vah,val,session_va_ok,ib_high,previous_session}'
bash scripts/uat_woodies_live_tick.sh 5 3   # unrelated but confirms backend up
```

**Expect (stale export example):** `source=sierra_tpo_json`, `poc≈7370`, `vah≈7391`, `val≈7358`, `session_va_ok=true`.

**Sierra:** ensure study export writes `tpo.json` every few seconds. Stale file shows `stale: true` in API — refresh Sierra export.

---

## Still needed (DLL / Agent 2)

Export on `tpo.json`:

```json
"previous_session": {
  "found": true,
  "poc": 7411.25,
  "vah": 7428.50,
  "val": 7390.75,
  "opened_ts": "...",
  "closed_ts": "..."
}
```

Until then white lines use last **CASH** row from DB (may not match Sierra pixel-perfect).

Native `periods[]` in `tpo.json` (replace DB interim for stepped magenta).

---

## Tests

`pytest tests/v9/api/test_tpo_routes_sierra_contract.py -q` → 4 passed
