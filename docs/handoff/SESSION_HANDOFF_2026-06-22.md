# SESSION HANDOFF — 2026-06-22 (Cowork → new chat)

To continue: read this + `CLAUDE.md` + `docs/SOURCE_OF_TRUTH.md`. **Michael works in Hebrew — reply in Hebrew.**

## TL;DR — where we are
The **"unify the 3 mechanisms into ONE brain"** thread. day-type + direction + patterns currently run as
independent, overlapping filters → they conflict → the math inverts (big losers / cut winners) → not
profitable even when each piece "works." We designed the fix (a CASCADE) and **tested the concept before
building**. Honest result: **NOT a proven edge yet → do not hand the engine to CC to build.**

## The honest prototype result (the important part)
Built a Python prototype "brain" (price + volume + CVD, the **same rules across all days** = the over-fit
test) and ran it across 10 days:
- TOTAL all-days **+$937** — but **+$1019 of that is ONE roll-contaminated day (06-09)**.
- TOTAL **clean days only (6 days) = −$11. FLAT.**
- Barely fires: **0 trades on 6 of 10 days**; missed the clean down-moves on **06-16 AND 06-22 (today)**.

Conclusion: the first-pass unified brain is flat-to-negative on clean data and **mis-calibrated (too strict —
misses real moves)**. The earlier +$340 single-day number was an over-fit illusion. ⇒ calibrate + more clean
days + run the **REAL** engine via `backend/v9/services/historical_replay.py` **BEFORE** building. Michael's
rule: honesty over feel-good numbers; test-before-build. The "before" gate was tested and did **not** pass.

## Current task — the replay / brain-view tool (in progress)
Michael asked for a per-day replay chart so he can **SEE how the system reads each day and improve the brain**.
Mockup approved. An agent built v1 — a **READ-ONLY viewer**, split into two scripts because this Cowork VM
**cannot reach the Mac's Postgres** (no driver, allowlist-blocked):

- `tools/export_replay_data.py` — DB→JSON exporter, **RUN ON THE MAC** (SELECT-only, localhost-guarded,
  `default_transaction_read_only`). `--date YYYY-MM-DD` → `tools/replay_data_<date>.json`
  (bars+volume+cci+trend/zlr/hfe, levels IBH/IBL/POC/VAH/VAL, cvd, day_type, trades). Contains
  `# verify column names on first Mac run` comments — **confirm the inferred columns on first run.**
- `tools/replay_brain_view.py` — JSON→HTML renderer, runs anywhere (stdlib + lightweight-charts CDN).
  `--date YYYY-MM-DD` → `tools/replay_<date>.html`: 3 synced panes — price (candles + Sierra-style level
  lines + brain's expected-direction zone-tint from `config/daytype_playbook.yaml` + trade markers) /
  volume / Woodies-CCI.
- **DEMO:** `tools/replay_2026-06-09.html` — **REAL**: candles (193), Woodies CCI, 2 trade markers,
  **IBH/IBL = 7491.0/7415.5** (computed from the real first-hour CT 08:30–09:30 bars, verified twice,
  labeled "IB (from bars)"), **RTH-focused** default view, CT axis. **PLACEHOLDER** (honest "not exported
  yet" notes, **never synthesized**): volume, **POC/VAH/VAL**, CVD, per-bar 7-type day-type.
- Renderer is **proven complete end-to-end** via a clearly-labeled synthetic fixture
  (`tools/_fixture_full.html`, `synthetic:true`) — all panes/overlays draw (volume, 5 levels, CVD,
  ZLR/HFE markers, fade zone-tint). Exporter column names are **pinned against the real ORM models**
  (zero guesses; only the runtime `classify_replay` HTTP call is Mac-checked). Two renderer bugs fixed
  by the finish-up agent: axis was UTC→now CT; CVD was carried but never plotted→now drawn.

### NEXT for the new chat
1. Get Michael's feedback on the demo layout (he wanted: demo → feedback → then build the real thing).
2. Have CC run the one Mac command to fill the real volume/POC/VAH/VAL/CVD/per-bar-day-type (columns are
   already pinned, so it should run clean):
   ```bash
   cd <repo> && export DATABASE_URL=postgresql://localhost/mems26 && \
   python3 tools/export_replay_data.py --date 2026-06-09 && \
   python3 tools/replay_brain_view.py --date 2026-06-09
   ```
3. Refinement already noted: demo shows full Globex (06:55–23:55 CT); Michael likely wants **RTH focus
   (08:30–15:00 CT)**.
4. Then use the tool to **calibrate the brain** (diagnose why it missed 06-16 / 06-22), re-test on clean
   days, and **only if it shows edge**, build per the spec below.
5. **Housekeeping (CLAUDE.md mandatory):** fold this session into `docs/plans/STATUS_BOARD.md` +
   `docs/plans/ROADMAP_TO_LIVE.html` (not yet done — deferred to keep this handoff clean).

## The brain spec (for WHEN it shows edge — do NOT build before that)
`docs/handoff/CC_UNIFIED_PIPELINE_2026-06-22.md` — the 4-layer cascade
(day-type → direction arm/disarm → pattern → management), volume+CVD first-class, "once" semantics.
Flag-gated default-OFF, SHADOW-validate, per-layer Michael sign-off.

## Open threads / flags (full map in `docs/SOURCE_OF_TRUTH.md`)
- **#0 BLOCKER-LIVE feed fix:** CC building `docs/handoff/CC_FEED_BARS5MIN_ATOMIC_2026-06-22.md` —
  `v9_bars_5min` gaps (Sierra JSON read-while-write). Prereq for enabling `DIRECTION_CONTEXT` (needs
  contiguous CVD).
- **LIVE in SHADOW:** `DAYTYPE_POSITION_GATE`, `DAYTYPE_PLAYBOOK`, `DAYTYPE_TARGETS_STRUCTURAL`,
  `RUNNER_TRAIL_V1`, `S1_NEW_CLASSIFIER` + (enabled this session, Michael-approved) `S1_ENGINE_NEW_CLASSIFIER`,
  `NONTREND_WIDTH_FLOOR`, `DEDUP_FIRE_GUARD`, `OPENING_TYPE_GATE`.
- **Built flag-OFF** (need backtest + Michael to enable): `DIRECTION_CONTEXT`,
  `runner_trail.widen_at_R`/`k_wide` (config).
- **Standing-OFF** (Michael written approval to re-enable): `LAYER0_CHOP_GATE`, `S2_CHOPPINESS_GATE`,
  `S2_REQUIRE_COT_AMT`.
- **Footprint / S3:** deferred pre-LIVE (do not touch/use).
- Still open: **#18** backtest `DIRECTION_CONTEXT` across all days · **#22** unify the live engine per-bar
  to the 7-type classifier.

## Discipline / working style (Michael)
- Hebrew. Honesty over flattering numbers. Test-before-build. Diagnose-first (verify with data before editing).
- Pre-LIVE: paste raw command+output (**Rule 5**); smallest correct change; no service starts during audits;
  **honest failure > synthetic value** (never fabricate OHLC/levels/CVD/day-type).
- Don't `present_files` for tracking-file edits (roadmap/status/CLAUDE.md). Local Postgres only; bridge localhost-only.

## Canonical data sources (don't re-derive — see `docs/SOURCE_OF_TRUTH.md`)
- Live OHLC+Woodies: `v9_bars_5min_woodies` (contiguous). OHLC+CVD: `v9_bars_5min` (can gap — check last bar).
- Day-type authority: `GET /api/v9/day_type/classify_replay?date=` (7-type). Levels: `v9_tpo_sessions` CASH.
- Trades: `v9_trades`. ts stored at +03:00 → convert to `America/Chicago`. RTH 08:30–15:00 CT.
