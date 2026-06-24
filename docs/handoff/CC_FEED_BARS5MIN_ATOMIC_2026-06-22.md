# CC Handoff — Fix v9_bars_5min feed gaps (read-while-write) · 2026-06-22

**Owner:** Cowork (diagnosis) → CC (infra fix). **Risk:** market-data / bridge / Sierra — read
`docs/runbooks/SIERRA_DLL_OPS.md` + CLAUDE.md §Sierra DLL + §Bridge before touching. **Blocker-LIVE #0.**

## Root cause (diagnosed 2026-06-22, raw evidence)
`v9_bars_5min` gapped 09:00–09:35 CT today (and 06-19 ~12:00) → blinded the direction strip + the
day-type classifier (both read it). Bridge log shows the cause:
```
[bars_5min] Read error: Expecting property name enclosed in double quotes: line 1 column 75740 (char 75739)
```
The Sierra `bars_5min` JSON export is a **single ~75KB line**. The bridge polls and **reads it
mid-write** → a truncated/half-written JSON → `JSONDecodeError` → the read is skipped → no push →
a **gap** in `v9_bars_5min`. ~94 such read-errors today. `woodies_5min` is far less affected (smaller /
more atomic export) — which is why it stayed live while `v9_bars_5min` gapped. This is a classic
read-while-write race, not a Sierra-down event.

## Fix — 3 layers (root → robustness → safety)
1. **ROOT — atomic export (sc_study/ Sierra DLL).** Write the bars_5min JSON to a temp path
   (`<file>.json.tmp`) and `rename()` it onto the final path (atomic on the same filesystem). The
   bridge then can never read a partial file. Apply to every large single-line export (bars_5min first;
   audit the others). Deploy per `docs/runbooks/SIERRA_DLL_OPS.md` (sc_study → build → Remote Build → reload).
2. **ROBUSTNESS — bridge (`bridge/v9_streams/bars_5min_stream.py`).** On `JSONDecodeError`: retry the
   read 2–3× with ~50ms backoff (the write finishes in ms); if still malformed, **hold the last-good
   payload** (do NOT push, do NOT advance) and log a **rate-limited WARNING** (not silent/`debug` —
   per CLAUDE.md "no silent failures"). Never write a partial/garbled bar.
3. **WATCHDOG — stream-death detection (Blocker-LIVE #0 / D22).** If a critical stream's
   `last_push_age` exceeds a threshold during RTH (e.g. bars_5min > 90s), set `readiness=DEGRADED`
   with the dead stream named, surface it on the dashboard, and **gate LIVE** on it (no LIVE with a
   silently-dead feed — the 06-19 lesson).

## Verify (Rule 5)
- One full RTH with **0 gaps** in `v9_bars_5min` (every 5-min bar present, contiguous) and **0**
  parse-error-induced skips (or all recovered by the retry). Paste the gap-check query + output.
- Watchdog: simulate a stall → `readiness=DEGRADED "dead: bars_5min"` within the threshold.

## Note for the trading gates
Consumers `direction_context_live` + the strip endpoint **already fall back to the contiguous
`v9_bars_5min_woodies`** when 5min is stale (Cowork 2026-06-22) — so the DISPLAY is protected. BUT
`DIRECTION_CONTEXT` needs **CVD (`cumulative_delta`), which ONLY `v9_bars_5min` carries** — woodies
has none. So this feed fix is a **prerequisite for enabling the direction gate** (#5 in the enable
plan): without contiguous 5min, the CVD slope misreads (today's strip "inside value / CVD +1" bug).

## NOT-DONE / scope
Do not touch trading logic or the other streams' semantics. Atomic-write is the root fix; the bridge
retry + watchdog are defense-in-depth. Enabling/deploying Sierra changes = Michael sign-off (market-data surface).
