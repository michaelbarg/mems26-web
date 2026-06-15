# Handoff → next Cowork chat · MEMS26 **fire-fixes verification** (2026-06-15, week start)

You are Cowork, orchestrating + verifying on Michael's Mac. CC executes code changes; you
prepare fixes/prompts, verify via repo + live DB + logs (**Rule 5 — paste raw command+output,
never accept CC's "✅"**), and stop for Michael at trading-logic gates. Cowork CAN
commit+tag+restart only when Michael explicitly orders it; `git push` stays with Michael.

**Purpose of this handoff:** last trading day was Fri 06-12 (anchor-trial day); 06-13/06-14
were closed; today Mon 06-15 reopens. Below is the **repo-verified** static state of the
S2+S4 fire fixes (✓ = I confirmed it from code/git/.env today) and the **🔴 LIVE checklist**
that must be run at RTH open via Desktop Commander + Postgres (sandbox can't reach the Mac).

## Environment
Repo `/Users/michael/Downloads/mems26_web_git` · local Postgres `postgresql://localhost/mems26`
(NEVER cloud) · backend = LaunchAgent `com.mems26.backend` (kill → launchd respawns with
`source .env`) · frontend next-dev :3000 · bridge LaunchAgent localhost-only. Mac shell via
Desktop Commander, prefix `set -a && . ./.env && set +a`. Browser checks: Chrome MCP, browser
**MACBOOK** (Home MAC can't reach localhost).
**⚠️ Confirm first:** the 06-12 plan was to migrate to a dedicated trading machine
(`docs/runbooks/MIGRATION_TO_TRADING_MACHINE.md`, this Mac → dev-only). Verify whether that
happened over the weekend before treating this Mac as the live host.

## ✓ Verified static state (repo, 2026-06-15)
- **Branch** `stabilize/mems26-local-truth-2026-05-16` · HEAD `8930466` (Fri 06-12 23:41).
- **85 commits ahead, 0 behind upstream — UNPUSHED.** Remind Michael to push from the Mac.
- **Tags:** `pre-anchor-trial-2026-06-12` (=`1e85ba6`, rollback point) ·
  `anchor-trial-2026-06-12` (=`e6d214e`). Rollback = flags OFF in .env + kill (launchd
  respawns), or `git revert`/checkout tag.
- **Working tree clean** except `docs/plans/STATUS_BOARD.md` (M) + `.claude/settings.local.json`
  (untracked). All runner/EOD work from 06-12 IS committed (no dangling uncommitted fix).
- **Regression tests present:** `test_a7_rr_on_runner.py`, `test_pre_fire_risk_gates.py`,
  `test_pre_fire_t2_none.py`, `test_s1_provisional_daytype.py`, `test_giant_bar_stop.py`,
  `test_s2_independent_of_s3.py`. (Re-run + paste raw before claiming green — Rule 5.)

## ✓ Fire fixes — what they are + where they live (all confirmed in code/.env)
| Fix | Where | Flag (.env state) |
|---|---|---|
| **A7 R:R on the RUNNER, not the T1-scalp** (THE dominant blocker — applied to both S2 & S4) | `backend/v9/shared/pre_fire_validator.py:79-88` — reward = `abs(t2-entry)`; T2=None → `expected_t2_r_mult` (default 2.0). Commit `319e303` | **structural, no flag** (the corrected measurement is always on) |
| Stop-sanity gates (reject degenerate / oversized stops) | same validator, `MEMS_MIN_RISK_POINTS` / `MEMS_MAX_RISK_POINTS` | both **set** |
| S4 bars un-silenced (price-band check only for 5min stream) | `backend/v9/api/v9/bars.py` `_route_bar` | structural |
| S1 provisional day_type @30min (opens auth in first hour) | `state_machine.py` `_maybe_provisional_classify` | `S1_PROVISIONAL_DAYTYPE=1` ✓ (+ `S1_DYNAMIC_RECLASS`/`S1_LIVE_RECLASS=true`) |
| **PATTERN_RISK_CAPS** (REV over-cap→`RISK_CAP_SKIP`, CONT→`SIZE_DOWN`-1c) | `woodies_system.py:577-663` (gated on `PATTERN_RISK_CAPS` **AND** `STOP_ANCHORS_V2`) | both **=1** ✓; caps in `config/stop_anchors.yaml` |
| **GIANT_BAR_STOP_V1** (intra-bar stop re-anchor; min-range precondition) | `woodies_system.py:621-647` (+ `GIANT_BAR_STOP_FRACTION/FLOOR_PT`) | `GIANT_BAR_STOP_V1=1` ✓ |
| **RUNNER_TARGETS_V1** (runner T2 + BE+0.5R after T2) | T2: `woodies_system.py:705-757` · BE+0.5R: `backend/v9/services/trade_manager/manager.py:340-382` | `RUNNER_TARGETS_V1=1` ✓ |
| **S2_VOL_ADAPTIVE** (loosened b2_vsa → INITIATIVE can fire) | `five_min` detectors | `S2_VOL_ADAPTIVE=1` ✓ |
| **PATTERN_LOSS_BREAKER** (2 losing closes/pattern/session → block) | woodies path | **set** ✓ |
| S2_DETECTION_LOG (per-bar `[S2-DL]` vectors) · S2_CHART_ALL_DAYTYPES | five_min | `=1` ✓ |

**✓ Standing Decisions correctly OFF** (do NOT re-enable without Michael): `LAYER0_CHOP_GATE`
commented out in .env · `S2_CHOPPINESS_GATE` absent (code default OFF) · `S2_REQUIRE_COT_AMT`
absent (code default OFF, S2 ⟂ S3).

## Last live outcome (06-12 anchor-trial day — Cowork-verified, for context)
23 trades (15 S4 + 8 S2), 17W/6L (74%), **net −$350.75** vs 06-11's 34 trades / −$2,187 / 69%
⇒ caps counterfactual **≈ +$1,836**. **INITIATIVE fired for the first time ever** (ids
71/73/74/75/82). **5 real T2 hits** (ids 65/66/78/85/86) — runner mechanism paid for the
first time. LOSS_BREAKER ×8 · caps 7 SIZE_DOWN + 3 REV SKIP · 0 giant-bar events post min-range
fix. **Reframe (I-29 🔴→🟡):** the loss root was **trend-coordination, not mechanism** — on a
V-reversal day damage concentrated in ZLR-SHORT×2 into the tail-bar (ids 69/70, shared anchor,
−$1,069) + REACTIVE_LONG×2 at range-top. **No revert to `319e303`** — calibration = trend-veto
+ stop/target table. Detail: `docs/reports/NIGHT_2026-06-12.md`, `PATTERN_EOD_2026-06-12.md`,
`docs/reports/DESIGNS_2026-06-12.md` (D1–D9).

## 🔴 Market-open LIVE verification (run via Desktop Commander; Rule 5 — paste raw)
0. **Host + process:** confirm migration status; single uvicorn on `127.0.0.1:8000`
   (`lsof -i:8000`); `curl -s localhost:8000/health` → `alive:true, mode:shadow`, <100ms.
1. **Flags loaded in the running process** (not just .env): first `[S2-DL]` line at RTH proves
   `source .env` took. If backend has been up since 06-12, confirm it picked up the current .env
   (else kill → launchd respawn).
2. **day_type@30:** `SELECT to_char(ts,'HH24:MI'), stage, opening_type, day_type, lock_state
   FROM v9_day_type_state WHERE ts::date=CURRENT_DATE ORDER BY ts;` → `day_type ≠ UNKNOWN`
   ~30min after RTH open with `lock_state=PENDING` (provisional). This is the recurring failure —
   confirm it stays closed.
3. **Fires happening + caps live:** `v9_trades` / `v9_woodies_patterns` today not empty; grep
   backend log for `RISK_CAP_SKIP` / `RISK_CAP_SIZE_DOWN` / `GIANT_BAR_STOP` / `[S2-DL]` /
   `LOSS_BREAKER`. Spot-check one S2 trade has the **correct pattern_id** (id 43 VEGAS bug fixed).
4. **No regression:** `/health` <100ms · bridge local-only, 0 push errors (`/tmp/bridge.err.log`)
   · polling floors unchanged.

## Open gates (Michael only — trading-logic, flag-gated default-OFF)
Trend/counter-pattern veto (**D3**, V-reversal + #49 evidence) · **ZLR/HFE price-location
condition** (the main 06-12 bleed root — neither detector has any price-location gate) ·
per-pattern cooldown after stop-out · `STOP_AFTER_T1_STRUCTURAL` (D-002) · b2_vsa / b1_expansion
calibration (needs external research + marker-tool data) · stop/target placement table (**D8**,
anchor calibration) · T3 trail (Trend-only) · observation-week plan
(`CC_PROMPT_PATTERN_OBSERVATION_WEEK_2026-06-11.md`).

## Open items / NOT-DONE (carry forward, not blockers)
D-priority: **D8 stop/target → D3 trend-veto → D5 cluster-guard → D2 (I-31)**. Plus: T1
counter-pattern mgmt (design done, gate) · T2 giant-bar retrace entry (design only) · T4
status.py:250 ghost FiveMinSystem instances · T6 POC/VAH/VAL chart lines wrong source
(local calc vs Sierra — Rule 1) · T7 trade markers on chart (wire `TradeMarkerOverlay`) · T8
chop persistence (`v9_chop_score` empty) + volume indicator — **log-only, gate stays OFF** ·
structural-T2 from Sierra TPO (struct=None is design, not a bug) · **I-22** pnl_r broken only
in T1/BE path (T2 path correct → one-branch fix) · **I-31** false fire-count in pattern-status
display (poisons calibration) · **I-32** gap-ids 64/72/76 in v9_trades · **DIAG agent didn't
run 2 days straight** (0 snapshots — fix trigger before the trading day, §D6) · CVD snapshots /
S4_DETECTION_LOG (deferred).

## Disciplines (non-negotiable)
Rule 5 raw evidence · anti-tautological tests (revert→RED, must import + call production code,
assert on real consumer) · trading-logic = flag-gated default-OFF + Michael gate · Standing
Decisions stay OFF (chop gates, `S2_REQUIRE_COT_AMT`) · local Postgres only · bridge
localhost-only · polling floors · §7a sc_study/bridge · source-of-truth Rule 1 (None, never
synthesize) · consult `SYSTEM_INDEX.md`/`_INDEX.md` before grepping blind · boards auto-update
every task · no `present_files` for tracking files · every CC prompt opens with "פעל לפי
docs/handoff/CC_HANDOFF_CONTRACT.md".

## First actions this session
1. Run the 🔴 LIVE checklist above (host/migration → flags → day_type@30 → fires+caps →
   no-regression). Paste raw.
2. Re-run the 6 regression tests; paste pass/fail.
3. Surface to Michael: (a) 85 unpushed commits — push? (b) migration to trading machine —
   done/run now? (c) which D-item to action this week (data favors D8 + D3).

**Pointers:** Drive tracker `1ydisW_4JJipSs5YQ4oS7L3sSPr_CCdb9` · placement table
`1IW5SQytZ6iFGcLSVgeE9tKo7BmEqDyFk` · roadmap `docs/plans/ROADMAP_TO_LIVE.html` (§אינדקס) ·
source of record `docs/plans/STATUS_BOARD.md` · prior handoff `HANDOFF_NEXT_CHAT_2026-06-12.md`.
