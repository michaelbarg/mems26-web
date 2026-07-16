# N3 — ZONE_LIMIT_ENTRY_V1 spec (design only, NOT implemented)

**Status:** NOT-DONE by design. Written instead of a rushed implementation — this changes
*when/where a trade enters*, a trading-risk surface, and the NIGHT_PROMPT's own contract requires
a full sim cycle (place→fill→ladder→FLATTEN→back-to-live) before any live effect, which is
impossible from the cowork-dev sandbox (no live backend/Sierra reachability — verified this
session, see AGENT_SYNC 22:32). Rather than half-wire it under time pressure, this doc is the
handoff spec for cc-imac (who has the live Sierra/gateway access to build, sim-test, and prove it)
or for tomorrow's session with more runway.

## Ask (verbatim, NIGHT_PROMPT_2026-07-17 §N3)
On rotation days, at identified value-edge zones (TARGET_ZONES), place a resting limit order in
the zone instead of waiting for a confirm-bar entry trigger; cancel if the zone is broken-and-accepted.
T0/ladder/structural-stop unchanged. Flag default OFF.

## What already exists (reusable, KEEP)
- `backend/v9/systems/target_zones.py` — confluence-zone clustering (`cluster_levels`,
  `select_target_zones`, `Zone.near_edge(direction)`) is currently used for C2/C3 *targets* beyond
  T1. The same `Zone`/clustering machinery is the right building block for an *entry* zone too —
  do not build a second clustering implementation.
- `backend/v9/systems/day_type/level_acceptance` (relative_features.py) already implements the
  "accepted break" test (>=2 closed bars beyond + volume-accept) used elsewhere for reference-level
  acceptance — this is the correct primitive for "zone broken-and-accepted → cancel", not a new
  ad-hoc check.
- `TradingGateway._execute_live`/`_execute_demo` (trading_gateway.py:1742-1913) build the
  Sierra command via `command_from_setup(setup, ...)` and pass `setup["entry_price"]` through
  unmodified. A zone-limit entry only needs to change what `entry_price` (and an order-type/limit
  flag) IS, computed *before* this call — it should not need new code inside `_execute_live` itself.

## Proposed shape (for whoever builds it)
1. **Rotation-day gate**: only apply when `day_type` is a rotation-family label (Normal/Variation/
   Neutral, i.e. NOT Trend_*) — reuse the exact day-type string set already used elsewhere for the
   RR-relief / playbook rotation-day checks (see `_rr_unclassified_relief_window` callers in
   `trading_gateway.py` for the existing "which labels count as rotation" convention — stay
   consistent with it rather than inventing a second list).
2. **Zone selection**: build `Zone`s from the same level set `target_zones.py` already clusters
   (IB high/low, POC, VAH/VAL, prior-day H/L/POC/VA, session extremes) via `cluster_levels`; pick
   the nearest zone in the trade's direction that is *between* the current price and where the
   confirm-bar trigger would normally fire (the entry zone must be reached before, not after, the
   existing trigger — otherwise this just delays entries).
3. **Resting limit price** = the zone's near edge (`Zone.near_edge(direction)`), grid-snapped —
   mirrors `select_target_zones`'s own snapping.
4. **Cancel condition**: reuse `level_acceptance(bars, zone_edge, side)` — if the zone's far edge
   is accepted-broken (2 closed bars + volume) before fill, cancel the resting order (the setup
   evaporated; this is not a dip to buy, it's a breakout to not fight).
5. **Everything downstream unchanged**: T0/ladder/structural-stop keep reading `setup["entry_price"]`
   as today — a filled zone-limit entry should be indistinguishable from a confirm-bar entry to
   every consumer past this point.
6. **New op needed?** Check with cc-imac whether Sierra's DLL already exposes a generic limit-order
   PLACE (vs. today's market/stop-confirm PLACE) — do NOT invent a new `op=` string without
   confirming the DLL side can honor it. If it can't yet, this needs an sc_study change first
   (cc-imac's DLL-ops lane per CLAUDE.md), not a backend-only flag.

## Explicit NOT-DONE
- No code written. No flag exists yet (`ZONE_LIMIT_ENTRY_V1` is not defined anywhere).
- No sim-cycle proof (needs live Sierra + `debug_gateway_fire`, sandbox can't reach either).
- No DLL-side capability check (needs cc-imac to confirm the limit-order PLACE path exists).

## Suggested next step
cc-imac (or next session with live access): confirm the DLL PLACE-limit capability first (5 min
check), then build steps 1-5 above as a pure decision module (`backend/v9/systems/zone_limit_entry.py`,
mirroring `target_zones.py`'s style) + unit tests, wire ONE call site in the gateway setup-building
path (before `_execute_live`/`_execute_demo`), then run the sim cycle. Flag stays OFF until Michael
signs off on the sim evidence.
