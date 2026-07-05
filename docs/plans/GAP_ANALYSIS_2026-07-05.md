# Gap analysis — everything we set out to do vs reality (2026-07-05)

Verified from code/flags/git, not memory.

## ✅ Live in trading (flags ON)
Safety + core: RR_ENTRY_GATE_V1 · FIXED_CONTRACTS_3 · DAYTYPE_TARGETS_STRUCTURAL
(resolver item-2) · item-1 counter-SKIP (playbook) · OPENING_FIRE_CVD_V1 (I-53) ·
RUNNER_TRAIL_V1 · I-57/58/59/60/61/62 fixes.

## 🟡 Built, flag-OFF — ready to ENABLE (your call)
item-10 OPENING_WINDOW_FIRE_V1 (Mon scheduled) · item-19 RISK_HALT_V1 ·
item-18 DAY_DIRECTION_DOCTRINE_V1 + halt-proof · item-21 EOD_RISK_WINDOW_V1 ·
item-5 S2_B4_VOL_V1 · item-9 DBDT alias · System 6 (supervisor+exit+journal,
endpoint live).

## 🔴 Built but NOT WIRED — the biggest gap (latent, doing nothing)
- **item-4 STOP_RESOLVER** — ✅ **NOW WIRED (02a2bf5)** at the gateway single
  choke point (S2+S4), flag-OFF. Ready to enable. (Was the #1 gap.)
- **item-22 TARGET_ZONES** — ✅ **NOW WIRED (7897ebd)**, flag-OFF. Refines t2/t3
  to confluence shelves at the gateway.
- **item-6 S4_ENTRY_CONFIRM** — ✅ **NOW WIRED (7897ebd)**, flag-OFF. Confirm-bar
  gate at the gateway.
- **item-20 reconcile** — wired into the System 6 endpoint, NOT into a periodic
  loop/alert. (Only remaining wiring gap.)

## ❌ NOT built (owed, mostly CC)
- item-11 sizing consolidation — `calculate_size` still in 5 files (two sizing
  systems still run in parallel).
- item-12 TT_SPEC_V2 — 0 files. TT still shallow (0 fires ever).
- item-13 PB_SHAPE_FILTER_V1 — 0 files.
- item-16 VOL_REGIME_V1 — 0 files (you ruled contracts=3, so its contract-override
  is moot, but the wider-stops/entry-confirm-on-volatile part is unbuilt).
- item-17 entry-side "why no trade" journal — not built (System 6's
  v9_exit_decisions covers the EXIT side only).
- item-7 phase detector / item-8 pullback-retest — research/design, not built.

## The one-line big picture
A LOT is built, but **almost nothing that improves profitability is actually
LIVE** — item-4/22/6 are built-and-inert, and item-10/18/19/System 6 are
flag-OFF. So today's DEMO behaviour ≈ the old system + safety fixes. The value
is real but LATENT. Closing the gap = wire item-4/22/6 + enable the proven
pieces + run a clean validation window. LIVE is NOT ready (demo net −0.67R).

## ✅ UPDATE 2026-07-05 ~22:05 (Michael ruling — gap-closing actions taken)
- **item-4/22/6 ENABLED** (`STOP_RESOLVER_V1=1`·`TARGET_ZONES_V1=1`·
  `S4_ENTRY_CONFIRM_V1=1`) for Monday DEMO validation. 28/28 tests green,
  snapshot `20260705T190115Z`, managed restart clean. The "built-but-inert"
  gap is CLOSED — the levers are now live to be measured. ⚠ three interacting
  changes at once → attribution caveat; read Monday's first fire carefully.
- **Missing code: only item-11 (sizing consolidation) commissioned to CC**
  (`CC_ITEM11_SIZING_CONSOLIDATION_2026-07-05.md`) — the one real LIVE-blocker.
  **items 12/13/16/17/7/8 deliberately DEFERRED** until a profitable validated
  baseline exists (don't add latent code).
- Next: run a clean multi-day DEMO validation window with 4/22/6 live, then
  read results before enabling item-10/18/19 or going LIVE.
