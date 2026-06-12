# Handoff → next Cowork chat · MEMS26 יום-תצפית-עוגנים (2026-06-12)

You are Cowork, orchestrating + verifying on Michael's Mac. Claude Code (CC) executes code
changes; you prepare fixes/prompts, verify via repo + live DB + logs (**Rule 5 — paste raw
command+output, never accept CC's "✅"; you caught tautological tests this way on 06-12
night — stash-the-fix→tests-must-fail**), and stop for Michael at trading-logic gates.
Cowork CAN commit+tag+restart when Michael explicitly orders it (done 06-12 01:30); git
push stays with Michael.

## Environment
Repo `/Users/michael/Downloads/mems26_web_git` · local Postgres `postgresql://localhost/mems26`
(NEVER cloud) · backend = **LaunchAgent `com.mems26.backend`** (kill → launchd respawns with
`source .env`; current PID 53821 since 06-12 01:29) · frontend next-dev :3000 (PID 69953) ·
bridge LaunchAgent localhost-only. Mac shell via Desktop Commander, prefix
`set -a && . ./.env && set +a`. Browser checks: Chrome MCP, browser **MACBOOK**
(`43c856d0-...`) — Home MAC can't reach localhost. Trades page works (was never broken).

## ✅ What shipped (06-11 → 06-12 02:30, SHADOW)
- Commit `e6d214e` **[ANCHOR-TRIAL]** + revert tags `pre-anchor-trial-2026-06-12`(=1e85ba6)
  / `anchor-trial-2026-06-12`. Rollback = flags OFF in .env + kill (launchd respawns), or revert.
- **LIVE at open:** `PATTERN_RISK_CAPS=1` (per-pattern max_risk_points in stop_anchors.yaml;
  enforcement woodies_system.py:539 — REV over-cap→RISK_CAP_SKIP, CONT→SIZE_DOWN-1c;
  gated on STOP_ANCHORS_V2 too, both ON) · `S2_DETECTION_LOG=1` (per-bar condition vectors
  `[S2-DL]` for REACTIVE+INITIATIVE) · pattern_id fix (id 43 VEGAS bug; `resolve_pattern_id()`
  extracted, genuine RED-on-revert tests).
- **Implemented, flag OFF (Michael's morning decision):** `RUNNER_TARGETS_V1` — runner T2 =
  min(R-mult 2.0 CONT/1.5 REV, structural), woodies_system.py:604 + BE+0.5R after T2
  (manager.py:340). 19/19 tests green (Cowork-verified). T3 trail NOT implemented.
- **Uncommitted when this chat ended:** manager.py + woodies_system.py (runner work) —
  CC was finishing EOD script + second commit. VERIFY FIRST THING.

## Key analyses (all in docs/, indexed in ROADMAP_TO_LIVE.html §אינדקס)
- **Sim 06-11 tri-config** (`SIM_0611_ANCHOR_TRIAL_2026-06-12.md`): BASE −$267 · CAPS −$178
  · CAPS+T2 **+$3** (+$270). Sim's cooldown+single-position prevented the HFE storm entirely
  ⇒ entry discipline > caps; caps are the safety net.
- **S2 replay** (`S2_WHY_NOT_FIRED_REPLAY_2026-06-11.md`): geometry was real — 25 near-misses
  killed by exactly ONE condition: `b2_vsa` ×9 (REACTIVE), `b1_expansion` ×13 (INITIATIVE —
  why it NEVER fired). Pipeline LOST Double-Bottom LONG detections (19:05–19:15) — **#49 fired
  HFE SHORT into active LONG geometry (spec deviation, Michael's screenshot, confirmed)**.
  17:50 REACTIVE detected-not-traded. HnS/DT_AA/Flags: geometry truly absent (0/79 bars).
- **Counter-signals**: `systems_agreement` disagree NOT predictive; **opposite-direction fires
  within 15min = real red flag** (13 pairs, nearly each had a big loser).
- 06-11 live: 34 trades −$2,187 shadow; HFE storm −$1,957 (shared anchor 7323.25/7387.25);
  winners +0.4R-on-third vs losers −1R-full; only-ever T2_HITs: ids 10/13/20.

## 🔴 Morning queue (06-12)
1. **Verify CC's overnight finish**: EOD script (`scripts/eod_anchor_trial_report.py`),
   second commit (tags untouched!), 19/19 still green. Rule 5.
2. **Michael decisions:** ① `RUNNER_TARGETS_V1=1` for observation day? (sim says yes;
   needs kill→launchd-respawn) ② `git push` ③ run
   `docs/research/EXTERNAL_CHAT_RESEARCH_PROMPT_2026-06-12.md` in external chat.
3. **At open verify live:** `[S2-DL]` lines flowing · first RISK_CAP_SKIP/SIZE_DOWN events ·
   pattern_id correct on new S2 trades · id60 ZLR PARTIAL (+25pt) follow-up.
4. **EOD (together):** CC's counterfactual report + `[S2-DL]` histogram → Michael's FINAL
   anchor decision (keep/calibrate/revert-via-tag) + b2_vsa/b1_expansion calibration +
   merge external research → ONE final recommendations doc.

## Open gates (Michael only)
Per-pattern cooldown after stop-out (HFE storm killer) · COUNTER_PATTERN_VETO (designed,
#49 evidence) · STOP_AFTER_T1_STRUCTURAL (D-002) · b2_vsa/b1_expansion calibration ·
S2 chain order/dedup losing detections (CC research, no fix yet) · T3 trail · CVD snapshots
+ S4_DETECTION_LOG (light, deferred) · observation-week plan
(`CC_PROMPT_PATTERN_OBSERVATION_WEEK_2026-06-11.md`).

## Disciplines (non-negotiable)
Rule 5 raw evidence · trading-logic = flag-gated default-OFF + anti-tautological RED-on-revert
test + Michael gate · Standing Decisions stay OFF (chop gates, S2_REQUIRE_COT_AMT) · local
Postgres only · bridge localhost-only · polling floors · §7a sc_study/bridge · source-of-truth
Rule 1 (None, never synthesize) · boards auto-update every task · no present_files for
tracking files · Drive tracker: `1ydisW_4JJipSs5YQ4oS7L3sSPr_CCdb9` · placement table:
`1IW5SQytZ6iFGcLSVgeE9tKo7BmEqDyFk`.
