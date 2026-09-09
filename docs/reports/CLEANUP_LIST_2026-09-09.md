# CLEANUP LIST — 09.09.2026 · "לנקות את כל מה שמזיק למסחר ולא אפקטיבי"

**Question (Michael 09.09 09:20):** put the whole system in order — what can be retired, deleted or corrected with **zero trading-risk**, and what needs a ruling.
**Scope / method:** read-only audit at `HEAD d5a5cf46` (09.09 09:10), working tree clean except `config/news_calendar.yaml`. Every claim below carries a file:line or a command output. No file was changed except this report. Nothing was restarted.
**Sub-verdict up front:** the system is not "dirty" in the trading path — it is dirty in **three bookkeeping layers** (flag index, doc registers, logs) that make agents mis-read the trading path. 1 phantom flag, 7 ruled-ON flags that cannot act, 112 undocumented flags (64 of them *ruled*), 6 competing task registers, 2 stale maps, and a log where five templates are 63% of all lines.

---

## 0 · Counts and the mandated command outputs

| What | Number | Evidence |
|---|---|---|
| `.env` assignments / behaviour-flag candidates | **314 / 290** | `/tmp/cleanup0909/flagscan.py` (mtime `.env` = 08.09 18:41) |
| `config/RULED_FLAGS.yaml` rows | **248** | same; `flag_guard.py` → `FLAG-GUARD: PASS — all 248 ruled flags match` · `BUDGET×MIN ≤ CAP: 225×3=675 ≤ 800` |
| Ruled but absent from `.env` | 18 — **all `expected: unset_or_0`** → consistent, not a bug | scan §"RULED but not in .env" |
| `python3 scripts/gen_flag_index.py --check` | **exit 1 — 112 UNDOCUMENTED behavior flags** (was 100 when `FLAG_INDEX.md` was last generated 03.09 23:54) | raw list in §1.5 |
| …of which are *ruled* in `RULED_FLAGS.yaml` | **64** (e.g. `RR_NO_SELF_INFLICTED_V1`, `STRUCT_TARGETS_WIN_V1`, `T3_REQUIRED_V1`, `OPENING_LADDER_V1`, `DALTON_EDGE_COMPASS_EXEMPT_V1`, `MORNING_LABEL_CONFIRM_V1`, `RISK_BUDGET_*`) | cross-join of `--check` output × YAML |
| PHANTOM (in `.env`, no read-site anywhere) | **1** — `OPENING_WINDOWS_V1` | §1.1 |
| INERT-ON (set/ruled ON, cannot act) | **7** (+ `RUNNER_TRAIL_V1`, already 0) | §1.2 |
| Standing-OFF gates from yesterday's list | 19 named → 12 ruled-OFF, 4 unruled-unset, 3 mis-classified | §1.3 |
| `scripts/sot_map_guard.py --strict` | 🔴 `SOURCE_OF_TRUTH.md` cites only 1 source file · 🔴 `SYSTEM_MANIFEST.md` 3 of 7 cited files changed after the map (+53d/+37d/+36d) | §2 |
| `scripts/task_log_guard.py` | ✅ "281 items… the only one" — **but it only globs `docs/plans/OPEN_TASKS*.md`** (`task_log_guard.py:180`); 6 other registers exist | §2.6 |
| `/tmp/backend.err.log` | 379,603 lines · 57.7 MB · 06.09 17:05 → 09.09 09:21 (65 h) · INFO 210,421 / WARNING 161,041 / ERROR 8,105 / CRITICAL 36 | §3.3 |
| `/tmp/backend.log` (uvicorn access log) | **905,136 lines · 70 MB** — `POST /api/v9/live_price` 153,489 · 7× `bars/*` ≈ 52,000 each | §3.3 |

`--check` raw output (first lines, full list is 112 names): `UNDOCUMENTED behavior flags (add to docs/FLAG_REGISTRY.yaml): ACTIVITY_FEED_MAX_AGE_S, APP_STATE_ROOT_FIX_V1, BACKEND_ERR_LOG, BAR5_FAILOVER_SECONDS, BLOCKED_TWIN_V1, CEILING_FLIP_SHORT_V1, … VA_FADE_V1, ZLR_SHADOW_V1` → `EXIT=1`. The check path writes nothing (`gen_flag_index.py:268-274`); `FLAG_INDEX.md` mtime stayed 03.09 23:54.

---

## 1 · TABLE 1 — flags by class, with the safe-to-remove verdict

**Rule that decides most verdicts:** `flag_guard.py:73-75` — for a row with `expected: "0"` or `"1"` the guard needs the *exact* `.env` value; a deleted line reads as `MISSING` → NO-GO. So "remove the `.env` line" is only safe together with a YAML change (`unset_or_0` + RETIRED note — the precedent is `OPENING_CONF_ENGINE_FUSE_V1`, `RULED_FLAGS.yaml:43`). A ruled-OFF gate is **not** cleanup — it is a deliberate dead branch (CLAUDE.md §Standing Decisions).

### 1.1 PHANTOM

| Flag | `.env` | Ruling | Evidence | Verdict |
|---|---|---|---|---|
| `OPENING_WINDOWS_V1` | `=1` (`.env:512`) | expected `1`, 06.08 ("pure detection, zero fire change") | `grep -rn OPENING_WINDOWS_V1 backend bridge` → **only** the docstring `backend/v9/systems/opening_windows.py:19` ("Flag: OPENING_WINDOWS_V1 (OFF)"). The module's single caller is `trading_gateway.py:1233` **inside** the `OPENING_DRIVE_EXHAUSTION_VETO_V1=0` block (:1231, ruled 0 on 19.08) → the whole module is unreachable at runtime. `flag_guard` liveness passes only because `_second_tooth` tests `flag in content` (substring, `flag_guard.py:150-152`), which the docstring satisfies. | **zero-risk:** delete `.env:511-512`, flip the YAML row to `expected: "unset_or_0"` with a RETIRED note (the 06.08 ruling was for a *detector*, and no code consults the flag — nothing can change). Also harden `flag_guard._second_tooth` to require a `getenv/environ` pattern, or this class recurs. |

### 1.2 INERT — read, but the value cannot change behaviour

| Flag | `.env` | Ruled | Why inert (file:line) | Verdict |
|---|---|---|---|---|
| `NONTREND_DISABLE_ALL` | `=1` | no row | Only read-site `daytype_position_gate.py:139`, inside `decide()`, whose only caller is `trading_gateway.py:1745` under `if _position_gate_on` = `DAYTYPE_POSITION_GATE=0` (:1622; ruled 0 since 01.07 "until I-44"). `FLAG_INDEX.md` shows it ✅ ON and the header claims "0 inert". | **zero-risk (doc):** mark INERT in `FLAG_REGISTRY`. Removing the line is also zero-risk (unruled) but pointless until the position-gate ruling is revisited — Nontrend blocking today comes from `daytype_playbook.yaml` cells, not this flag. |
| `NEUTRAL_RESPONSIVE_V1` | `=1` | expected 1 (08.07) | Read only at `trading_gateway.py:2066`, nested in the `DIRECTION_CONTEXT` block (:2042) — ruled **0 permanently** 28.08 ("אין להחזיר"). | doc-mark INERT (parent permanently OFF). Code deletion of the whole `:2042-2106` block = consistent with the 28.08 ruling → **needs one-line ack** (it is `trading_gateway.py`). |
| `LSMA_FLAT_ATR_V1` | `=1` | expected 1 (20.08) | `:2222`, nested in `LSMA_FLAT_GATE_V1` (:2214) — ruled **0 permanently** 28.08. | same as above (block `:2214-2269`). |
| `LEG_EXEMPT_LSMA_FLAT_V1` | `=1` | expected 1 (11.08) | `:2257`, same block. (`direction_compass.py:250` mentions it in a docstring only.) | same. |
| `ENTRY_BUDGET_SKIP_LOSERS_V1` | `=1` | expected 1 (21.08) | `:2304`, nested in `DAYTYPE_ENTRY_BUDGET_V1` (:2275) — ruled 0 the same evening (21.08 19:12, "until the label is stable"). `.env:614` already documents the twin `ENTRY_BUDGET_QUALITY_MIN_CONF` as removed *for this exact reason* — these two were left behind. | doc-mark INERT. **Keep code** — the parent ruling foresees a return. |
| `ENTRY_BUDGET_QUALITY_V1` | `=1` | expected 1 (21.08) | `:2323`, same block. | same. |
| `RELEASE_LEG_EXEMPT_V1` | `=1` | expected 1 | `:2661`, inside `if _rg.enabled()` (:2627) = `RELEASE_ENTRY_GATE_V1=0` (ruled 0, 08.09 17:20, "re-measure after a week"). NB the sibling params `RELEASE_MIN_HIGHER_LOWS/VOL_WINDOW/VOL_RATIO/ZONE_POINTS/MAX_BARS/STOP_BUFFER_POINTS` are **still LIVE** through `five_min_system.py:2273` (`edge_fade` ARM→RELEASE calls `check_release`, `release_gate.py:145-156`), and `RELEASE_TREND_BYPASS_PTS` is LIVE via `:1989`/`:2426`. | doc-mark INERT; keep (the parent is a one-week trial). |
| `RUNNER_TRAIL_V1` | `=0` | expected 0 (08.09) | `bar_level_detector.py:964-978` — `elif` unreachable under `DYNAMIC_STRUCT_TRAIL=1`; the code itself logs "INERT". | already correct; nothing to do. |
| `S4_GRAY_RELABEL_CCI` | `=100` | expected 100 (17.07, note says "inert, dormant backup") | `trend_relabel.py:44` under `S4_GRAY_RELABEL_V1=0`. | already declared; nothing to do. |
| `MORNING_LABEL_CONFIRM_V1`, `DAY_DIRECTION_STRUCTURAL_V1` | `=0` | expected 0 (25.08 "held OFF until fix") | `:1557`, `:1309`; YAML note documents the `_app_state` source is always None. | correct as-is. Not "ON against OFF" — the index simply has **no row** (both in the undocumented list). |

### 1.3 Yesterday's "INERT" list — re-classified (these are gate *reason strings*, not flags)

| Gate reason (`blocked_by`) | Flag → state | Ruling | Class |
|---|---|---|---|
| `suffering_side_veto` (:1149) | `SSV_GATE_V1=0` | 15.07 | STANDING-OFF (ruled) — keep line + row |
| `chop_searching` (:1191) | `LAYER0_CHOP_GATE` unset | 08.06 standing (CLAUDE.md) | STANDING-OFF — keep row |
| `opening_type_gate` (:1219) | `OPENING_TYPE_GATE=0` | 13.08 "until ib_locked chain fix" | STANDING-OFF |
| `drive_exhaustion_veto` (:1272) | `OPENING_DRIVE_EXHAUSTION_VETO_V1=0` | 19.08 | STANDING-OFF |
| `trend_direction_gate` (:1631) · `reactive_location` (:1649) | `TREND_DIRECTION_GATE=0` · `REACTIVE_LOCATION_GATE=0` — **no YAML row**; ruling lives only as an inline `.env` comment (`.env:90`, `:96`, "OFF Michael 2026-07-02") | 02.07 | STANDING-OFF, **unregistered** → add YAML rows (zero-risk) |
| `daytype_position_gate` (:1758) | `DAYTYPE_POSITION_GATE=0` | 01.07 | STANDING-OFF |
| `direction_context` (:2097) | `DIRECTION_CONTEXT=0` | 28.08 **permanent** | STANDING-OFF (dead forever) |
| `multiday_veto` (:2192) | `MULTIDAY_VETO_V1` unset, **no ruling, no `.env` line** | — | dead branch, unowned |
| `lsma_flat` (:2259) | `LSMA_FLAT_GATE_V1=0` | 28.08 **permanent** | STANDING-OFF (dead forever) |
| `day_entry_budget` (:2338) | `DAYTYPE_ENTRY_BUDGET_V1=0` | 21.08 | STANDING-OFF |
| `system7_score` (:2601) | `SYSTEM7_SCORE_V1` unset (S7 is shadow-log by ruling 05.08) | — | dead branch by design |
| `day_direction_doctrine` (:2796) | `DAY_DIRECTION_DOCTRINE_V1` unset, **no ruling, no `.env` line** | — | dead branch, unowned |
| `zone_limit_late_entry` (:3828/:3851) | `ZONE_LIMIT_ENTRY_V1=0` | 14.08 | STANDING-OFF |
| `consecutive_loss_halt` (:3909) | `RISK_CONSECUTIVE_LOSS_LIMIT=0` | 20.07 | STANDING-OFF |
| `chase_tip_revoke` (:2479) | `EXTREME_CHASE_TIP_REVOKE_V1` unset, no ruling | — | dead branch, unowned |
| `OPPOSITE_EXIT` (:3982) | `OPPOSITE_EXIT_V1` unset | 14.07 until EXIT-v2 | STANDING-OFF |
| `NONTREND_DISABLE_ALL` · `RUNNER_TRAIL_V1` | see §1.2 | | INERT (true) |

Unruled `=0` lines that equal the code default and can go without any guard change: `HTLB_LATCH_RESET_V1=0` (`woodies_system.py:319`), `ORPHAN_AUTO_STOP_V1=0` (`sierra_position_reconciler.py:705`), `STOP_TABLE_V1=0` (`trading_gateway.py:2923`) — zero-risk, but also zero value; leave unless tidying.

### 1.4 LIVE but invisible — the six the index lacks

`FIXED_CONTRACTS_5=1` (`contract_size.py:66`), `STRUCT_TARGETS_WIN_V1=1` (`:3408`), `RR_NO_SELF_INFLICTED_V1=1` (`:3682`), `T3_REQUIRED_V1=1` (`sierra_command.py:894`), `OPENING_LADDER_V1=1` (`opening_entry.py:298`), `DALTON_EDGE_COMPASS_EXEMPT_V1=1` (`:2152`, inside `DIRECTION_COMPASS_V1=1` → LIVE). All six: `grep -c "^| <flag>" docs/FLAG_INDEX.md` = 0 and `grep -cE "^  <flag>:" docs/FLAG_REGISTRY.yaml` = 0. The index also shows `RELEASE_ENTRY_GATE_V1` ✅ ON (`FLAG_INDEX.md:389`) and `RUNNER_TRAIL_V1` ✅ ON (`:218`) against `.env` `=0`/`=0`, and renders `TREND_DIRECTION_GATE`/`REACTIVE_LOCATION_GATE` as "🔢 param" (`:169`, `:180`) because of the inline comments.

### 1.5 SHADOW (read, routes to shadow only) — as declared, all consistent

`S2_CVD_DETECTION_V1`, `DELTA_BREAKOUT_RELEASE_V1` (live path = `edge_fade` → `release_gate.py:93,162`), `RE_ACCEPTANCE_V1`, `FAILED_RE_IB_V1`, `TREND_STEP_ENTRY_V1`, `S1_STRUCTURAL_BINARY_V1`, `S2_DELTA_DBL_V1`, `TARGET_MIN_SPACING_V1`, `S1_DAY_DIRECTION_V1`, `APP_STATE_ROOT_FIX_V1`, `FAILED_BREAK_VA_V1`, `CEILING_FLOOR_STATE_V1`, `VA_FADE_V1`, `STRUCTURE_EXIT_FAILBREAK_V1`, `CEILING_FLIP_SHORT_V1`, `BLOCKED_TWIN_V1`, `ZLR_SHADOW_V1=1`. Two of them are the #2 and #5 log-noise sources (§3.3).

---

## 2 · TABLE 2 — contradicting and stale documents

| # | Documents | The contradiction / staleness (quoted) | Fix | Risk |
|---|---|---|---|---|
| 2.1 | `docs/spec_authority/REACTIVE_SPEC_DRAFT.md` (28.06, header: "DRAFT · טרם יושם … **לא יושם בקוד**") vs `docs/spec_authority/S2_AUTH_TABLE_V1.md` (🔒 LOCKED 25.05) vs **code** | Draft `:28`: "⛔ **Variation / Trend_Normal / Trend_DD** → **לא REACTIVE**… שייכים ל-INITIATIVE (מאושר 2026-06-28)"; `:90`: "Variation/Trend = INITIATIVE, לא REACTIVE". Auth table `:63-64`: `REACTIVE_LONG/SHORT` on TN/TDD = "⚠️ 2/1/0" (reduced, **allowed**), on NV = "✅ 3/2/2" (full). Code `config/daytype_playbook.yaml:188`: `REACTIVE: { require_with_trend: true, cells: { Trend_Normal: FULL, Trend_DD: FULL, Variation: FULL … } }` — a **third** position (allowed, with-trend only). | **needs-ruling** (already a strategic stop in `MEASUREMENTS.md` §S2, 08.09): Michael names the governing doc; the loser gets a SUPERSEDED banner. | ruling |
| 2.2 | `CLAUDE.md:38-45` §"Agent Sync — read `AGENT_SYNC.md` **FIRST, every session**… any row addressed to you is a task — handle it first" vs `CLAUDE.md:36` "`AGENT_SYNC.md` נשאר לתיאום … **ההיסטורי**" | `docs/handoff/AGENT_SYNC.md` last commit **17.07** (54 days); its 🔴 OPEN table still holds **15 rows**. A new agent obeying §Agent Sync executes July tasks first. | demote §Agent Sync to one line "historical, see LIVE_CHANNEL"; add a SUPERSEDED banner to `AGENT_SYNC.md`. | zero-risk |
| 2.3 | `docs/SOURCE_OF_TRUTH.md` (last commit 01.09) | `sot_map_guard --strict`: "🔴 cites only 1 source file(s). A map of this system cannot honestly rest on that few." CLAUDE.md §Codebase Index still says "consult BEFORE querying/wiring any signal". | either cite `file:line` per row (the guard's own instruction) or strip it to the 4 rows the guard can verify; log the choice in TASK_LOG. | zero-risk |
| 2.4 | `docs/SYSTEM_MANIFEST.md` (last commit **11.07**, 60 days) | guard: "3 of 7 cited files changed after the map: `scripts/trade_activity_feed.py` +53d · `scripts/gen_flag_index.py` +37d · `sc_study/MES_AI_DataExport_merged.cpp` +36d". CLAUDE.md §Change-Safety still calls it "the map of every surface — consult + keep current". | re-read the 3 rows, update, commit (the commit timestamp clears the guard). | zero-risk |
| 2.5 | `docs/FLAG_INDEX.md` (generated 03.09 23:54) | see §1.4; header "162 ON (of which **0 inert**)" while §1.2 lists 7. `--check` = exit 1 / 112 undocumented, **64 of them ruled** — i.e. the ruling exists in `RULED_FLAGS.yaml` but the index cannot show it. | add the 64 registry stubs from the YAML notes (mechanical), then `python3 scripts/gen_flag_index.py`; make `--check` part of `fire_drill` so the index cannot lag again. | zero-risk |
| 2.6 | Competing task registers (CLAUDE.md: "אל תיצור קובץ-משימות מתחרה") | `docs/handoff/MASTER_BACKLOG.md:1` still titles itself "**אינדקס-משימות ראשי (מקור-אמת יחיד)**" (last 14.08); `docs/plans/DEV_BACKLOG.md` (22.07), `docs/plans/OPEN_ITEMS_2026-07-06.md`, `docs/plans/EXECUTION_PLAN_OPEN_ITEMS_2026-06-04.md`, `docs/handoff/OPEN_ITEMS_PRE_LIVE_2026-05-28.md`, `docs/reports/OPEN_ITEMS_SINCE_THU_2026-09-01.md`. `task_log_guard.py:180` only globs `docs/plans/OPEN_TASKS*.md` → passes ✅. | SUPERSEDED banner on all six; widen the guard glob to `**/{OPEN_TASKS,OPEN_ITEMS,*BACKLOG}*.md` minus an allow-list. | zero-risk |
| 2.7 | Handoff docs that instruct a state the code no longer has (`docs/handoff/` = **677** files, **402** `CC_*` prompts, no index) | `CC_LIVE_PREP_2026-07-22.md:26,:83` "`LSMA_FLAT_GATE_V1=1` — 🔴 בנוי OFF — **להדליק**" and `CC_SMART_BUILD_2026-07-22.md`, `CC_T1_STRUCTURE_END_2026-07-21.md` (same flag; ruled **permanently 0** 28.08) · `NEW_CHAT_ONBOARDING_2026-07-02.md:56` "revert `DAYTYPE_POSITION_GATE=1` after validation" (ruled 0; playbook supersedes) · `GAP_REGISTER.md:68` lists `DIRECTION_CONTEXT=1` in the live flag-set (ruled permanently 0) · `CC_PATTERN_ECONOMICS_PACKAGE_2026-07-02.md` (`OPENING_TYPE_GATE`, `DAYTYPE_POSITION_GATE`) · `CC_TRAILING_RUNNER_2026-06-18.md` (`RUNNER_TRAIL_V1`, inert). | SUPERSEDED banner (one line, pointing at the ruling); move pre-01.08 `CC_*` prompts to `docs/handoff/archive/` and generate a 1-line index. | zero-risk |
| 2.8 | `.env:90` and `.env:96` carry inline `# …` comments | `backend/env_loader.py:53` does **not** strip `#` (`val.strip().strip('"').strip("'")`) → the loaded value is `"0  # OFF Michael …"`. Harmless today (still falsy), but the same pattern on a `=1` line would silently read as OFF. | move both comments to their own line (values unchanged, both OFF before and after). Snapshot first (`scripts/mems26_snapshot.sh`) per §Change-Safety. | zero-risk |

---

## 3 · TABLE 3 — code that hurts or duplicates, and the log

### 3.1 `_route_setup_inner` vs `DALTON_PLAYBOOK_V1`

| Item | Finding | Risk class |
|---|---|---|
| Is the playbook behind a flag so `=0` restores today's gates? | **Not verifiable yet — the flag does not exist in code at HEAD:** `grep -rn DALTON_PLAYBOOK backend` → 0 hits. The contract is only in `docs/handoff/CC_DALTON_PLAYBOOK_2026-09-09.md:58`: "`DALTON_PLAYBOOK_V1` — `0` (no change) · `1` (replaces the four gates). **The four old gates stay in code behind `=0`**" and `:49`: replaces `direction_compass` (`:2120-2171`) · `daytype_playbook` (`:1611`) · `location_gate` (`:1733`) · `awaiting_release` (`:2709/2719`, already OFF). Acceptance test when CC lands: `grep -c DALTON_PLAYBOOK_V1 trading_gateway.py` ≥ 4 (one guard per replaced gate) **and** `=0` byte-identical (`tests/` diff on a recorded `gateway_decisions.jsonl`). | verify-on-landing |
| What else becomes redundant once `intent()` owns bias/kind | LIVE today and overlapping the playbook's *bias*: `cont_trend_filter` (`:2029`, `CONT_TREND_FILTER=1` ruled 07.07), `REQUIRE_WITH_TREND_DAY_DIRECTION_V1` (`daytype_playbook.py:71`, gateway `:1334`, ruled 20.07), `NEVERFADE_TREND_ONLY_V1` (`daytype_playbook.py:228`), `VARIATION_WITH_TREND_CONT_V1`. Overlapping *entry kind/location*: `entry_location_quality` (`:1952`; near-inert after T-235/T-244: 82/103 pass, 0 blocked), `extreme_chase_guard` (`:2550`). | **needs-ruling** (each is ruled ON) — but the ruling can be one sentence: "when `DALTON_PLAYBOOK_V1=1`, these are skipped" — i.e. wrap them in `if not playbook_on`, do not delete. |
| Dead branches the playbook makes permanently obsolete | `trend_direction_gate`/`reactive_location`/`daytype_position_gate` (`:1623-1764`), `direction_context` + nested `NEUTRAL_RESPONSIVE_V1` (`:2042-2106`), `multiday_veto` (`:2179-2200`), `lsma_flat` + 2 nested (`:2214-2269`), `day_direction_doctrine` (`:2750-2800`), `opening_type_gate` (`:1200-1225`), `drive_exhaustion_veto` + `opening_windows.py` (`:1231-1286`), `system7_score` (`:2583-2604`), `zone_limit_late_entry` (`:3804-3855`). ≈ **400 lines of `trading_gateway.py` that cannot execute today** (sum of the ranges listed). | deleting code under a **permanently-cancelled** ruling (`DIRECTION_CONTEXT`, `LSMA_FLAT_GATE_V1`) or an **unowned** flag (`MULTIDAY_VETO_V1`, `DAY_DIRECTION_DOCTRINE_V1`, `EXTREME_CHASE_TIP_REVOKE_V1`) is zero trading-risk by construction — still **needs one-line ack** because it edits the gateway and because rows like `DAYTYPE_POSITION_GATE` ("until I-44") / `OPENING_TYPE_GATE` ("until ib_locked fix") / `DAYTYPE_ENTRY_BUDGET_V1` imply a return. Keep those. |

### 3.2 Target writers and stop rewriters — execution order today (all in `trading_gateway.py`, all ruled ON unless noted)

`STOP_RESOLVER_V1` :2817 (stop #1) → `EARLY_ATR_FLOOR_V1` :2846 (stop floor) → `STOP_TABLE_V1` :2923 (**OFF**) → `DAYTYPE_TARGETS_STRUCTURAL` :3003 (targets #1) → `STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1` :3082 (validator) → `T1_STRUCTURE_END_V1` :3179/:3243 (targets #2, "keep") → `T2T3_NO_STOMP_V1` :3256 (patch: stop #1 stomping #1) → `TARGET_ZONES_V1` :3275 (targets #3) → `STEP_SCALED_LADDER_V1` :3337 (targets #4 **and** stop #2 — rewrites `stop,t1,t2,t3` at :3385-3389, no S2 exemption) → `STRUCT_TARGETS_WIN_V1` :3408 (targets #5, "applied AFTER step-ladder so it wins") → `TARGET_STRUCTURE_CLAMP_V1` :3499 (clamp) → `TARGET_REALISM_V1` :3530 (cap) → `RR_ENTRY_GATE_V1` :3618 → `RR_NO_SELF_INFLICTED_V1` :3682 (patch: restores `t1_pre_struct` when the chain itself broke the R:R — ruled 08.09 precisely because #3408 + #2817 combined to block `DOUBLE_BOTTOM_EE_LONG` at R:R 0.27).
Outside the gateway: S2's own stop `five_min_system.py:2651-2676` (discarded by the chain), `opening_entry.py:298-305` (`OPENING_LADDER_V1`, a 6th target writer), `stop_resolver.py:92,137` (`STOP_FLOOR_IB_V1`, `STOP_WIDEN_TO_STRUCTURE_V1`), `sierra_command.py:711-728,894,985` (`RISK_BUDGET_*`, `T3_REQUIRED_V1`, `RUNNER_BY_DAYTYPE_V1`).

| Under a single `trade_economics()` authority | Class |
|---|---|
| **Redundant writers:** `DAYTYPE_TARGETS_STRUCTURAL`, `T1_STRUCTURE_END_V1`, `TARGET_ZONES_V1`, `STEP_SCALED_LADDER_V1`, `STRUCT_TARGETS_WIN_V1`, `OPENING_LADDER_V1` (targets) · `STOP_RESOLVER_V1`, `STEP_SCALED_LADDER_V1`-stop, `STOP_WIDEN_TO_STRUCTURE_V1` (stops). **Redundant patches** that exist only to undo the chain: `T2T3_NO_STOMP_V1`, `RR_NO_SELF_INFLICTED_V1`, `TARGET_REALISM_V1`, `TARGET_STRUCTURE_CLAMP_V1`. | **needs-ruling** (one ruling: "`trade_economics` is the only writer; the flags above become `=0` behind it"). Note `STRUCTURAL_STOP_REPLAY_2026-09-08` already showed the naive structural stop = −$845 vs +$283.80 (n=54) — the authority must be measured before it owns the stop. |
| **Keep as validators (not writers):** `STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1`, `RR_ENTRY_GATE_V1` hard floor, `T3_REQUIRED_V1`, `RISK_MAX_PTS_HARD`, `PATTERN_RISK_CAPS`, `STOP_FLOOR_IB_V1`, `EARLY_ATR_FLOOR_V1`. | keep |
| `STOP_TABLE_V1=0` (unruled, `:2923`) — a third stop-table that never ran. | zero-risk to delete line; code = with the chain ruling |

### 3.3 Log noise — `/tmp/backend.err.log`, 06.09 17:05 → 09.09 09:21 (`/tmp/cleanup0909/lognoise.py`)

| # | Template (logger) | Lines | Share | Rate | What it drowns / note |
|---|---|---|---|---|---|
| 1 | `BarRouter: dispatch total <f>ms for 5min` + `…for woodies_5min` + `SLOW handler BarLevelDetector.on_bar took <f>ms` — **WARNING** | 33,898 + 16,705 + 16,388 = **66,991** | 17.6% | 770/h · 382/h · 414/h | a latency *metric* emitted at WARNING on every dispatch — makes `grep WARNING` useless |
| 2 | `[S1DayDir] SHADOW accepted_break=… \| s1_state=… \| agree=…` — INFO (`S1_DAY_DIRECTION_V1=shadow`) | **46,781** | 12.3% | up to **40/min** (08.09 21:10); 3,019 active minutes | prints per evaluation, not per change |
| 3 | `T1 HIT: trade <n> at <f>` 23,819 · `T0-remap: DLL T1 → logical T0` 23,779 · `T2 HIT` 8,514 · `T0-remap: DLL T2 → logical T1` 8,500 | **64,612** | 17.0% | 643/h | "T1 HIT" is a **once-per-trade event** logged 23,819 times → the HIT-loop (T-252 family). A real new hit is invisible. |
| 4 | `F5 swing-trail trade=<n>: … does not tighten stop … HOLD (never widen)` — INFO | **33,654** (SHORT 21,990 + LONG 10,230; `F5 ` total 33,678) | 8.9% | **41 lines/min for one trade** (= every 1.5 s) | trade **#1142 alone = 18,799 lines**, still logging at 08.09 00:27 and 01:32 → a trade the books held open overnight |
| 5 | `[S2-CVD] insufficient coverage: <n>/<n> rows (min=<n>) — returning None (Rule 1)` — **WARNING** (`S2_CVD_DETECTION_V1=shadow`) | **27,962** | 7.4% | 936/h | Rule-1 honesty is right; at WARNING per bar it is spam |
| 6-10 | `SMART_BE no-op … never widen` 7,626 (5,866/h bursts) · `structure-trail anchor` 7,647 · `Coercing datetime→str for pydantic field` 7,860 WARN · `target_divergence_t2/t3 ALERT` 2,816 × 2 WARN (1,898/h — an **ALERT** repeated per second is alert-fatigue) · `closed_bar.zlr=… routed=False` 8,639 | ~37,000 | 9.7% | | |

Top-5 alone = **239,000 lines = 63%** of the file. **The three named claims, checked:** `[Reconcile] AGREED_FLAT` = **20 lines** in 65 h (not "every few seconds" in this window) — but each line is 452-549 chars carrying `db_open=[…49 ids…]` while Sierra reports `position_qty=0` → the real defect is **49 "open" rows in `v9_trades` against a flat broker** (the `exit_ts IS NULL`/CANCELLED class, T-178/T-251), not the print. `F5 swing-trail` = confirmed per-trade-per-1.5 s. `S1DayDir SHADOW` = confirmed, 40/min peak.
**Real signals buried:** ERROR+CRITICAL = 8,141 lines, of which ≈ 8,000 are `[bars/5min] TS-OFFSET-GATE REJECTED batch: newest bar ts 221,0xx s behind now` (the frozen `5min.json`, T-265, repeated on every push); `[DAYTYPE_WATCHDOG] ESCALATION … the 5min feed IS stale` ×35; `[S1] rib=<f> at IB lock — input is not a closed bar` ×29. Those three are the day's actual story and are 2% of the file.
`/tmp/backend.log` is the uvicorn access log — 905,136 lines / 70 MB in the same window (`live_price` 153 K, seven `bars/*` routes ≈ 52 K each): pure bridge/poll traffic.

| Fix | Risk |
|---|---|
| #1 → DEBUG, or WARNING only above a threshold (e.g. > 500 ms); #2/#5 → log on **state change** or once per bar; #3 → once per `(trade_id, level)`; #4/#6 → once per `(trade_id, stop)` change; `target_divergence` → once per trade per gap; `TS-OFFSET-GATE` → rate-limit to 1/min with a counter; uvicorn `--no-access-log` (or a rotated separate file). Logging only — no decision path touched — but it edits `bar_level_detector.py`/`trading_gateway.py`/`bars.py`, so **restart-window** (16:00 IL per protocol) and a regression test that the *first* occurrence still logs. | zero-risk (restart-window) |
| The 49-id `db_open` list: close/cancel the stale rows (`state NOT IN ('CANCELLED')` + cross-check `slot_health.live_open_ids`, memory 08.09) — a DB books fix, not a log fix. | zero-risk to *measure* tonight; the UPDATE = T-251 owner |

---

## 4 · Tonight — zero-risk, no ruling needed

1. **`FLAG_REGISTRY.yaml` + `FLAG_INDEX.md`:** add the 112 undocumented rows (64 can be generated from `RULED_FLAGS` notes), regenerate, wire `--check` into `fire_drill.py`. Fixes §1.4/§2.5 in one commit.
2. **`OPENING_WINDOWS_V1`:** delete `.env:511-512`; YAML row → `unset_or_0` + RETIRED note (§1.1). Harden `flag_guard._second_tooth` to a `getenv`-pattern (`flag_guard.py:150-152`).
3. **Mark the 7 INERT-ON flags** (§1.2) as `INERT (parent OFF)` in their YAML notes + registry → index shows 🟡; add YAML rows for `TREND_DIRECTION_GATE`/`REACTIVE_LOCATION_GATE` (`expected: "0"`, 02.07 ruling from `.env` comment).
4. **`.env:90/:96`:** comments to their own line (snapshot first).
5. **Docs:** CLAUDE.md §Agent Sync → historical; SUPERSEDED banners on `AGENT_SYNC.md`, the 6 registers (§2.6), the 7 handoff docs (§2.7); widen `task_log_guard` glob; refresh `SYSTEM_MANIFEST.md` (3 rows) and `SOURCE_OF_TRUTH.md` (cite file:line) until `sot_map_guard --strict` is green.
6. **Logs (restart-window):** the throttles in §3.3, top-5 first. Expected effect: err.log −60% lines, `grep -E "ERROR|CRITICAL"` becomes readable.
7. **Measure** the 49 `db_open` ids against `slot_health.live_open_ids` and record the count (no UPDATE tonight).

## 5 · Needs a ruling (each is one sentence from Michael)

| # | Ruling asked | Why it is a ruling |
|---|---|---|
| R1 | Which S2 document governs REACTIVE on Trend/Variation: 28.06 draft ("לא REACTIVE"), 25.05 LOCKED table (allowed/reduced), or today's code (with-trend only)? | trading behaviour; three sources disagree (§2.1) |
| R2 | "`trade_economics()` is the only stop/target writer; the 6 target writers, 2 stop rewriters and 4 patches in §3.2 go `=0` behind it once the replay gate passes." | retires 12 ruled-ON flags |
| R3 | "When `DALTON_PLAYBOOK_V1=1`, the bias/kind gates in §3.1 row 2 are skipped (wrapped, not deleted)." | `CONT_TREND_FILTER`, `REQUIRE_WITH_TREND_DAY_DIRECTION_V1`, ELQ, chase-guard are ruled ON |
| R4 | Delete the ≈400 dead gateway lines under **permanently-cancelled** or **unowned** flags (§3.1 row 3, list A); keep the "until-fix" ones (list B). | edits `trading_gateway.py`; zero trading-risk by construction, but CLAUDE.md treats gate removal as a ruling |
| R5 | `SCALE_IN_V1` — already on the table (`SCALE_IN_CLEAN_2026-09-09.md`: n=10 legs −$157.50, mechanism inert since 01.09). | already open |

*Not cleanup, do not touch:* every STANDING-OFF row in §1.3, `S6_TARGET_APPROACH_REALIZE_V1=0`, `ORPHAN_AUTO_FLATTEN_V1`, `STALL_EXIT`/`OPPOSITE_EXIT_V1` (until EXIT-v2), `SYSTEM6_AUTOCORRECT=protective`, the chop gates, `S2_REQUIRE_COT_AMT`. Their `.env` lines and YAML rows are the memory of a ruling; `flag_guard` fails on their absence (`flag_guard.py:73-75`).

---
*Produced read-only by the cleanup audit agent, 09.09.2026 ~09:45 IL. Scan artefacts: `/tmp/cleanup0909/{flagscan.py,flagscan.out,flag_sites.json,lognoise.py,lognoise.out}` on the MacBook (not in git).*
