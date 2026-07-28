# CC — System-6 AUTO-STOP on unprotected positions (Michael ruling 2026-07-28)

## The ruling (verbatim)

> "לגבי מערכת 6 אני רוצה שהיא תמצא עסקאות פתוחות ותחפש מבנה קרוב להציב עליו סטופ
> אוטומטי ללא אישור"

**Standing** per CLAUDE.md § "Rulings are one-time and standing". Build → verify
(tests + SIM) → **enable without asking again**. Record the pointer in
`config/RULED_FLAGS.yaml` in the same commit.

### What changed vs. the previous ruling
2026-07-25 ruled the manual-position guard **alert-only** ("התראה-בלבד"), and the
12:20 ownership ruling said never touch Michael's manual position. On 07-27 that
combination cost more than half the account: the alerts fired 12 times into a log
nobody could see, and nothing placed a stop.

**This ruling supersedes the alert-only limitation for the NAKED case only.**
- position with **no protective stop** → S6 **places** a structural stop, no approval.
- position **with** a stop → untouched, forever. Never modify, never tighten,
  never cancel. (12:20 ownership ruling stands in full.)

---

## Blocker first: there is no working "place a stop" op

`op=EXIT` is broken and forbidden (CLAUDE.md). The current auto-protect
(`MANUAL_GUARD_AUTOPROTECT_V1`) places a **virtual** stop: the backend watches
price and sends `FLATTEN_ACCOUNT` on breach. That is better than nothing but it
dies with the backend and does nothing overnight or on a gap.

**W8 must land first** — the DLL op Michael already ruled on 07-25:

```
op=PLACE_STOP  qty=<n>  price=<p>  side=<BUY|SELL>
  → sc.BuyExit / sc.SellExit with OrderType = SCT_ORDERTYPE_STOP,
    OrderQuantity = n, Price1 = p, and o.TradeAccount = sc.SelectedTradeAccount
    (the 07-27 root cause of every r=-1: the account was hard-coded).
  → write trade_result.json {status:"PLACE_STOP_OK"|"PLACE_STOP_FAIL", r:<code>}
```
This is a **real resting stop on Sierra's book** — survives a backend crash,
protects against gaps, visible in `orders[]` so `_has_protective_stop` sees it.

Deploy note (found 07-28): `sc_study/MES_AI_DataExport_merged.cpp` is now the
**hand-maintained** DLL source — the modular files are 6 days stale and the
generator would delete every fix. The script now refuses to regenerate; edit the
monolith. `--deploy` works again (two `set -e` landmines fixed).

---

## The structure engine (the actual ask)

"מבנה קרוב" — the nearest *structural* level, not a fixed distance. Order of
preference, first that qualifies wins:

| # | Level | Condition |
|---|-------|-----------|
| 1 | swing low/high of the 5-min structure | most recent confirmed swing beyond entry side |
| 2 | prior-bar extreme | when the swing is further than `S6_AUTOSTOP_MAX_PTS` |
| 3 | session extreme (IB low/high, day low/high) | when inside the IB |
| 4 | ATR fallback | `1.0 × ATR(14)` when no structure qualifies |

Constraints — all mandatory:
- **buffer**: `S6_AUTOSTOP_BUFFER_TICKS` (default 4) beyond the level, never at it.
- **min distance**: ≥ 6 ticks from last price (a stop inside the spread is an
  instant market order).
- **max risk**: reject any candidate whose `qty × distance × $1.25` exceeds
  `S6_AUTOSTOP_MAX_RISK_USD` (default 250) → fall back down the table; if nothing
  qualifies, place at the max-risk distance and log `CLAMPED_TO_RISK_CAP`.
- **sanity**: long → stop strictly BELOW last price; short → strictly ABOVE.
  Wrong side = reject and alert, never send.
- Reuse the existing level source (`StopResolver` / bar structure); do **not**
  build a second level engine — audit first per CLAUDE.md.

## Wiring

`system6_supervisor.diagnose_trade` already has the AUTO/ALERT split. Add
`NAKED_POSITION` → AUTO tier, emitting `PLACE_STOP` (never `EXIT`).

Trigger: `sierra_position_reconciler` naked detection (`_has_protective_stop` is
False) after `S6_AUTOSTOP_GRACE_S` (default 45 — long enough for a bracket to
register, short enough to matter). `None` (unknown) → **no action**, alert only
(Rule 1: never place on a guess).

Applies to **both** system and manual positions. Ownership only decides the log
line, not whether we protect.

Idempotency: one stop per position episode. Track `(qty, avg_price)`; a
`PLACE_STOP_OK` for that episode blocks any further placement. If the stop is
cancelled manually and the position goes naked again → new episode, place again,
but cap at `S6_AUTOSTOP_MAX_PER_EPISODE` (default 3) to prevent a loop against
Michael cancelling on purpose.

## Flags

| flag | default | meaning |
|------|---------|---------|
| `S6_AUTOSTOP_V1` | **1 after sim-verify** (ruled) | master |
| `S6_AUTOSTOP_GRACE_S` | 45 | naked seconds before placing |
| `S6_AUTOSTOP_BUFFER_TICKS` | 4 | beyond the structural level |
| `S6_AUTOSTOP_MAX_RISK_USD` | 250 | hard risk cap per position |
| `S6_AUTOSTOP_MAX_PER_EPISODE` | 3 | anti-loop |

## Tests (all required before enabling)

1. long naked → stop below the swing low − buffer
2. short naked → stop above the swing high + buffer
3. protected position → **zero** calls (the 12:20 ruling, pinned)
4. `_has_protective_stop` returns None → no placement, alert only
5. structure further than max risk → clamped, `CLAMPED_TO_RISK_CAP` logged
6. computed stop on the wrong side of price → rejected, never sent
7. within grace → nothing; past grace → exactly one placement
8. `PLACE_STOP_OK` → no second placement for the same episode
9. new episode after cancel → places again; 4th time → blocked by cap
10. flag off → byte-identical no-op
11. **never emits `op=EXIT`** — source-level assertion
12. anti-mock: no fixture may inject a symbol the module does not define
    (the `_t` NameError class — tests passed while the code failed every poll)

## Verification (Rule 5 — paste command + raw output)

SIM, live-fire: open a naked position in Sim → confirm within ~45s a **real stop
order appears in `sierra_state.json.orders[]`** with the right side/qty, at the
structural level, and `_has_protective_stop` flips to True. Paste the raw
`orders[]` before and after. A green test suite is **not** sufficient evidence
for this one — it is exactly the path that failed on 07-27.
