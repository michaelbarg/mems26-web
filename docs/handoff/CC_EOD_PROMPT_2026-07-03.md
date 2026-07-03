# CC handoff — remaining pattern-economics package (2026-07-03 evening)

**Contract:** obey `docs/handoff/CC_HANDOFF_CONTRACT.md` (anti-tautological
fail-on-old tests · mandatory NOT-DONE section · paste raw verification per
Pre-LIVE Rule 5). Full item specs live in
`docs/handoff/CC_PATTERN_ECONOMICS_PACKAGE_2026-07-02.md` (22 items) — this
prompt is the ordered build queue + what changed today. Do NOT re-derive specs
from memory; read the package item before building each one.

---
## State as of this handoff (verify, don't trust — Rule 2)

**Backend runs under launchd** (`com.mems26.backend`, KeepAlive on-failure).
Restart = `launchctl kickstart -k gui/$(id -u)/com.mems26.backend`, **never**
manual `nohup uvicorn` (it bind-collides and dies — this is the likely source
of the "uninitiated restarts"). DB = local Postgres
(`postgresql://localhost/mems26`, psql at
`/Applications/Postgres.app/Contents/Versions/18/bin/psql`).

**LIVE now (flags ON, verified this session):** resolver floor/grid/monotonic/
wrong-side (item-2, e7a1cc8) · counter-REACTIVE-on-Variation SKIP (item-1) ·
`RR_ENTRY_GATE_V1=1` (item-3, Michael approved 07-03) · `FIXED_CONTRACTS_3=1` ·
`DAYTYPE_TARGETS_STRUCTURAL=1` · I-57/I-58/I-59/I-60/I-61 · cooldown OFF
(standing) · `OPENING_FIRE_CVD_V1=1` (un-broken today via I-53 ts cast).

**BUILT this session, flag-OFF (do NOT rebuild):**
- **item-10 `OPENING_WINDOW_FIRE_V1`** (bd4a50e) — positive with-drive override
  of day-type refusals in the first 30 min, wired at BOTH choke points
  (`setup_emitter.py` auth-SKIP + NO_TRADE, gateway playbook-SKIP). Enable is
  SCHEDULED for Monday 15:40 IL (Michael: OFF for the holiday, ON for the next
  full session). 12 tests `test_opening_window_fire_item10.py`.
- **item-19 daily-loss halt `RISK_HALT_V1`** (1302d03) — block-only STOP-DAY
  gate, all modes, closes the 06-29 guards-bus gap (`passes_strict_checks` only
  ran in `mode="live"`). Michael's number `RISK_DAILY_LOSS_CAP=450` is in .env;
  consecutive-loss gated on an explicit `RISK_CONSECUTIVE_LOSS_LIMIT>0` (Michael
  has NOT fixed that number — leave 0). 5 tests `test_daily_loss_halt_item19.py`.

**Michael's LIVE-framework decision (item-19, confirmed 07-03):** halt −$450/day ·
promote to LIVE after **5 demo days with ≥+2R cumulative AND zero mechanical
faults**. The −$450 is built; the promotion criteria are a REPORTING gate — fold
them into the EOD report + a short `docs/plans/LIVE_READINESS_CRITERIA.md`
(GO/NO-GO checklist), not a runtime flag.

**Regression battery green (paste the raw output):**
`pytest tests/v9/regression/test_opening_window_fire_item10.py test_daily_loss_halt_item19.py test_todays_fires_golden_2026-07-02.py test_slot_release_all_paths.py test_fill_routing_i58.py test_dedup_after_gates_i60.py test_target_side_guard_i61.py test_cooldown_default_off.py test_s4_target_sanitize_i59.py test_s2_independent_of_s3.py test_stream_health_unknown_spam.py --noconftest` → **50 passed** last run.

---
## Build queue — ordered (Michael's priority: stop-resolver is lever #1)

Each item: read the package spec → build flag-gated default-OFF → add a
fail-on-old regression test (drive the real path, assert the FIXED behavior;
a test that passes on `HEAD~1` is rejected) → `gen_flag_index.py` if a flag was
added → commit. One thread at a time; report before the next.

1. **item-4 `STOP_RESOLVER_V1`** — THE lever (EOD 07-02: right-direction shorts
   died −1R on tight initial stops, ≈−5..7R CF; report headline #2). Structural
   stop band (floor 0.5×ATR-live, cap 1.2×ATR CONT / 1.5×ATR REV) + rungs =
   REAL bars ±3T (Michael's rule: "the lowest bar in the accumulating part",
   never synthetic). Fold in the walkthrough ladder rulings D-10..D-13
   (VEGAS/GHOST/FAMIR) + HTLB anchor. ATR must be LIVE, not the hardcoded 7.0.
2. **item-9 DBDT alias fix** — `daytype_playbook.yaml` DBDT cells unmapped;
   quick, unblocks playbook coverage for that pattern.
3. **item-11 sizing consolidation + notify** — two sizing systems run in
   parallel (`calculate_size` legacy still in the routing path alongside V2 —
   A5 said "reject" while V2 said 3, 07-02 18:50). Collapse to V2-only; add the
   TradeManager single-point close-notify + FillPoller fallback.
4. **item-18 `DAY_DIRECTION_DOCTRINE_V1`** (full) — the counter-SKIP first step
   is already live (item-1); build the rest: reference = expansion side (not
   local LSMA K=3 that flickers on a bounce), counter opens only after a proven
   stop (2 closes back / double-print). Includes the "trend-mode within
   Variation" runner→hold-to-close (issue #25).
5. **item-16 `VOL_REGIME_V1`** — canonical vol-regime signal (avg-14-bar range,
   threshold 8pt; 07-02 was 16.6) → 3 consumers (2 contracts on violent days,
   wider stops, entry confirm/retest). Coordinate the contract count with the
   `FIXED_CONTRACTS_3` standing decision (regime override needs Michael's word).
6. **item-6 `S4_ENTRY_CONFIRM_V1`** — confirm-bar / delta gate. NOTE: this is
   also the candidate "not-at-a-fresh-drive-extreme" condition for item-10 (the
   08:45 counter-fixture). Build it so item-10 can optionally require it.
7. **item-13 `PB_SHAPE_FILTER_V1`** (P/b pullback shape) + **item-5
   `S2_B4_VOL_V1`** (b4 volume check).
8. **item-12 `TT_SPEC_V2`** — port the transcribed source spec
   (`docs/spec_authority/…TT…`) into `tt.py`: stage-2 pause 3–9 bars below the
   ZL, no trend requirement at the entry bar.
9. **item-22 `TARGET_ZONES_V1`** — level-confluence clustering for C2/C3 target
   ZONES beyond T1 (Michael: "אזורים לקביעת מימושים חוץ מה-T1"). Uses today's +
   prior-day support/POC/VA inventory.
10. **item-17 decision journal** — PG table `v9_decision_journal` (survives
    restart) fed from every choke point + a "why no trade" UI tab. ADAPT the
    existing `missed_trade_detector`; don't build parallel.
11. **item-20 Sierra-Truth-Reconcile** — `position_state.json` comparator +
    naked-stop detector (Michael: "המערכת יודעת לקבל מסיארה את מה שהיה בפועל").

**Checklist debt (do alongside):**
- **Mechanism-C behavioral test** — replace the tautological string-check
  (e291bed) with a real double-push-after-hours behavioral test (the A7
  root: Mechanism-C path missing `fire_setup`).
- **Opportunistic:** green or xfail-with-reason the 21 pre-existing fixture-era
  failures; finish the ts-as-TEXT → timestamptz conversion (I-53 fixed one
  site; `cumulative_delta` + `tpo trading_date` remain).

**Every item, on completion:** update `docs/plans/STATUS_BOARD.md` (finding +
fix + raw verification, per CLAUDE.md) and `docs/plans/ROADMAP_TO_LIVE.html`;
regenerate the index if files moved. Final: one `launchctl kickstart` restart
with a 0-open-trades pre-check, paste the boot-line + health.

---
## Mandatory NOT-DONE section
End your run with an explicit list of every queue item NOT built, why, and what
it needs. Do not silently drop an item. If you hit a plan contradiction or a
trading-risk decision (e.g. a regime contract-count override, enabling any
flag), STOP and ask Michael — do not set the enable flag yourself.
