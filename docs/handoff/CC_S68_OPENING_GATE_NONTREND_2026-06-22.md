# CC Handoff — Opening-type gate + Nontrend width-floor (Michael 2026-06-22)

**Owner:** Cowork → CC · **Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` · **Risk:** trading-surface · **Default:** flag-OFF · **Enable:** Michael + SHADOW.

## Why (today's live evidence)
2026-06-22 opened **OPEN_DRIVE UP (confidence 0.85** — "no return through opening print, monotonic"). The system fired **4 SHORTS *against* the up-drive** (08:30–09:05, pre-IB-lock, stamped **Nontrend**) → run over by the push to 7599 → **−$555**. The drive then failed and reversed down; the later with-break shorts won (+$275). Two root causes:
1. **Nontrend misclassification** — session range was **72pt** (06-19 真Nontrend = 14.5pt). Nontrend's no-block gap let the counter-drive shorts through.
2. **No opening-type gate** — the system already DETECTS `OPEN_DRIVE UP 0.85` (via `opening_detector_v2`) but never uses it to gate fires.

Michael's principle: don't blanket-block the opening — **enable the opening trade WITH the drive, block AGAINST it.**

## Fix A — Nontrend width-floor (flag `NONTREND_WIDTH_FLOOR`, default OFF)
- In the classifier (`daytype_classifier.classify` / `relative_features`), a day **cannot be Nontrend if session range (high−low so far) > `NONTREND_MAX_RANGE_PTS` (config, default 18)**. If range > 18 and the result would be Nontrend, fall to the next-best type (≥ Normal).
- Verified by Cowork: today 72pt → **Normal** ✓ · 06-19 14.5pt → **Nontrend** ✓.
- Test: synthetic Nontrend-features + range 14pt → Nontrend; same + range 25pt → Normal. Real replay: 06-19 Nontrend, 2026-06-22 not-Nontrend.

## Fix B — Opening-type gate (flag `OPENING_TYPE_GATE`, default OFF)
New gate in `trading_gateway.route_setup`, governs ONLY the **opening window** (RTH open → IB-lock). After IB-lock it is inert (the existing day-type/position gates take over). Fail-open on missing data.

**Drive direction (from bars-so-far, in-memory):**
- Once ≥6 RTH bars: use `detect_opening_type` → `opening_type` + `direction`.
- Before 6 bars: use the running bias = sign(last_close − opening_print).

**Rule:**
- `OPEN_DRIVE` / `OPEN_TEST_DRIVE` (or early directional bias) → **ALLOW fires WITH the drive direction; BLOCK counter-drive.** (Today: allow LONG, block SHORT.)
- `OPEN_AUCTION` / rotation (≥3 crossings of the open) → **HOLD all fires** until IB-lock (no opening edge — e.g. 06-19).
- If the drive **fails** (price returns through the opening print after driving) → release the block + let reclassification take over (the failed-drive → reversal case, e.g. today's later breakdown).

**Order:** this gate runs BEFORE the position gate during the opening window (it's the first directional filter at the open).

**Anti-tautological tests (drive REAL route_setup, assert `result["blocked_by"]=="opening_type_gate"`):**
- Today first-hour bars (OPEN_DRIVE UP) → SHORT setup BLOCKED, LONG setup PASSES.
- Flip the drive (mock DOWN) → LONG blocked, SHORT passes (proves it consults the drive, not a constant).
- 06-19 bars (OPEN_AUCTION) → fires HELD.
- Flag OFF → never blocked_by opening_type_gate.
- Post-IB-lock → gate inert (does not block).

## SHADOW validation (before LIVE) — Rule 5
Enable both flags on a session; over the opening hour log `opening_type` + every fire's blocked/allowed decision. Verify: counter-drive fires blocked, with-drive allowed, rotation-open holds; 0 tracebacks; health <100ms. Paste raw evidence. Re-run today's tape (counterfactual): the 4 counter-drive shorts must be blocked.

## NOT-DONE / open
- Interaction with `DAYTYPE_POSITION_GATE` in the opening window (opening gate wins first).
- The earliest-bar bias threshold (how strong before it blocks) — tune in SHADOW.
- Enabling either flag = trading-surface change → **Michael sign-off required**; keep both default-OFF.
