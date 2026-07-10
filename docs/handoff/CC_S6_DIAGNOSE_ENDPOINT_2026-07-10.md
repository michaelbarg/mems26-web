# CC handoff — `GET /api/v9/s6/diagnose/{trade_id}` (System-6 live view on the trade card)

**Date:** 2026-07-10 · **From:** Cowork (frontend) · **Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md`
**Context:** `docs/handoff/PROMPT_SYSTEMS_TRADE_UX_2026-07-10.md` §4 — Michael's ruling
"שמערכת 6 תהיה שם ורואים מה היא חושבת" (System-6 visible on the active-trade card).

## Why
The frontend now renders a live **"מערכת 6 — פיקוח"** block on the active-trade card
(`ActiveTradeCard.tsx` → `System6Block`, polls every 15s). It is **already shipped and
degrades gracefully**: when the endpoint 404s it shows
*"ממתין ל-endpoint מ-CC: GET /api/v9/s6/diagnose/{trade_id}"*. No frontend change is
needed when you ship the route — the block lights up automatically.

## What to build
`GET /api/v9/s6/diagnose/{trade_id}` → run `diagnose_trade()` on the OPEN trade and return
its checks. Source of truth: `backend/v9/systems/system6_supervisor.py:69 diagnose_trade(...)`
returning `SupervisorReport{ ok, issues[], reconcile_verdict }`, `Issue{ key, severity
(INFO|WARN|CRITICAL), action (AUTO|ALERT), detail }`.

The route must gather the live inputs `diagnose_trade` needs (it does NOT fetch them itself):
`trade` dict (direction, entry_price, stop, t1/t2/t3, contracts), `atr`, `t1_hit`,
`reconcile_verdict`/`reconcile_mismatch` (from the item-20 reconciler), `expected_contracts`
(FIXED_CONTRACTS_2 → 2 today), `now_ct_min`. Pull the open trade from
`app.state` / `v9_trades` the same way the active-trade route does
(`backend/v9/api/v9/trades.py` active handler).

### Response shape (frontend accepts either)
The block reads an **array** OR `{ checks:[...], ruling }`. Each check:
`{ name|key: str, ok|pass: bool  (or status:"PASS"/"FAIL"), severity?: str, detail?: str }`.

```jsonc
// Preferred — all 9 invariants with pass/fail so the trader sees ✓ and ✗:
{
  "trade_id": 350,
  "ruling": "healthy — stop at BE, sizing ok",     // shown as "שיפוט: …"
  "checks": [
    { "key": "stop_wrong_side", "name": "Stop on correct side", "ok": true },
    { "key": "naked_stop",      "name": "Stop is live at broker", "ok": true },
    { "key": "stop_not_at_be",  "name": "Stop at BE after T1",   "ok": false,
      "severity": "WARN", "detail": "T1 hit 3m ago, stop still 7604.00" }
    // … all invariants: stop_wrong_side, naked_stop, stop_too_tight, stop_too_wide,
    //    stop_not_at_be, t1_too_close, contract_mismatch, reconcile_mismatch, eod_open_position
  ]
}
```

> ⚠ `diagnose_trade()` today returns **only failing** issues (an empty list = healthy). If you
> return the raw `issues[]`, the card will show every listed item as ✗ (never ✓). Michael asked
> to *see the 9 invariants with ✓/✗* — so emit the **full set** (passing checks as `ok:true`),
> not just the failures. Simplest: keep a static list of the 9 invariant keys, mark those present
> in `issues` as failed, the rest as passed.

- **404** when there is no open trade (the block already handles this = "ממתין ל-endpoint").
- **Read-only.** Do NOT trigger AUTOCORRECT from this GET — diagnosis only.

## NOT needed (verified — do not build)
Prompt §3 mentioned a possible `GET /api/v9/trades/{id}/timeline`. **Not required** — the
detail drawer already builds the full timeline (ENTRY · every STOP_MOVE `from→to (reason)` ·
T-hits · EXIT) from the existing `fetchTradeById` `management_log`. Verified in-browser 07-10.

## Verify (Pre-LIVE Rule 5 — paste raw output)
`curl -s localhost:8000/api/v9/s6/diagnose/<open_trade_id> | jq` → array/`checks` with ≥1
item; card block flips from the waiting-note to ✓/✗ rows within 15s.
