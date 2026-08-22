# DEAD / INERT SYSTEMS AUDIT — 2026-08-22

> **מייקל: "לסדר את המערכות המתות".** Read-only audit. No code, flag, `.env`, or service was
> changed. Every row carries evidence (log line, DB count, or `file:line`).
> Repo HEAD at audit time: `7062a412`. Backend PID 577 (`uvicorn backend.main:app`), booted
> `2026-08-22 13:08:36`.

## Method + evidence sources

| # | Source | Command / path |
|---|---|---|
| E1 | Live app log | `/tmp/backend.err.log` (116 lines, boot 13:08:36 → 14:24) |
| E2 | Bridge log | `/tmp/bridge.err.log` (only boot-time `Connection refused`; no drift) |
| E3 | Postgres | `psycopg2.connect("postgresql://localhost/mems26")` — 51 tables swept for `count(*)` + `max(ts)` |
| E4 | Decisions feed | `~/SierraChart_Data/v9_export/decisions_archive/*.jsonl` + `gateway_decisions.jsonl` — **9,880 rows, 2026-07-22 → 2026-08-21** |
| E5 | Sierra exports | `~/SierraChart_Data/v9_export/` mtimes (all live files `Aug 22 02:08`) |
| E6 | Flag state | `.env` (268 keys) + `config/RULED_FLAGS.yaml` (195 unique) + `docs/FLAG_INDEX.md` |
| E7 | Code | `SYSTEM_INDEX.md`, `_INDEX.md`, `docs/spec_authority/` |

> **⚠ E4 caveat, proven this audit:** the live decisions feed is polluted by pytest.
> ~791 of 9,880 rows (8.0%) carry fixture-only signatures. See §B.4 — every number in §B that
> comes from E4 is quoted **after** removing them.

---

## A · Systems

### A.1 — Alive / dead per system

| Sys | Module | Alive? | Processing bars? | Candidates ≤30d | Ever fired LIVE? | Gating flags | Evidence |
|---|---|---|---|---|---|---|---|
| **S1** day-type | `backend/v9/systems/day_type/` (+ `daytype_classifier.py`, `classifier_core.py`) | ✅ **ALIVE** | ✅ `_day_type_on_bar` → `5min` | 72 labels total, daily to 08-21 | n/a — gate, not a firer | `S1_NEW_CLASSIFIER=1`, `S1_ENGINE_NEW_CLASSIFIER=1`, `S1_DYNAMIC_RECLASS=1`, `S1_LIVE_RECLASS=1`, `BOOT_DAYTYPE_REPLAY_V1=1` (+12 more, all ON) | E1 `BarRouter: subscribed _startup.<locals>._day_type_on_bar to '5min'`; E3 `v9_day_type_history` last row `2026-08-21 Variation conf=33` |
| **S2** five_min | `backend/v9/systems/five_min/five_min_system.py` | ✅ **ALIVE** | ✅ `FiveMinSystem.process_bar` → `5min` | **926** setups total; 40–95/pattern in 30d | ✅ yes | ~30 flags; `S2_ADAPTIVE_THRESHOLDS_V1=1`, `S2_VSA_VOLUME=1`, `S2_CHART_ALL_DAYTYPES=1` | E1 `FiveMinSystem hydrated + subscribed: ['5min']`; E3 `v9_five_min_setups` max ts `2026-08-21 22:40` |
| **S3** footprint | `backend/v9/systems/footprint/footprint_system.py` | 🔴 **INERT (by ruling)** | ⚠ **subscribed but returns immediately** | 0 | ❌ never | `FOOTPRINT_DISABLED=1` (.env:51) + `S3_MUTE=1` (.env:29) — standing since 06-08 | E1 `FootprintSystem hydrated: cumulative_delta=0.0, today_bars=0` · `subscribed FootprintSystem.process_bar to 'tick_reversal_15','tick_reversal_12'` · `EventDispatcher registered system 3 (footprint) for stream 'tick_reversal_15'/'tick_reversal_12'/'footprint'` · `routing footprint to system 3` |
| **S4** woodies | `backend/v9/systems/woodies/woodies_system.py` | ✅ **ALIVE** | ✅ `WoodiesSystem.process_bar` → `woodies_5min` | **2,329** signals (1,040 ZLR in 30d) | ✅ yes — biggest live producer | `ZLR_SPEC_V2=1`, `TLB_SPEC_V2=1`, `VEGAS_SPEC_V2=1`, `HTLB_DIRECTION_GATE=1`, `HFE_DISABLED=1` | E1 `WoodiesSystem hydrated + subscribed: ['woodies_5min']`; E3 `v9_woodies_signals` max ts `2026-08-21` |
| **S5** TPO | `backend/v9/systems/tpo/tpo_system.py` (`system_id = 5`) | 🟡 **ALIVE, ADVISORY-ONLY** | ✅ `TPOSystem.process_bar` → `5min` | 134 sessions; CASH row every weekday 08-03→08-21 | ❌ never — emits levels, no setups | **no flag at all** (bare `try/except`, `backend/main.py:188`) | E1 `TPOSystem hydrated + subscribed: ['5min']`; E3 `v9_tpo_sessions` last `2026-08-21 CASH+GLOBEX` |
| **S6** supervisor | `backend/v9/systems/system6_supervisor.py` + `system6_exit_signals.py` + `system6_journal.py` | ✅ **ALIVE** | ✅ indirect — `bar_level_detector._system6_scan`, subscribed to `5min` + `woodies_5min` | **7,234** exit decisions in 30d (all `decided_by='auto_loop'`) | ✅ manages live trades (never opens one) | `SYSTEM6_SUPERVISOR=1`, `SYSTEM6_AUTOCORRECT=protective`, `SYSTEM6_EXIT_SIGNALS=1`, `SYSTEM6_EXIT_JOURNAL=1` | E1 `BarLevelDetector subscribed to 5min + woodies_5min via BarRouter`; E3 `v9_exit_decisions` 7,234/30d, max ts `2026-08-21 22:50` |
| **S7** scoring | `backend/v9/systems/system7_score.py` | 🟡 **SHADOW-ONLY** | ✅ computed per routed setup | **75** shadow scores (08-07 → 08-21); 7 would-have-blocked | ❌ **the gate never runs** | `SYSTEM7_SCORE_V1` **absent from .env → OFF** ⇒ `trading_gateway.py:2061` block unreachable. `S7_SHADOW_LOG_V1=1` (.env:464) is the only live path | E3 `v9_s7_shadow_log`: 75 rows, `sizing=0 → 7 blocked`, `sizing=1 → 68` |
| **S8 / S9** | — | ❌ **DO NOT EXIST** | — | — | — | — | Repo-wide grep `system8\|system9\|S8_\|S9_\|SYSTEM8\|SYSTEM9` over `*.py *.ts *.tsx *.yaml *.md` = **0 hits** |

### A.2 — System-level dead wiring found

| # | Finding | Evidence | Consequence |
|---|---|---|---|
| A-1 | **S3 is disabled but still fully subscribed.** EventDispatcher registers system 3 on 3 streams and actively routes to it every boot. | E1 lines 13:08:51 + `13:09:10 routing footprint to system 3 (footprint)` | Dead dispatch on every footprint push; the panel/health surface reports S3 as a "registered system" |
| A-2 | **S3's two input streams are themselves dead tables.** `FootprintSystem` is subscribed to `tick_reversal_15` + `tick_reversal_12`; `v9_bars_tick_reversal` last row **2026-07-02 23:32** (51 days). | E3 | Even if `FOOTPRINT_DISABLED` were flipped to 0, S3 would receive nothing from DB-backed history |
| A-3 | **`v9_system_signals` is a one-writer orphan.** 64,405 rows, **100% `system_id=3 / classification='IMBALANCE'`**, 53,237 of them in the last 30 days — while S3 is disabled. No reader found. | E3 | ~53k rows/month of write amplification with zero consumer |
| A-4 | **TPO history snapshotter writes to the RETIRED SQLite DB.** | E1 `[tpo_snapshotter] task started — tpo.json=… db=/Users/michael/Downloads/mems26_web_git/data/mems26_local.db`; `tpo_history_snapshotter.py:48,74-75,233` (`import sqlite3`); file is **446 MB, mtime 2026-08-20 16:51** | Violates § *DB — local Postgres* in `CLAUDE.md`. TPO history is being persisted to a file nothing else reads |
| A-5 | **TPO route serves knowingly-stale data with no fallback**, once every 5 min, forever. | E1 ×17 `[tpo] Sierra tpo.json stale age=44166.6s > 30.0s — serving anyway (no TPOSystem fallback)` | S5 exists and is subscribed, yet the API prefers a 12-hour-old JSON over the live system |
| A-6 | **LIVE mode is `[2, 4]` only.** | E1 `LIVE mode enabled: systems [2, 4] (LIVE_TRADING_V1)` | S1/S3/S5/S6/S7 cannot produce a live trade by construction — correct, but should be stated once instead of re-diagnosed |

---

## B · Detectors / patterns inside live systems

**32 pattern identities** exist across the four detector families. `PatternName`
(`backend/v9/systems/five_min/output_schema.py:13-20`) is a 12-member `Literal`; S4 uses a
separate `PatternId` enum (`backend/v9/systems/woodies/schemas.py:8-18`, 9 members); 9 more
patterns bypass both and call `gateway.route_setup` directly.

### B.1 — Live-era scoreboard (all-time `v9_trades`, mode-split)

| Pattern | Sys | LIVE n / $ | SHADOW n / $ | Last fire | Detections ≤30d | State |
|---|---|---|---|---|---|---|
| **ZLR** | S4 | 46 / **−$201.25** | 180 / −$1,531.23 | 2026-08-21 | 1,040 signals · 791 decisions | ✅ ALIVE (highest volume, negative live) |
| **REACTIVE_SHORT** | S2 | 17 / **+$161.25** | 67 / −$2,211.02 | 2026-08-21 | 95 setups · 261 decisions | ✅ ALIVE |
| **REACTIVE_LONG** | S2 | 10 / **+$535.00** | 43 / −$1,528.90 | 2026-08-04 (live) | 86 setups · 119 decisions | ✅ ALIVE (best live $) |
| **GB100** | S4 | 12 / **+$381.25** | 18 / +$652.70 | 2026-08-19 | 121 signals · 52 decisions | ✅ ALIVE (best S4 $) |
| **INITIATIVE_LONG** | S2 | 8 / **+$57.50** | 19 / −$992.50 | 2026-08-21 | 40 setups · 37 decisions | ✅ ALIVE |
| **INITIATIVE_SHORT** | S2 | 7 / **+$51.25** | 30 / +$4.66 | 2026-08-05 (live) | 56 setups · 39 decisions | ✅ ALIVE |
| **GHOST** | S4 | 6 / **−$177.50** | 14 / −$532.22 | 2026-08-19 | 83 signals · 76 decisions | 🟡 ALIVE-NEGATIVE (no FULL playbook cell exists) |
| **HTLB** | S4 | 4 / **+$33.75** | 9 / +$885.75 | 2026-08-04 | 66 signals · 16 decisions | ✅ ALIVE (also the S4 direction latch) |
| **TREND_STEP** | side | 4 / **−$197.50** | 12 / −$810.00 | 2026-08-20 (live) | 29 decisions | 🟡 ALIVE-NEGATIVE |
| **BEAR_FLAG_SHORT** | S2 | 3 / **−$51.25** | 7 / −$70.50 | 2026-08-06 (live) | 9 setups · 7 decisions | 🟡 THIN |
| **DOUBLE_BOTTOM_EE_LONG** | S2 | 2 / **+$46.25** | 3 / +$182.50 | 2026-08-10 | 22 setups · 14 decisions | 🟡 THIN-POSITIVE |
| **OPENING_DRIVE** | side | 2 / **−$262.50** | 2 / −$266.25 | 2026-07-31 | 5 decisions | 🔴 STALLED 22 days |
| **CONFLUENCE_RI_ZLR** | side | 1 / **−$42.50** | 2 / +$78.75 | 2026-08-06 | 59 decisions | 🟡 SHADOW-by-design (n<15 rule) |
| **FAMIR** | S4 | 2 / **$0.00** (no `entry_ts`) | 9 / **−$660.00** | 2026-07-22 (shadow) | 56 signals · 52 decisions | 🔴 **DEAD-WIRED** — playbook SKIP ×8 |
| **VEGAS** | S4 | 0 | 4 / **−$614.00** | 2026-07-01 | 7 signals · 6 decisions | 🔴 **DEAD-WIRED** — playbook SKIP ×8 |
| **BULL_FLAG_LONG** | S2 | **0 ever** | 6 / −$405.62 | 2026-08-04 | 6 setups · 3 decisions | 🔴 NEVER LIVE |
| **TLB** | S4 | **0 ever** | 50 / +$792.52 (all pre-06-23) | 2026-08-07 (signal) | **1** signal in 30d · **0** clean decisions | 🔴 EFFECTIVELY DEAD |
| **TT** | S4 | **0 ever** | 0 | 2026-07-21 (signal) | **0** in 30d | 🔴 DEAD |
| **HFE** | S4 | **0** | 27 / **−$2,986.70** | 2026-06-23 | **0 real** (all 396 feed rows are fixtures — §B.4) | 🔴 **CORRECTLY KILLED** (`HFE_DISABLED=1`) |
| **INVERSE_HNS_LONG** | S2 | **0 ever** | 0 | 2026-07-15 (setup) | **0** in 30d | 🔴 DEAD |
| **HNS_TOP_SHORT** | S2 | **0 ever** | 0 | epoch (`1970-01-01` ts bug) | **0** in 30d | 🔴 DEAD + corrupt ts |
| **DOUBLE_TOP_AA_SHORT** | S2 | **0 ever** | 0 | 2026-08-12 (setup) | 1 setup · 1 decision | 🔴 NEVER LIVE |
| **RE_PULLBACK_LONG / SHORT** | S2 | **0 ever** | 0 | never | 0 | 🔴 **TRIPLE-DEAD** — §B.2 |
| **HIGHER_LOW_SECOND_TEST_L/S (HLST)** | S2 | **0 ever** | 0 | never | 0 | 🔴 **DOUBLE-DEAD** — §B.2 |
| **EDGE_FADE_LONG / SHORT** | side | **0 ever** | 0 | never | 0 | 🔴 flag OFF (`EDGE_FADE_V1` unset) |
| **OPENING_ORR** | side | 0 | 1 / +$80.00 | 2026-07-31 | 2 decisions | 🔴 STALLED |
| **OPENING_PULLBACK_CONT** | side | 0 | 1 / −$216.25 | 2026-07-31 | 1 decision | 🔴 STALLED |
| **OPENING_TEST_DRIVE** | side | **0 ever** | 0 | never | 0 | 🔴 NEVER FIRED |
| **OPENING_EXTREME_REJECT** | side | **0 ever** | 0 | never | 0 | 🔴 NEVER FIRED |

**Totals: 32 pattern identities · 13 have produced a live trade · 19 never have.**

### B.2 — Dead-wired: patterns that CANNOT fire even if detected

| # | Pattern | Defect | Kill site | Verified? |
|---|---|---|---|---|
| B-1 | **HLST** (`HIGHER_LOW_SECOND_TEST_LONG/SHORT`) | Emits a name **not in `PatternName`**. `five_min_system.py:2199` rebuilds `pattern_name = f"{kind}_{direction}"` → `"HIGHER_LOW_SECOND_TEST_LONG"`. `get_auth_cell` **raises `ValueError`**, swallowed by `except Exception` → one `logger.error`, zero routing. Also missing from `contract_split._SPLIT_MAP`, and would fail pydantic `T1Setup`. | `backend/v9/systems/five_min/auth_table_v1.py:149-157` raise → `five_min_system.py:2443-2444` swallow | ✅ **CLAIM CONFIRMED, and it is dead twice**: `HIGHER_LOW_SECOND_TEST_V1` is also absent from `.env`, so `higher_low_second_test.py:43-44` returns `(None, 0.0, {})` unconditionally |
| B-2 | **RE_PULLBACK_LONG/SHORT** — 🆕 **same defect class, not previously known** | Name **is** in `PatternName` and **is** in the hardcoded 84-cell dict — but the hardcoded dict is not what runs. `_try_load_yaml_auth()` accepts any table with `>= 70` cells; `config/auth_matrix.yaml` has **exactly 70** (10 patterns × 7 day-types, **no `RE_PULLBACK_*` block**) so YAML wins. Result: **`KeyError`** at lookup, same silent swallow. Also missing from `contract_split._SPLIT_MAP`. Also flag-OFF. | `auth_table_v1.py:122-137` (loader) → `:163` `AUTH_TABLE[(pattern_name, day_type)]` KeyError → `five_min_system.py:2443` | ✅ **Live-log proof:** E1 `[Pkg8/auth_table_v1] loaded 70 cells from auth_matrix.yaml`. The three import-time assertions at `auth_table_v1.py:139-146` only validate the **unused** `_AUTH_TABLE_V1`, so nothing catches it |
| B-3 | **VEGAS** | Every day-type cell = `SKIP` (7 day-types + Nonconviction). Detected + routed every time, then blocked. | `config/daytype_playbook.yaml:178` → `trading_gateway.py:1312` `blocked_by="daytype_playbook"` | ✅ Playbook is LIVE (`DAYTYPE_PLAYBOOK=1`, `DAYTYPE_POSITION_GATE=0` ⇒ the early-return at `daytype_playbook.py:178` does not fire). E4: 6 VEGAS decisions, 6 blocked, 0 live |
| B-4 | **FAMIR** | Every day-type cell = `SKIP`. | `config/daytype_playbook.yaml:180` | ✅ E4: 52 FAMIR decisions, **52 blocked, 0 live** |
| B-5 | **GHOST** (near-dead) | No `FULL` cell exists on any day-type — best case `REDUCED` on Normal/Variation. | `config/daytype_playbook.yaml:179` | ✅ 6 live trades, −$177.50 |
| B-6 | **ZLR** (structurally capped) | Also has **no `FULL` cell** — `REDUCED` on the 3 trend/variation days, `SKIP` everywhere else. The single highest-volume live pattern is permanently size-capped. | `config/daytype_playbook.yaml:161` | ✅ 46 live trades at −$201.25 |
| B-7 | **HFE** | Hard-killed in both the Python and DLL-fallback paths. | `woodies_system.py:461-462` (`patterns = [p for p in patterns if p.pattern_id != "HFE"]`) and `:532` (`… and not _HFE_DISABLED`) | ✅ Working as ruled — **0 real gateway decisions**, see §B.4 |
| B-8 | **Fail-OPEN hole** 🆕 | Any pattern **absent** from the playbook returns `Decision("FULL", …, "unmapped(...)")` — silently *fully* authorized, not blocked. | `daytype_playbook.py:189-190` | Affects `TREND_STEP`, all `OPENING_*`, `EDGE_FADE`, `RE_PULLBACK`, `HLST`, `HFE`, `FIRE_*`. The playbook has 14 keys; the detectors emit 32 identities |

### B.3 — Panel vs reality

| Item | Finding | Evidence |
|---|---|---|
| Panel source | `build_status/auth_table_lookup.py:124-148` → `/api/v9/build/pattern-status` → `usePatternFeed.ts:78` → `AllPatternsPlan.tsx:83`. Exactly **19 rows** (10 S2 + 9 S4). | code |
| **Panel shows HFE** | `WOODIES_PATTERN_IDS` still lists `HFE` although `HFE_DISABLED=1` since 06-24 | `auth_table_lookup.py:138-148` |
| **Panel hides 13 real patterns** | `TREND_STEP`, `RE_PULLBACK_*`, `HLST`, `EDGE_FADE_*`, all 5 `OPENING_*`, `CONFLUENCE_RI_ZLR` have **no** `PatternStatus` row anywhere | grep over `frontend/v9/src` |
| **Stale ghost list in the tree view** | `BuildTreeView.tsx:826-828` lists `GB50`, `RB100`, `RB50` — **three patterns that have never existed as detectors** | code |

### B.4 — 🆕 The decisions feed is polluted by pytest (affects every panel that reads it)

| Evidence | Value |
|---|---|
| Total decisions 07-22 → 08-21 | **9,880** |
| Rows with fixture-only signatures | **≈791 (8.0%)** |
| Fixture pattern names never emitted by any detector | `STRATEGIC` **158** · `NO_SUCH_PATTERN` **79** · `TLB_LONG` **148** (S4 emits `TLB`, never `TLB_LONG`) |
| **HFE: 396 rows, exactly 2 distinct entry prices** — `7595` (324×) and `7600` (72×) | ⇒ **100% synthetic.** `HFE_DISABLED` is doing its job; the feed lied |
| Synthetic entry prices seen | `5900.0`, `7405.0`, `7595`, `7600` — each repeated 2–4× per burst |
| Root cause | `backend/v9/tests/conftest.py:17-24` redirects `GATEWAY_DECISIONS_PATH` to `tmp_path` — but only for tests under `backend/v9/tests/`. **`tests/v9/conftest.py` (137 bytes) and `tests/conftest.py` do not set it**, so the whole `tests/v9/**` suite writes to the live `~/SierraChart_Data/v9_export/gateway_decisions.jsonl` |
| Blast radius | `context_radar.py:27` and `gateway_routes.py:46` (`/api/v9/gateway/decisions`) both read that file. Every "why didn't it fire" answer since 07-22 is up to 8% fiction |

**After removing fixture minutes, the honest 30-day picture is 1,598 clean decisions: 88 live · 215 shadow_only · 1,295 blocked.** Top real blockers: `awaiting_release` 196 · `cold_start_guard` 162 · `daytype_playbook` 135 · `cont_trend_filter` 125 · `eod_entry_cutoff` 102 · `feed_watchdog` 94 · `rr_entry_gate` 93 · `lsma_flat` 89 · `extreme_chase_guard` 68.

---

## C · Flags

`config/RULED_FLAGS.yaml`: **198 entry lines / 195 unique flags** (3 duplicate keys — `FIXED_CONTRACTS_3` L46+L139, `RISK_DAILY_LOSS_CAP` L49+L276, `TARGET_MIN_SPACING_V1` L87+L293). **146 ON · 28 OFF · 20 numeric · 4 string.**
**`.env` vs `RULED_FLAGS`: 0 mismatches — `flag_guard.py` passes.** That is exactly why every
contradiction below is invisible to the guard: each dead flag sits at its *ruled* value.

### C.i — ON, but doing nothing measurable

| Flag | .env | Why it is inert | Evidence |
|---|---|---|---|
| **`RUNNER_TRAIL_V1`** | `1` | **100% unreachable.** `if _f5 is not None: pass` / `elif DYNAMIC_STRUCT_TRAIL` / `elif RUNNER_TRAIL_V1` — the third arm can never be taken under *any* combination of the two ON flags. | `backend/v9/services/trade_manager/bar_level_detector.py:797-833`; `config/stop_anchors.yaml:109-110` "⚠️ INERT"; `FLAG_REGISTRY.yaml:861-867` |
| **`ENTRY_BUDGET_SKIP_LOSERS_V1`** | `1` | 🆕 Guard sits **inside** `if DAYTYPE_ENTRY_BUDGET_V1` (=`0`). Never reached. | `trading_gateway.py:1753` (outer) → `:1781-1782` |
| **`ENTRY_BUDGET_QUALITY_V1`** | `1` | 🆕 Same nesting. Its WARNING at `:1807-1811` — the very instrumentation the 08-21 ruling asked for — can never emit. | `trading_gateway.py:1753` → `:1800-1802` |
| **`OPENING_WINDOWS_V1`** | `1` | 🆕 **Zero code references.** `opening_windows.py:19` is a *docstring*; the module has no `os.getenv` at all. Its only consumer `evaluate_drive_location` is imported at `trading_gateway.py:1051`, inside the `OPENING_DRIVE_EXHAUSTION_VETO_V1` block — which is `0`. | grep + `.env:476`, `.env:479` |
| **`DYNAMIC_STRUCT_TRAIL`** | `1` | Partially inert: shadowed whenever F5 (`RUNNER_TRAIL_V2`) returns non-`None`, which is the normal case. | `bar_level_detector.py:808-810`; `manager.py:1050-1080` |
| **`S3_RELATIVE`** | `true` | Scales thresholds for a system that returns immediately (`FOOTPRINT_DISABLED=1`). | `backend/v9/shared/atr.py:102` |
| **`S3_MUTE`** | `1` | Redundant with `FOOTPRINT_DISABLED=1`, which is strictly stronger (kills processing, not just fires). | `atr.py:108-109` |
| **27 flags emit no log line on their active path** | `1` | Unobservable by design. Worst cluster: the **12 S1 flags in `daytype_classifier.py`** — `classify()` has **no logger at all**, so every day-type decision is unattributable. Also `FIXED_CONTRACTS_6` (the live sizing decision logs nothing). | `daytype_classifier.py:171,217,218,228,268,307,321,400,434,444,481`; `classifier_core.py:82`; `contract_size.py:64` |

> Baseline: only **11 of 146 ruled-ON flags** are ever named in a log message.

### C.ii — OFF and superseded

| Dead flag | .env | Superseded by | Evidence |
|---|---|---|---|
| `FIXED_CONTRACTS_2` / `_3` / `_4` / `_5` | all `0` | **`FIXED_CONTRACTS_6=1`** (.env:300, ruled 08-19 → 6 contracts, ladder 1/2/2/1) | `RULED_FLAGS.yaml:46,138,139,267,268`; resolver `contract_size.py:58-74` |
| `S4_GRAY_RELABEL_V1` | `0` | `TREND_CCI_DIRECT_V1=1` | `RULED_FLAGS.yaml:180` "מנוטרל — מוחלף ב-TREND_CCI_DIRECT_V1 הקנוני" |
| `WOODIES_TS_HOUR_FIX`, `TS_WHOLE_HOUR_NORMALIZE_V1` | `0` | `TS_OFFSET_INGEST_GATE_V1=1` + `V9_CHART_TZ=Chicago` | `RULED_FLAGS.yaml:142,215` |
| `SYSTEM6_REVERSAL_TIGHTEN_V1` | `0` | Ruled OFF because `op=MODIFY_TARGET` has no branch in `_exec` | `RULED_FLAGS.yaml:116` |
| `NEWS_BLACKOUT_BEFORE_MIN` / `_AFTER_MIN` | n/a | `NEWS_WIN_RED` / `_ORANGE` / `_YELLOW` (`news_blackout.py:76`) | **genuinely dead** — only appear in the module docstring at `news_blackout.py:13-14` |
| `S2_REQUIRE_COT_AMT` | unset | Standing-OFF since 06-08 (S2 ⟂ S3). Correct — S3 is down. | `CLAUDE.md` §S2 ⟂ S3 |
| `S2_CHOPPINESS_GATE`, `LAYER0_CHOP_GATE` | unset | Standing-OFF since 06-08. **Verified still off:** the only `chop_searching` blocks in 30d (46) belong to the fixture pattern `STRATEGIC`. | E4 |
| **`TREND_DIRECTION_GATE` + `REACTIVE_LOCATION_GATE`** | both `0` | 🔴 **Superseded by `DAYTYPE_POSITION_GATE` — which is ALSO `0`.** Both were switched off with the comment *"superseded ע"י position-gate/playbook"*; the successor never came on. **Nothing is running in that lane.** | `.env:83`, `.env:89`, `.env:100` |

### C.iii — Contradictory pairs (one flag makes the other dead code)

| # | Pair | States | Shape | File:line |
|---|---|---|---|---|
| C-1 | `RUNNER_TRAIL_V2` ▸ `DYNAMIC_STRUCT_TRAIL` ▸ `RUNNER_TRAIL_V1` | `1` / `1` / `1` | **Two-layer** `if/elif/elif`. V2 shadows both; DST shadows V1. 🆕 The honesty WARNING at `:822-825` lives *inside* the DST arm, so **the "V1 is INERT" warning is itself unreachable** when V2 takes the branch. | `bar_level_detector.py:797-833` |
| C-2 | `DAYTYPE_ENTRY_BUDGET_V1` ▸ `ENTRY_BUDGET_SKIP_LOSERS_V1` + `ENTRY_BUDGET_QUALITY_V1` | `0` / `1` / `1` | 🆕 **Highest-value find.** Three rulings on the same day (2026-08-21) cancel each other: the outer was ruled OFF at 19:12 while the two inner ones were ruled ON. E4 confirms `day_entry_budget` blocked 17 setups on 08-21 and **never again**. | `trading_gateway.py:1753 / :1782 / :1800` |
| C-3 | `FIXED_CONTRACTS_6` ▸ `_5` ▸ `_4` ▸ `_2` ▸ `_3` | `1`/`0`/`0`/`0`/`0` | Early-return ladder. Harmless today, but setting `FIXED_CONTRACTS_4=1` tomorrow would be a **silent no-op with zero warning**. | `contract_size.py:58-74` |
| C-4 | `OPENING_WINDOWS_V1` ▸ `OPENING_DRIVE_EXHAUSTION_VETO_V1` | `1` / `0` | 🆕 The ON flag's only consumer is imported inside the OFF flag's block. | `trading_gateway.py:1049-1051`; `opening_windows.py:19` |
| C-5 | `DAYTYPE_POSITION_GATE` ▸ `DAYTYPE_PLAYBOOK` | `0` / `1` | ✅ **Not** a contradiction today — but `FLAG_REGISTRY.yaml:388-389` still declares the playbook "ON but a NO-OP, inert_when `DAYTYPE_POSITION_GATE=1`". **That text is stale by 180°:** the playbook matrix *is* live (135 real blocks in 30d). `docs/FLAG_INDEX.md:141` repeats the error. | `daytype_playbook.py:178-179`; E4 |

### C.iv — Doc drift in the "cannot go stale" index

| Claim in `docs/FLAG_INDEX.md` | Truth |
|---|---|
| L12: "166 ON, **of which 0 inert**" | ≥5 inert — C-1, C-2 ×2, C-4, plus `DYNAMIC_STRUCT_TRAIL` |
| L16: 6 registry flags "not referenced in code" | **4 of 6 are wrong.** `DIRECTION_COMPASS_V1` is live+ON (read via the module constant `_FLAG` at `direction_compass.py:82,90`; 4 real blocks on 08-20/21). `FIXED_CONTRACTS_2/3/4` are read via the `_on()` wrapper at `contract_size.py:68-72`. The generator only matches literal `os.getenv("NAME")`. Only the two `NEWS_BLACKOUT_*_MIN` are genuinely dead |
| L141: `DAYTYPE_POSITION_GATE=1` / playbook inert | Opposite of `.env` |
| L14: 46 undocumented behavior flags | Confirmed, incl. live ones: `DAYTYPE_ENTRY_BUDGET_V1`, `EXIT_VERIFY_V1`, `SCALE_IN_*`, `STOP_FLOOR_IB_V1` |

---

## D · Data streams

| Stream / table | Rows | Last row | Age | Sierra export mtime | Who consumes | What breaks silently |
|---|---|---|---|---|---|---|
| `v9_bars_5min_woodies` | 13,193 | **2026-08-21 23:55** | fresh | `woodies_5min.json` Aug 22 02:08 | S4, S1 classifier, ATR, `direction_context_live` | ✅ healthy — 276 bars/day, contiguous |
| `v9_bars_5min` | 1,035 | **2026-08-21 23:55** | fresh | `5min.json` Aug 22 02:08 | CVD (`cumulative_delta` col), S2 | 🟡 **partial**: 126 rows/day vs woodies' 276; 08-17 only 84, 08-14 only 78. Known gap-prone (SoT map) |
| `v9_bars_cumulative_delta` | 5,219 | **2026-08-21 23:55** | fresh | `cumulative_delta.json` Aug 22 02:08 | delta features, `DELTA_FEATURES_V1`, radar | ✅ **NOT frozen — the 08-18 freeze is RESOLVED.** 89–90 rows/day 08-13→08-21 (RTH 08:35–15:55 CT). ⚠ 08-20 shows **178** (duplicate day) |
| `v9_tpo_sessions` | 134 | **2026-08-21** | fresh | `tpo.json` Aug 22 02:08 | S1 (IB/VAH/POC/VAL), playbook levels | ✅ CASH+GLOBEX on every weekday 08-03→08-21 |
| `v9_tpo_journal` | 670,786 | 2026-08-21 20:55 | fresh | — | TPO history | ✅ 10k–18k rows/day |
| `v9_woodies_signals` | 2,329 | 2026-08-21 | fresh | — | S4 panel, archive | ✅ healthy |
| `v9_exit_decisions` | 7,234 | 2026-08-21 22:50 | fresh | — | S6 | ✅ healthy |
| **`v9_bars_footprint`** | 2,710,516 | 2026-08-22 13:09 | **misleading** | `footprint.json` Aug 22 02:08 (live) | S3 (disabled) | 🔴 **DEAD.** 2,709,972 of 2.71M rows are from **June**. July = 454, August = **90**. The "fresh" timestamp is a 30-row boot probe. 2.7 GB-class dead weight |
| **`v9_bars_tick_reversal`** | 1,067,963 | **2026-07-02 23:32** | **51 days** | `tick_reversal_12.json` + `_15.json` **Aug 22 02:08 (live!)** | `FiveMinAggregator`, `FootprintSystem`, `ReversalBarHandler` — all subscribed to these streams | 🔴 **FROZEN.** Sierra still exports; the DB write stopped. Silent breakage: `FiveMinAggregator.on_bar_event` is subscribed to `tick_reversal_15`, so 5-min bar synthesis has no DB-backed history to rehydrate from after a restart |
| **`v9_bars_30min_woodies`** | 373,750 | **2026-07-02 22:10** | **51 days** | `woodies_30min.json` **Aug 22 02:08 (live!)** | 30-min stair-steps (`S1_TREND_CONTROL_V1`, `TREND_STEP_STAIR_OR_V1`) | 🔴 **FROZEN.** Both flags are ON and both consume 30-min structure — they are reading a table that stopped 51 days ago |
| **`v9_system_signals`** | 64,405 | 2026-08-21 23:47 | fresh | `imbalance_flags.json` | **nobody** | 🔴 **ORPHAN WRITER.** 100% `system_id=3 / IMBALANCE`; 53,237 rows in 30d for a disabled system |
| `v9_bars_imbalance` | 1,436 | 2026-08-21 20:47 | fresh | `imbalance_flags.json` | S3 (disabled) | 🟡 writing into a dead system |
| `v9_bars_volume_profile` | 5,229 | 2026-08-21 23:08 | fresh | `volume_profile.json` | S5 TPO (`volume_profile` stream) | ✅ but ⚠ 08-20 spike 798 vs typical 30–90 |
| **`v9_bars_stacked_imbalance`** | **0** | — | never | `stacked_imbalances.json` **Aug 22 02:08 (live!)** | — | 🔴 **INGEST NEVER WORKED.** Sierra exports, bridge pushes, table is empty |
| `v9_bars_5min_continuous` | 8,485 | 2026-08-21 23:45 | fresh | `5min_continuous.json` | 🔴 **none** — `close` is garbage, excluded from `/chart/bars5min` 06-24 | orphan model, still being written |
| `v9_bars_woodies` / `v9_woodies_patterns` / `woodies_trade_terminals` | **0 / 0 / 0** | never | — | — | — | 🔴 empty schema stubs |
| `v9_bars_tick_reversal`-family stubs: `v9_footprint_markers`, `v9_footprint_setups`, `v9_killzone_log`, `v9_chop_score`, `v9_system_markers`, `v9_system_configs`, `v9_build_status_archive`, `v9_daily_quality_reports`, `v9_account_status`, `v9_audit_events`, `v9_five_min_state` | **all 0** | never | — | — | 🔴 **11 empty tables** — schema with no writer |
| `v9_tpo_bars` | 5,605 | **2023-11-25** | 3 years | — | — | 🔴 fossil |
| `v9_day_type_shadow_transitions` | 50 | 2026-06-22 | 61 days | — | — | 🔴 dead shadow experiment |
| `v9_reversal_enrichment` | 1 | 2026-06-04 | 79 days | — | `ReversalBarHandler` | 🔴 one row, ever |
| `v9_footprint_journal` | 9,246 | ts stored as **epoch int** `1780663879` | — | — | S3 | 🔴 dead + wrong type |
| Backup tables (`*_bak_0720`, `*_bak_0722fix`, `v9_bars_ghosts_bak_0723`) | 786 total | Jul 20–23 | 30+ days | — | — | 🟡 5 stale backup tables |
| **`data/mems26_local.db`** (SQLite) | — | **mtime 2026-08-20 16:51** | live writer! | — | `tpo_history_snapshotter.py` | 🔴 **446 MB retired SQLite still being written**, against `CLAUDE.md` § DB |
| `~/SierraChart_Data/v9_export/gateway_decisions.jsonl` | 9,880 (30d) | 2026-08-21 22:45 | fresh | — | `context_radar.py:27`, `/api/v9/gateway/decisions` | 🔴 **8% pytest-polluted** — §B.4 |

---

## ACTION TABLE (ranked — decisive)

| # | Item | State | Recommendation | Why | $ impact | Who |
|---|---|---|---|---|---|---|
| **1** | `DAYTYPE_ENTRY_BUDGET_V1=0` shadowing `ENTRY_BUDGET_SKIP_LOSERS_V1=1` + `ENTRY_BUDGET_QUALITY_V1=1` (`trading_gateway.py:1753/1782/1800`) | Two ruled-ON risk flags are unreachable | **RULE** — Michael decides in one line: either the outer goes back to `1` (all three live) or the two inner ones go to `0` (honest). Do **not** leave three same-day rulings contradicting each other | A ruled risk control that provably never executes is worse than no control — it is believed to be on | Unknown; the budget blocked 17 setups on 08-21 alone before being switched off | Michael → CC |
| **2** | pytest writes into the live `gateway_decisions.jsonl` (`tests/v9/conftest.py` missing the `GATEWAY_DECISIONS_PATH` fixture) | 791/9,880 rows (8.0%) are fake, incl. **all 396 HFE rows** | **FIX** — copy the 8-line fixture from `backend/v9/tests/conftest.py:17-24` into `tests/conftest.py`; purge the archive | Every "why didn't it fire" diagnosis since 07-22 was read off a partly fabricated feed. This audit nearly reported "HFE_DISABLED is broken" because of it | 0 direct; unbounded diagnostic cost | CC |
| **3** | `v9_bars_30min_woodies` frozen 51 days (last `2026-07-02`) while `S1_TREND_CONTROL_V1=1` and `TREND_STEP_STAIR_OR_V1=1` consume 30-min structure | Sierra exports fine (`woodies_30min.json` Aug 22 02:08); the DB write is dead | **FIX** — restore the ingest, or prove the two flags read the in-memory stream and not the table | Two live trading flags reading a 51-day-old table is a silent-wrong-answer generator | `TREND_STEP` live = **−$197.50** (4 trades), shadow **−$810** | CC |
| **4** | `TREND_DIRECTION_GATE=0` + `REACTIVE_LOCATION_GATE=0`, both "superseded by `DAYTYPE_POSITION_GATE`" — which is also `0` | Unmanned gate lane | **RULE** — turn the successor on, or delete the two legacy gates and their comments | Three gates off, each pointing at another for cover. The playbook partly covers it (135 blocks/30d) but the direction lane is genuinely empty | Counter-trend entries are the recurring loss class (07-24, 07-31) | Michael |
| **5** | `RUNNER_TRAIL_V1=1` — 100% unreachable; and its own "INERT" warning is unreachable too | Inert | **RETIRE** — set `0`, delete the elif arm, move the WARNING above the `if _f5` branch | Known since 08-17 and still `1`; the guard passes because it is at its ruled value | 0 direct | CC |
| **6** | `v9_bars_footprint` 2.71M rows / `v9_system_signals` 64k rows / `v9_bars_imbalance` — all feeding disabled S3 | Orphan writers | **RETIRE** — stop the S3 EventDispatcher registration + the three writers; archive+drop `v9_bars_footprint` (99.98% June) | 53,237 rows/month written for a system that `return`s on line 1. S3 is deferred until after LIVE by ruling | 0 P&L; DB + I/O | CC |
| **7** | `tpo_history_snapshotter` writes to `data/mems26_local.db` (446 MB SQLite, mtime 08-20) | Live writer to the retired DB | **FIX** — repoint to Postgres or stop the task | Direct violation of `CLAUDE.md` § *DB — local Postgres ONLY*; also the residual "remove the SQLite fallback" item | 0 | CC |
| **8** | **RE_PULLBACK** dead-wired 3× (YAML auth table has 70 cells, no `RE_PULLBACK` block → `KeyError`; no `contract_split` entry; flag unset) | Built, ruled-worthy, cannot run | **FIX then RULE** — add the 7 YAML cells + the split entry + assert on the **loaded** `AUTH_TABLE` (`auth_table_v1.py:139` currently asserts the unused fallback); then Michael rules the flag | This is "the missing Dalton entry" (MASTER_BACKLOG C2). Enabling `RE_PULLBACK_ENTRY_V1` today would produce nothing but swallowed exceptions | Est. from 08-10 study: 1 LONG @7791.25, targets 7801/7811 | CC → Michael |
| **9** | **VEGAS** + **FAMIR** — `SKIP` on all 8 day-type cells; detected and routed every bar, blocked every time | Dead-wired | **RETIRE** — remove from `_DETECTORS` and from the panel, or give them one non-SKIP cell | 58 wasted gateway round-trips in 30d and two rows on the panel that can never light up | VEGAS shadow **−$614**, FAMIR shadow **−$660**. Retiring locks in the avoided loss | CC |
| **10** | **HLST** emits `HIGHER_LOW_SECOND_TEST_LONG`, not in `PatternName` → `ValueError` swallowed at `five_min_system.py:2443` | Dead-wired ×2 (also flag-unset) | **FIX** — add both names to `PatternName` + `contract_split._SPLIT_MAP` + 14 auth cells, or delete the module | Michael's own mandate ("שיזהה את הירידה בפעם השנייה"). Today it is 2 dead files | 0 to date | CC |
| 11 | 27 ruled-ON flags emit **no log line**; 12 of them are the S1 classifier family and `classify()` has no logger at all | Unobservable | **FIX** — one `logger.info` per active branch, rate-limited | 44% day-type disagreement (T-47/F6) is un-attributable to any flag today | Disagreeing days **−$728.75** vs agreeing **+$1,048.75** | CC |
| 12 | `docs/FLAG_INDEX.md` false negatives: `DIRECTION_COMPASS_V1` + `FIXED_CONTRACTS_2/3/4` listed "not in code"; "0 inert"; L141 playbook text inverted | Generated doc is wrong | **FIX** — teach `gen_flag_index.py` to resolve module-constant and single-arg wrapper reads (`contract_size._on`, `direction_compass._FLAG`) | The index says the live sizing family is not in the code. That is the exact failure mode the index was built to prevent | 0 | CC |
| 13 | **ZLR** has no `FULL` playbook cell on any day-type (`REDUCED` at best), yet it is the #1 live pattern | Structurally capped | **RULE** — Michael: is ZLR meant to be permanently size-reduced? | 46 live trades at **−$201.25**; 791 clean decisions in 30d | −$201.25 live to date | Michael |
| 14 | **GHOST** (no FULL cell) + **TREND_STEP** (fail-OPEN, unmapped) both live-negative | Live and losing | **RULE** — Michael: keep, cap, or retire | GHOST −$177.50 live / −$532.22 shadow; TREND_STEP −$197.50 live / −$810 shadow | **−$375** combined live | Michael |
| 15 | Playbook **fail-OPEN**: 18 of 32 emitted pattern names are unmapped → `Decision("FULL")` | Silent full authorization | **FIX** — flip the default to `REDUCED` and log `unmapped(...)` at WARNING | `TREND_STEP`, all `OPENING_*`, `EDGE_FADE`, `RE_PULLBACK`, `HLST` bypass the day-type matrix entirely | The two worst live patterns (TREND_STEP, OPENING_DRIVE) are both unmapped | CC → Michael |
| 16 | `v9_bars_tick_reversal` frozen 51 days while `FiveMinAggregator` + `ReversalBarHandler` subscribe to `tick_reversal_15` | Frozen input to a live aggregator | **FIX** — restore the write or drop the subscription | Post-restart the aggregator has no DB history to rehydrate from | 0 observed | CC |
| 17 | `v9_bars_stacked_imbalance` = **0 rows, ever**, while Sierra exports and the bridge pushes | Ingest never worked | **RETIRE** — drop the stream + table | Pure waste in the bridge loop | 0 | CC |
| 18 | 11 empty tables + `v9_tpo_bars` (2023) + `v9_day_type_shadow_transitions` (06-22) + `v9_reversal_enrichment` (1 row) + 5 `*_bak_*` tables | Schema debris | **RETIRE** — one migration, drop all 20 | 20 of 51 tables (39%) carry no live meaning; they make every "is this table the source of truth?" question expensive | 0 | CC |
| 19 | Panel shows **HFE** (killed 06-24) and `BuildTreeView.tsx:826-828` shows **GB50 / RB100 / RB50** (never existed); hides `TREND_STEP`, `OPENING_*`, `CONFLUENCE_RI_ZLR` | UI lies both ways | **FIX** — regenerate the panel list from the live detector registry | Michael reads this panel to decide what is armed | 0 | CC |
| 20 | **TT** (0 signals in 30d, last 07-21), **TLB** (1 signal in 30d, 0 clean decisions ever, 0 live trades ever), **BULL_FLAG_LONG** (0 live ever, shadow −$405.62), `INVERSE_HNS_LONG` / `HNS_TOP_SHORT` / `DOUBLE_TOP_AA_SHORT` (0 live ever) | Detectors that produce nothing | **RETIRE** the detector or **REVIVE** the spec — six patterns, one decision each | Six of the 19 panel rows are decoration. `HNS_TOP_SHORT`'s last setup carries ts `1970-01-01` (epoch bug) | BULL_FLAG shadow **−$405.62** | Michael |
| 21 | `EDGE_FADE_V1` unset; two replays NO-GO (−14.5pt, −20.0pt) — root cause is balance-day identification, not the fade logic | OFF, correctly | **LEAVE** — do not touch until the classifier's balance-day labelling is fixed | Ruled by Michael 08-02; re-asking would violate the one-time-ruling rule | Detection gap valued at $1,550 in DEV_PLAN 02.08 | — |
| 22 | `S2_REQUIRE_COT_AMT`, `LAYER0_CHOP_GATE`, `S2_CHOPPINESS_GATE`, `HFE_DISABLED`, `FOOTPRINT_DISABLED`, `S3_MUTE`, `STALL_EXIT`/`OPPOSITE_EXIT_V1` | Standing decisions, all verified still at their ruled values | **LEAVE** | Verified this audit: `chop_searching`'s 46 blocks in 30d belong **only** to the fixture pattern `STRATEGIC`; HFE's 396 feed rows are **100% synthetic** (2 distinct prices). All standing gates are honestly off | HFE disable = **+$2,987** avoided | — |
| 23 | `OPENING_WINDOWS_V1=1` with zero code references; consumer gated by `OPENING_DRIVE_EXHAUSTION_VETO_V1=0` | Phantom flag | **RETIRE** — remove from `.env` + `RULED_FLAGS.yaml`, or wire it | A ruled-ON flag with no `os.getenv` anywhere | 0 | CC |
| 24 | `FIXED_CONTRACTS_2/3/4/5` all `0` behind the `_6` early-return | Superseded ladder | **RETIRE** — collapse to one `CONTRACTS_N` integer | A future `FIXED_CONTRACTS_4=1` would be a silent no-op — the exact class of bug this audit exists to kill | 0 today | CC |
| 25 | `v9_bars_cumulative_delta` — the reported 08-18 freeze | **RESOLVED** | **LEAVE** (one watch item: 08-20 has **178** rows = a duplicated day) | 89–90 rows/day, 08-13 → 08-21, RTH 08:35–15:55 CT. Not frozen | 0 | — |

### Section counts

| Section | Audited | Alive / healthy | Dead, inert, or frozen |
|---|---|---|---|
| **A · Systems** | 7 (S8/S9 confirmed non-existent) | 4 alive (S1, S2, S4, S6) + 2 advisory-only (S5, S7) | 1 inert (S3) + **6 system-level dead-wirings** (A-1…A-6) |
| **B · Patterns** | 32 identities | 13 have ever produced a live trade | **19 never have** · 8 provably dead-wired (HLST×2, RE_PULLBACK×2, VEGAS, FAMIR, HFE, EDGE_FADE×2) |
| **C · Flags** | 195 ruled (146 ON / 28 OFF) + 342 indexed | `flag_guard` = 0 mismatches | **5 inert-while-ON** · **5 contradictory pairs** · **10 OFF-and-superseded** · **27 unobservable** · 4 index false-negatives |
| **D · Streams** | 51 tables + 20 exports + 1 SQLite + 1 JSONL feed | 8 healthy | **3 frozen** (tick_reversal, 30min_woodies, footprint) · **1 never-ingested** · **3 orphan writers** · **20 empty/fossil/backup tables** · **1 polluted feed** |

---

*Audit performed read-only 2026-08-22 by cowork-dev. No code, flag, `.env`, or service was
modified. Every §A–§D row is reproducible from E1–E7 above.*
