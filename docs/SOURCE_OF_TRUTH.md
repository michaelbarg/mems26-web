# MEMS26 — Source-of-Truth Map

Per `CLAUDE.md` § *Source-of-Truth Discipline* + § *Codebase Index Protocol*.

`SYSTEM_INDEX.md` (auto-generated) maps **WHERE code is**. This map (hand-maintained) maps
**WHICH data source is the canonical LIVE truth** for each signal — the layer the index can't
capture, and exactly the gap that caused 2026-06-22's stale-table + two-classifier confusion.
**Consult this BEFORE querying or wiring any signal.** Verify a "found" source's last row is
actually recent before trusting it (Rule 2).

## 5-minute bars (OHLC / CVD)
| use | source | notes |
|---|---|---|
| ✅ live OHLC + trend_state | `v9_bars_5min_woodies` | contiguous, live (Woodies study stream); has `trend_state`/`zlr_detected`/`hfe_detected`; **no** `cumulative_delta` |
| ✅ OHLC **+ bar delta** | `v9_bars_5min` (`cumulative_delta` column — **misnomer**: holds PER-BAR delta, not a running cumulative; ingested from `5min_continuous.json` `delta` field) | **can STALL / GAP** (2026-06-22 stuck 08:55; gap 09:00–09:35) — always check the last bar is recent. `cvd_slope` uses `sign(Σ delta over N bars)`. |
| ✅ live price (tick) | `GET /api/v9/live_price` | ~1s fresh (bid / ask / last) |
| 🔴 **AVOID for price** | `v9_bars_5min_continuous` | `close` is GARBAGE (e.g. 12693/13456 — not a real price); **excluded from `/api/v9/chart/bars5min`** (2026-06-24). 3 corrupt rows deleted. Orphan model — do not wire new consumers. |

Helper that already does the right thing: `direction_context_live._fetch_live_bars` — prefers
`v9_bars_5min` for CVD, falls back to the contiguous `v9_bars_5min_woodies` when 5min is stale/gapped.

## Day-type
| use | source | notes |
|---|---|---|
| ✅ **canonical 7-type** (Michael-validated 11/11) | `GET /api/v9/day_type/classify_replay?date=` · `classifier_core.classify_session(...)` | the authority. Build-Status, the strip, and the pills all read this. |
| 🟡 live-engine (OLD 3-type) | `app.state.day_type_machine` · `cockpit/systems-snapshot` sys-1 · `v9_day_type_state` | only Trend_Normal/Variation/Normal **until `S1_ENGINE_NEW_CLASSIFIER` (part-b) is live** |
| ✅ direction now | `GET /api/v9/day_type/direction_now` → `direction_context_live.current()` | UP/DOWN/NEUTRAL + `day_type` + `source`. When `DIRECTION_LSMA_VETO=1`, direction = LSMA-lead + CVD-veto (source = `v9_bars_5min_woodies` lsma_value + cvd_slope); flag OFF = CVD+breakout engine. |
| 🔴 **DEAD — do not re-wire** | `/api/v9/day_type/v9/current` (returns None) · `/api/v9/day_type/current` (V1 wrapper) | retired from the frontend 2026-06-22 |

## TPO levels (IB / VAH / POC / VAL)
| ✅ | `v9_tpo_sessions` WHERE `session_type='CASH'` ORDER BY id DESC LIMIT 1 | **`trading_date` is VARCHAR** — pass an ISO **string** (`.isoformat()`), not a `date` object, or the query errors. IB = first hour (08:30–09:30 CT). |

## Trades / setups
| use | source | notes |
|---|---|---|
| ✅ trades | `v9_trades` | entry/exit/pnl/`day_type_at_entry`/`pattern_id_at_entry`; management timeline in `v9_trade_management_log` (`action`,`value`) |
| ✅ S2 setups | `v9_five_min_setups` | |
| ✅ S4 pattern triggers | `v9_bars_5min_woodies` (`zlr_detected`,`hfe_detected` = 0/1) | |

## Trading-surface flags → see `docs/FLAG_INDEX.md` (canonical, generated)
This list used to be hand-maintained here and **drifted** — it listed 4 flags as OFF that were
actually ON (`OPENING_TYPE_GATE`, `NONTREND_WIDTH_FLOOR`, `DEDUP_FIRE_GUARD`,
`S1_ENGINE_NEW_CLASSIFIER`, flipped 06-22 evening). The canonical flag state is now **generated**
from the live code + `.env`: **`docs/FLAG_INDEX.md`** (regenerate with
`python3 scripts/gen_flag_index.py`; semantics in `docs/FLAG_REGISTRY.yaml`). Consult that for any
flag's ON/OFF — never this prose or memory (Rule 2).

## Timezone
Timestamps are stored at **+03:00**; convert to trading-time with `(ts AT TIME ZONE 'America/Chicago')`.
RTH = 08:30–15:00 CT. Keep this in mind for every `WHERE`/`date` filter.

---
*Maintained by hand — update when a data source's role changes (new table, a source goes stale/legacy,
a flag flips). Last updated 2026-06-24.*
