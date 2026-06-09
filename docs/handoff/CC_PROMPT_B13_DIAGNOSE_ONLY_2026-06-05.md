# CC Prompt — B-13 DIAGNOSE-ONLY: why S2 fired phantom trades after hours

**Michael's directive: NO fix, NO guardrail, NO patch. Investigation only.**
Produce evidence that explains WHY, paste raw output (Rule 5). Do not touch
trading logic, risk values, sc_study, or any system code. Read/query only.

## What we already proved from the Cowork side (code + live API)
- Live market now **7554.62** (`/api/v9/live_price`). Real range 28/5–4/6 ≈ 7548–7630.
- S2 (five_min, firing_system=2) fired 2 shadow trades:
  - id 9: SHORT `DOUBLE_TOP_AA_SHORT` entry **7365.75**, entry_ts `2026-06-05T00:20:30+03:00` (= **17:20 ET 06-04**, after RTH close 16:00).
  - id 7: SHORT entry **7341.00**, entry_ts `2026-06-05T00:18:36+03:00` (= **17:18 ET**).
  - Both ≈190–225 pts **below** live market → ran on a phantom/corrupt bar.
- `/api/v9/chart/bars5min?limit=600` → 428 RTH bars, **none below 7450**; last RTH bar ts `2026-06-04 22:55:00+03:00` (15:55 ET). The phantom price is NOT in the RTH 5-min table → bar entered via the **live push path**, not hydrate.
- Code root (confirmed): `five_min_system.py` `process_bar` after-hours guard (L782) is gated on `self.mode in {OVERNIGHT,MAINTENANCE,WEEKEND}`. The live transition code (L760–779) only promotes OVERNIGHT→FIRST_HOUR→DAY_TYPE. **There is no DAY_TYPE→OVERNIGHT edge at RTH close.** OVERNIGHT/MAINTENANCE are set ONLY in `hydrate()` at startup (L141/L181). ⇒ once S2 enters DAY_TYPE_MODE intraday it stays armed through the close until restart.

## What we need CC to retrieve from the Mac (DB + logs) — questions, not fixes
1. **The exact bar S2 fired on.** Query the live bar source S2's `process_bar`
   consumed at 17:18–17:20 ET 06-04. For each table that feeds S2's BarRouter,
   paste any row with ts in `2026-06-04 21:00..22:00 UTC` (17:00–18:00 ET) and
   any row anywhere with low/close < 7450:
   - `SELECT ts, open, high, low, close, volume FROM v9_bars_5min WHERE ... ORDER BY ts;`
   - same for `v9_bars_5min_continuous`, `v9_bars_5min_woodies`, and any tick/
     live-price table the BarRouter publishes from. Paste raw rows.
2. **Where the 7341/7365 value originated.** Grep the bridge + S2 logs for that
   window: `grep -nE "17:1[89]|21:1[89]:" /tmp/bridge.err.log` and the backend
   log around those entry_ts; paste any bar payload showing 7341/7365 and its
   `source`/stream. Was it a Sierra glitch bar, a stale row, a unit/typo, or a
   synthesized value? Heartbeat showed errors=2–3 near a restart — correlate.
3. **S2 mode at fire time.** Confirm from logs what `self.mode` was at 17:18 ET
   (expect DAY_TYPE_MODE). Paste the last mode-transition log line before the fire.
4. **Reconcile the systems.** Michael reports systems **6, 1, 2** fired "contrary
   to their action." The trades API shows fires only from firing_system **2
   (five_min), 3 (footprint), 4 (woodies)** — none from 1 (day_type) or 6
   (killzone). Paste any S1/S6 fire/emit records (or confirm none exist) so we
   reconcile what Michael saw vs. what's persisted.

## Deliverable
A short evidence dump (raw rows + raw log lines) answering 1–4. **No code edits,
no test, no guardrail.** Michael decides remediation only after he sees the
phantom bar's origin. Per CLAUDE.md: diagnose first, fix second.
