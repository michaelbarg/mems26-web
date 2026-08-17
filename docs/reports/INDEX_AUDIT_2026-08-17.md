# INDEX AUDIT — 2026-08-17

**Auditor:** Cowork subagent (read-only + generators only) · **Repo HEAD:** `17d1815a`
**Scope:** the four indexes CLAUDE.md declares mandatory — `SYSTEM_INDEX.md`/`_INDEX.md`,
`docs/SOURCE_OF_TRUTH.md`, `docs/FLAG_INDEX.md`, `docs/SYSTEM_MANIFEST.md`.
**Wrote:** nothing but this file + the regenerated index files (via the project's own
generators). **Committed:** nothing.

---

## VERDICT

🟡 **AMBER — no index is catastrophically wrong, but three of the four were stale or lying,
and two of the lies are in the safety-critical direction.** The generated code-index was
1 file short and 9 rows stale (now regenerated). `FLAG_INDEX.md` is byte-fresh but
**`--check` fails with 22 undocumented flags**, and it displays `SYSTEM6_AUTOCORRECT` as
🔴 OFF while the flag is provably acting — the exact defect that was suspected.
`SOURCE_OF_TRUTH.md` has not been touched in 54 days and mis-describes one table's
corruption status. `SYSTEM_MANIFEST.md` is a month stale and omits 4 of the 9 live
LaunchAgents and 3 of the indexes CLAUDE.md itself mandates.

One reported concern did **not** reproduce: `v9_bars_5min` is *not* dead — it is a
**windowed** feed (see §E-2). I nearly filed it as a 🔴; the raw data says otherwise.

---

## A. DRIFT — generator output

### A-1 `scripts/gen_index.py`

```
$ python3 scripts/gen_index.py
$ git diff --name-only | wc -l
     119
```

119 files changed, but **110 of those are the `*Auto-generated … · <date>*` header line only**.
The substantive drift is 1 missing file + 9 stale rows:

```
$ git diff -U0 | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' | grep -viE 'generated|last updated'
-**Scope:** [...] · 959 files · 118 directories
+**Scope:** [...] · 960 files · 118 directories
-- `backend/` — 610 files → `backend/_INDEX.md`
+- `backend/` — 611 files → `backend/_INDEX.md`
+| `contract_size.py` | ✅ 6 | 103 | 2026-08-16 | The one place that answers "how many contracts did Michael rule for?". |
-| `exit_verifier.py`  | ✅ 2  |  235 | ...   →  +| `exit_verifier.py`  | ✅ 2  |  259 |
-| `bar_level_detector.py` | ✅ 5 | 1026 | ... →  +| ... | 1049 |
-| `five_min_system.py` | ✅ 14 | 2295 | 2026-08-13 → +| ... | 2312 | 2026-08-16 |
-| `mobile_monitor.py` | ✅ 2 | 732 | ...    →  +| ... | 733 |
-| `quality_tier.py`  | ✅ 2 |  111 | 2026-07-15 → +| ... | 113 | 2026-08-16 |
-| `setup_emitter.py` | ✅ 4 |  229 | 2026-07-31 → +| ... | 222 | 2026-08-16 |
-| `sizing.py`        | ✅ 3 |  176 | 2026-07-18 → +| ... | 174 | 2026-08-16 |
-| `MES_AI_DataExport_merged.cpp` | — | 3912 | 2026-07-28 → +| ... | 3943 | 2026-08-16 |
```

| ISSUE | Severity | file:line | Smallest correct fix |
|---|---|---|---|
| `backend/v9/services/contract_size.py` (added today, 6 importers, sits on the sizing path) was **absent from the index** | 🟠 MED | `backend/v9/services/_INDEX.md` | Done — regenerated. Commit the refresh. |
| 9 rows carried stale LOC/date, incl. the DLL monolith (3912→3943) | 🟡 LOW | various `_INDEX.md` | Done — regenerated. |
| The index was last regenerated **before** today's T1–T7 session | 🟠 MED | — | Add `gen_index.py` to the end-of-session checklist (it is already in `mems26_verify.sh`). |

### A-2 `scripts/gen_flag_index.py`

```
$ python3 scripts/gen_flag_index.py --check > /tmp/fc.log 2>&1; echo "REAL_EXIT=$?"
REAL_EXIT=1
$ cat /tmp/fc.log
UNDOCUMENTED behavior flags (add to docs/FLAG_REGISTRY.yaml):
  BAR5_FAILOVER_SECONDS          EXIT_VERIFY_MAX_ATTEMPTS   EXIT_VERIFY_TIMEOUT_S
  EXIT_VERIFY_UNKNOWN_MAX_S      EXIT_VERIFY_V1             FIXED_CONTRACTS_6
  IB_BARS_VALIDATE_V1            LEG_EXEMPT_LSMA_FLAT_V1    MACHINE_TAG
  OPENING_BIAS_BAR_CLOSE_REFRESH_V1  OPENING_CONF_ENGINE_FUSE_V1
  OPENING_OR_ATR_SCALE_V1        OR_NARROW_MAX_PTS          PUSHOVER_API_TOKEN
  PUSHOVER_USER_KEY              RELEASE_LEG_EXEMPT_V1      SCALE_IN_ADD_CONTRACTS
  SCALE_IN_MAX_TOTAL             SCALE_IN_MIN_PROFIT_PTS    STEP_ZZ_REV
  TREND_LEG_CHASE_EXEMPT_V1      TREND_STEP_ENTRY_V1

$ python3 scripts/gen_flag_index.py
wrote docs/FLAG_INDEX.md — 332 flags (158 ON / 104 OFF / 7 not built); 22 undocumented, 5 not-in-code.
$ git diff --stat docs/FLAG_INDEX.md
(no output — file was already fresh)
```

`FLAG_INDEX.md` itself is **byte-current** (regeneration produced zero diff — good). But
`--check` **is failing right now**, i.e. the repo is in the state CLAUDE.md says must fail
loudly. 22 flags exist in code with no entry in `docs/FLAG_REGISTRY.yaml`, so their
"what it does / why" column is blank. Several are live trading-risk flags shipped in the
last week: `EXIT_VERIFY_V1` (+3 tuning knobs, today's T4), `SCALE_IN_*` (Michael's 08-13
ruling), `TREND_STEP_ENTRY_V1`, `FIXED_CONTRACTS_6`, `RELEASE_LEG_EXEMPT_V1`.

| ISSUE | Severity | file:line | Smallest correct fix |
|---|---|---|---|
| 22 behavior flags undocumented → `--check` exits 1 | 🟠 MED | `docs/FLAG_REGISTRY.yaml` | Add the 22 entries (semantics + ruling pointer). Highest-value first: `EXIT_VERIFY_V1`, `SCALE_IN_*`, `FIXED_CONTRACTS_6`, `TREND_STEP_ENTRY_V1`. |
| 5 registry flags no longer in code ("not-in-code") | 🟡 LOW | `docs/FLAG_REGISTRY.yaml` | Mark retired or delete. |
| `PUSHOVER_API_TOKEN` / `PUSHOVER_USER_KEY` / `MOBILE_ACCESS_KEY` / `NTFY_TOPIC` are **secrets** being scanned as behavior flags | 🟡 LOW | `scripts/gen_flag_index.py:56-75` (`INFRA` skip-list) | Add them to the infra skip-list — they are credentials, not flags, and `MOBILE_ACCESS_KEY`'s **value is printed in `FLAG_INDEX.md`** (`***MASKED — rotate***`), which is git-tracked. |

---

## B. CORRECTNESS — 19 entries spot-checked against the files

Method: `grep -rh "^| \`<file>\`" --include=_INDEX.md .` vs `head -6 <file>`.

| File | Indexed? | Purpose true? | Usage flag right? |
|---|---|---|---|
| `backend/main.py` | ✅ `✅ 5 · 1264` | ✅ verbatim docstring L1 | ⚠️ see §C |
| `backend/v9/gateway/trading_gateway.py` | ✅ | ✅ "TradingGateway — 3-mode trade routing…" matches L1 | ✅ |
| `backend/v9/systems/five_min/five_min_system.py` | ✅ `✅ 14 · 2312` | ✅ | ✅ |
| `backend/v9/systems/woodies/woodies_system.py` | ✅ `✅ 4 · 1550` | ✅ | ✅ |
| `backend/v9/services/bar_level_detector.py` | ✅ `✅ 5 · 1049` | ✅ | ✅ |
| `backend/v9/services/sierra_command.py` | ✅ `✅ 20 · 858` | ✅ verbatim | ✅ |
| `backend/v9/services/exit_verifier.py` (new) | ✅ `✅ 2 · 259` | ✅ "T4 — books close only after Sierra proves…" | ✅ |
| `backend/v9/services/contract_size.py` (new) | ✅ **only after regen** | ✅ | ✅ 6 |
| `backend/v9/services/sierra_position_reconciler.py` | ✅ `✅ 7 · 970` | ✅ | ✅ |
| `backend/v9/services/trade_manager/manager.py` | ✅ `✅ 19 · 1742` | ✅ | ✅ |
| `backend/v9/services/entry_guard.py` | ✅ | ✅ | ✅ |
| `backend/v9/db/session_guard.py` | ✅ | ✅ | ✅ |
| `backend/v9/services/trade_manager/scale_in.py` | ✅ | ✅ | ✅ |
| `backend/v9/systems/five_min/patterns/pullback_retest.py` | ✅ | ✅ | ✅ |
| `backend/v9/systems/five_min/step_scaled_ladder.py` | ✅ | ✅ | ✅ |
| `backend/v9/systems/trend_step/detector.py` | ✅ | ✅ | ✅ |
| `backend/v9/systems/five_min/trend_step_entry.py` | ✅ | ✅ | ✅ `⚠️ orphan?` — **verified true**, 0 importers |
| `backend/v9/tests/conftest.py` + 3 test files | ✅ | ✅ | ✅ `▶ entry/test` |
| **`sc_study/MES_AI_DataExport_merged.cpp`** | ✅ | 🔴 **FALSE** | — |

### B-1 🔴 The DLL monolith's one-line purpose is a mis-extracted comment

Index says:

```
| `MES_AI_DataExport_merged.cpp` | — | 3943 | 2026-08-16 | lookback — ignored, session-anchored now |
| `v9_exports.h`                 | —  |  707 | 2026-05-20 | lookback — ignored, session-anchored now |
```

The file's actual header:

```
$ head -3 sc_study/MES_AI_DataExport_merged.cpp
// MES_AI_DataExport_merged.cpp — v9.4.2 monolith for Sierra Chart remote build
// Generated 2026-07-21 09:10:12 by build_monolithic_cpp.sh
// CRITICAL: sierrachart.h + SCDLLName MUST be in first 10 lines
```

Root cause — `scripts/gen_index.py:61-67`:

```python
def cstyle_purpose(text):
    m = re.search(r"/\*+(.*?)\*/", text, re.S)     # ← searches the WHOLE file
```

The `/* */` branch runs **before** the `//` branch and is unanchored, so on a file whose
header uses `//` it walks past the header and grabs the first inline block comment anywhere
in the file. Proven:

```
$ python3 -c "import re; t=open('sc_study/MES_AI_DataExport_merged.cpp').read(); \
  m=re.search(r'/\*+(.*?)\*/', t, re.S); print('offset',m.start(),'line',t[:m.start()].count(chr(10))+1); print(repr(m.group(1)))"
offset 27487 line 788
'lookback — ignored, session-anchored now'

$ sed -n '787,789p' sc_study/MES_AI_DataExport_merged.cpp
inline std::string v9_cumulative_delta_to_json(
    SCStudyInterfaceRef sc, int /*lookback — ignored, session-anchored now*/)
```

A **commented-out parameter name on line 788** is the documented purpose of the most
safety-critical out-of-git artifact in the system.

| ISSUE | Severity | file:line | Smallest correct fix |
|---|---|---|---|
| `/* */` scan is unanchored and beats the `//` header | 🟠 MED | `scripts/gen_index.py:61-67` | Move the `//` loop **above** the `/* */` regex, or require `m.start()` to precede the first non-comment line. Then regenerate. |

### B-2 🟡 DLL provenance banner is 26 days older than the file

`MES_AI_DataExport_merged.cpp` says `// Generated 2026-07-21 09:10:12 by build_monolithic_cpp.sh`
but its mtime/index date is **2026-08-16** and LOC grew 3912→3943. Either the banner is not
refreshed on rebuild, or the merged artifact was hand-edited after generation. Per the
Change-Safety protocol the deployed DLL source must be traceable — worth one command to
settle (`git log -1 --format=%ci sc_study/MES_AI_DataExport_merged.cpp`) before the next deploy.

---

## C. THE KNOWN TRAP — `backend/main.py` vs `backend/v9/main.py`

**The original trap is extinct by deletion:**

```
$ ls -la backend/v9/main.py backend/main.py
ls: backend/v9/main.py: No such file or directory
-rw-r--r--@ 1 michael staff 76914 Aug 17 03:34 backend/main.py
```

**But the index does not positively identify the live entrypoint, and a near-identical
decoy now sits one directory over.** What actually runs:

```
$ ps aux | grep uvicorn
michael 34190 ... Python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
$ grep -n "uvicorn" ~/Library/LaunchAgents/com.mems26.backend.plist
16: ... exec .../Python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

What the index shows — note the importer counts:

```
backend/_INDEX.md:13
| `main.py` | ✅ 5 | 1264 | 2026-08-14 | MEMS26 unified backend — serves V8-compatible routes + V9 API. |

backend/v9/_INDEX.md:24
| `app.py`  | ✅ 8 |  388 | 2026-08-02 | MEMS26 V9 FastAPI application. |
```

Three problems, in order of danger:

1. **The decoy outranks the real thing.** `backend/v9/app.py` is described as "MEMS26 V9
   FastAPI application" with **8** importers; `backend/main.py` shows **5**. An agent
   scanning for "the FastAPI app" picks `app.py`. It is a real, importable `app`
   (`from backend.v9.app import app` appears in 9 test files) — it just is not what
   production serves. `backend/main.py:27` imports only `v9_router` + `init_event_dispatcher`
   from it. Same failure class as 2026-06-05, one file over.
2. **`main.py` is not marked as an entrypoint.** The `SYSTEM_INDEX.md` legend defines
   `▶ entry/test/stream`, but `backend/main.py` carries the ordinary `✅ 5`. Nowhere in
   `SYSTEM_INDEX.md` do the strings `main.py` or `entrypoint` appear at all.
3. **`main.py`'s own docstring is misleading post-Render.** L3 reads `Entry point for
   Render: web: uvicorn backend.main:app` — and Render is precisely what the Bridge
   Local-Only rule forbids. The index faithfully copies L1, so the index inherits nothing
   wrong here, but a reader who opens the file sees "Render".
4. **9 handoff docs still route readers to the deleted file**, one of them as a live
   instruction: `docs/handoff/DESKTOP_PKG0_PATHX_HANDOFF.md:18` — *"Wired in:
   `backend/v9/main.py` via `bar_router.subscribe()`"*.

| ISSUE | Severity | file:line | Smallest correct fix |
|---|---|---|---|
| Index does not mark `backend/main.py` as THE live entrypoint; `backend/v9/app.py` looks more central | 🔴 HIGH | `backend/_INDEX.md:13` · `backend/v9/_INDEX.md:24` · `SYSTEM_INDEX.md` | Add an "Entrypoints" block at the top of `SYSTEM_INDEX.md` (hand-authored section the generator preserves, or a constant in `gen_index.py`): `backend/main.py` = LIVE (`uvicorn backend.main:app`, per LaunchAgent) · `backend/v9/app.py` = router factory, test-only `app`. |
| `backend/v9/app.py` description is ambiguous | 🟠 MED | `backend/v9/app.py:1` | Change the module docstring's first line to `MEMS26 V9 router factory — mounted by backend/main.py; the bare app is test-only.` The generator then propagates it for free. |
| `main.py` docstring says "Entry point for Render" | 🟡 LOW | `backend/main.py:3` | Replace with the local uvicorn invocation. |
| Stale doc points at a deleted file | 🟡 LOW | `docs/handoff/DESKTOP_PKG0_PATHX_HANDOFF.md:18,86` | One-line correction to `backend/main.py`. |

---

## D. NEWLY-ADDED-BUT-UNINDEXED

```
$ git log --since=2026-08-10 --diff-filter=A --name-only --pretty=format: | sort -u
backend/v9/db/session_guard.py
backend/v9/services/contract_size.py
backend/v9/services/entry_guard.py
backend/v9/services/exit_verifier.py
backend/v9/services/trade_manager/scale_in.py
backend/v9/systems/five_min/patterns/pullback_retest.py
backend/v9/systems/five_min/step_scaled_ladder.py
backend/v9/systems/five_min/trend_step_entry.py
backend/v9/systems/trend_step/{__init__,detector}.py
backend/v9/tests/conftest.py + 12 test_*.py
(+ docs/, data_handoff/ — outside gen_index scope, correctly)
```

**After regeneration: all 22 in-scope files are indexed with accurate descriptions.**
Before regeneration, exactly one was missing: `contract_size.py` (§A-1). `exit_verifier.py`
*was* already present but with a stale LOC (235 vs 259).

Two notes:
- `backend/v9/systems/five_min/trend_step_entry.py` is flagged `⚠️ orphan?` — **the flag is
  correct**. Nothing imports it; the live implementation is `backend/v9/systems/trend_step/detector.py`
  ("H15 TREND_STEP_ENTRY_V1 (live port, 2026-08-14)"). Verified:
  `grep -rn "trend_step_entry" --include=*.py backend` returns only comment references.
  Recommend an explicit "SUPERSEDED by trend_step/detector.py" line in its docstring so the
  next agent does not re-wire the dead one.
- `gen_index.py` scope excludes `docs/`, `config/`, `tests/` (repo-root). That is by design,
  but it means `config/RULED_FLAGS.yaml` — the flag-ruling memory — is in **no** index.

---

## E. SOURCE_OF_TRUTH — verified against the live DB

`docs/SOURCE_OF_TRUTH.md:58` — *"Last updated 2026-06-24"* → **54 days stale.**

```
$ psql postgresql://localhost/mems26 -X -c "SELECT 'v9_bars_5min_woodies' t, max(ts)::text FROM v9_bars_5min_woodies
   UNION ALL SELECT 'v9_bars_5min', max(ts)::text FROM v9_bars_5min
   UNION ALL SELECT 'v9_bars_5min_continuous', max(ts)::text FROM v9_bars_5min_continuous;"
            t            |          max
-------------------------+------------------------
 v9_bars_5min_woodies    | 2026-08-17 03:45:00+03
 v9_bars_5min            | 2026-08-14 23:55:00+03
 v9_bars_5min_continuous | 2026-08-17 03:45:00+03
$ date
Mon Aug 17 03:48:35 IDT 2026
```

### E-1 ✅ `v9_bars_5min_woodies` is canonical and live — map is CORRECT

Fresh to 3 minutes ago, `trend_state` populated, close 7809.25 — matches the tick feed.

### E-2 ✅ `v9_bars_5min` — NOT stale. The alarming reading is a **windowed feed**, and the map does not say so.

`max(ts)` = Friday 23:55, which looks like a 2.6-day outage. It is not:

```
$ psql ... -c "SELECT min(ts)::text, max(ts)::text, count(*) FROM v9_bars_5min WHERE ts::date='2026-08-14';"
 2026-08-14 13:30:00+03 | 2026-08-14 23:55:00+03 | 126
$ psql ... -c "SELECT min(ts)::text, max(ts)::text, count(*) FROM v9_bars_5min_woodies WHERE ts::date='2026-08-14';"
 2026-08-14 01:00:00+03 | 2026-08-14 23:55:00+03 | 276
```

`v9_bars_5min` runs **13:30–23:55 IDT (05:30–15:55 CT), 126 bars/day**; woodies runs ~24h
(276 bars). At 03:48 IDT the day's window has simply not opened. Row counts confirm the
pattern is stable across the week (08-10…08-14: 126/126/117/89/126; 08-15,16 = weekend = 0).

The map's per-bar-delta claim also checks out (values alternate sign: -1487, -773, +1817,
-1145 — a running cumulative could not do that). **But** the map only says the table "can
STALL/GAP — always check the last bar is recent". Applied literally before 13:30 IDT, that
instruction yields a **false 🔴** on every pre-market check. The windowing is undocumented.

### E-3 🟠 `v9_bars_5min_continuous` — the map's stated facts are wrong; its verdict is still right

Map, line 17: *"`close` is GARBAGE (e.g. 12693/13456 — not a real price) … **3 corrupt rows
deleted**. Orphan model — do not wire new consumers."*

```
$ psql ... -c "SELECT count(*) total, count(*) FILTER (WHERE close>9000 OR close<3000) AS garbage, min(close), max(close) FROM v9_bars_5min_continuous;"
 total | garbage | min |  max
-------+---------+-----+-------
  8037 |     929 |   1 | 19413
$ psql ... -c "SELECT max(ts)::text FROM v9_bars_5min_continuous WHERE close>9000 OR close<3000;"
 2026-07-20 18:10:00+03
$ psql ... -c "SELECT ts, open, high, low, close FROM v9_bars_5min_continuous ORDER BY ts DESC LIMIT 2;"
 2026-08-17 03:45:00+03 | 7809.25 | 7809.75 | 7808.75 | 7809.25
 2026-08-17 03:30:00+03 | 7809.25 |    7810 |    7808 | 7809
```

Three corrections: (a) **929** corrupt rows are still in the table, not 3, and they were
**not deleted**; (b) corruption **stopped on 2026-07-20** — 4 clean weeks since; (c) the
table is **live and fresh** (03:45, prices identical to woodies). The 🔴 AVOID verdict should
stand — 11.6% of the table is poison, and `min(close)=1` would detonate any `min()`
aggregator (Source-of-Truth Rule 3) — but the map's stated reasoning is false and would not
survive a challenge, which is how warnings get overridden.

### E-4 Other sources — all consistent with a Friday close (no defect)

```
 v9_tpo_sessions      | 2026-08-15          v9_trades          | 2026-08-14 21:50:00+03
 v9_tpo_sessions CASH | 2026-08-14          v9_five_min_setups | 2026-08-14 17:55:00+03
 v9_day_type_state    | 2026-08-15 07:14:09
```

`docs/spec_authority/S1_ACTIVE_CANONICAL.md` (referenced at line 23) exists. The day-type
"🔴 DEAD — do not re-wire" endpoint row is unverified here (would need a live HTTP probe;
out of read-only scope for a trading machine).

| ISSUE | Severity | file:line | Smallest correct fix |
|---|---|---|---|
| Map 54 days stale; no entry for `exit_verifier`/`contract_size` era changes | 🟠 MED | `docs/SOURCE_OF_TRUTH.md:58` | Refresh + re-date. |
| `v9_bars_5min` windowing (13:30–23:55 IDT / 05:30–15:55 CT, 126 bars) undocumented → guaranteed false-🔴 pre-market | 🟠 MED | `docs/SOURCE_OF_TRUTH.md:15` | Append: *"windowed 05:30–15:55 CT (~126 bars/day) — empty outside the window is NORMAL; compare against `v9_bars_5min_woodies` (24h) before declaring a stall."* |
| "3 corrupt rows deleted" is false — 929 remain, `min(close)=1` | 🟠 MED | `docs/SOURCE_OF_TRUTH.md:17` | Replace with: *"929/8037 rows have garbage `close` (min 1, max 19413); corruption stopped 2026-07-20; table is live+fresh but the poison rows were never deleted — never `min()`/`max()` over it."* |

---

## F. FLAG_INDEX TRUTHFULNESS

### F-1 🔴 CONFIRMED — `SYSTEM6_AUTOCORRECT` is displayed OFF while it is provably ON

```
docs/FLAG_INDEX.md:168
| SYSTEM6_AUTOCORRECT | 🔴 OFF | `protective` (.env) | "0" | When ON … | OFF (built 2026-07-05). …
```

The code:

```
backend/v9/systems/system6_supervisor.py:291-296
    # 07-15 Michael decision 6/6 ("מערכת 6 תתחיל לעבוד", protective tier):
    # value "protective" enables applying the AUTO set — which is by
    return os.getenv("SYSTEM6_AUTOCORRECT", "0").lower() in ("1", "true", "yes", "protective")
```

The generator:

```
scripts/gen_flag_index.py:53
TRUTHY = {"1", "true", "yes", "on"}
scripts/gen_flag_index.py:177
    return val.strip().strip("\"'").lower() in TRUTHY
```

`"protective"` is truthy in the supervisor and falsy in the generator. The index therefore
states 🔴 OFF for a flag that CLAUDE.md explicitly calls **"ALLOWED + LIVE"** and warns
agents not to "restore" — and `backend/v9/services/trade_manager/manager.py:197` reasons
about live behaviour on the assumption it is on. An agent trusting `FLAG_INDEX.md` would
conclude System 6 auto-correction is dead and could "fix" it — writing to a live position.

### F-2 🟠 The same defect mislabels 12 more in-effect settings as 🔴 OFF

Every non-boolean `.env` value falls through `is_truthy` to OFF. Enumerated from the
generated index:

| Flag | `.env` value | Shown | Reality |
|---|---|---|---|
| `SYSTEM6_AUTOCORRECT` | `protective` | 🔴 OFF | **ON** (protective tier) |
| `RR_MIN_ROTATION` | `0.65` | 🔴 OFF | in-effect threshold |
| `T1_BANK_R` | `1.5` | 🔴 OFF | in-effect |
| `T0_TARGET_PTS` | `3.0` | 🔴 OFF | in-effect |
| `STOP_FLOOR_ROTATION_ATR` | `0.8` | 🔴 OFF | in-effect |
| `STOP_ANCHOR_OFFSET_TICKS_OVERRIDE` | `16` | 🔴 OFF | in-effect |
| `TREND_CCI_DIRECT_PT` | `50` | 🔴 OFF | in-effect |
| `S4_GRAY_RELABEL_CCI` | `100` | 🔴 OFF | in-effect |
| `CHASE_MIN_SESSION_BARS` | `8` | 🔴 OFF | in-effect |
| `OPENING_MIN_CONF` | `0.6` | 🔴 OFF | in-effect |
| `MARGIN_BUFFER_USD` | `50` | 🔴 OFF | in-effect |
| `MES_MARGIN_PER_CONTRACT` | `276.21` | 🔴 OFF | in-effect |
| `FEED_CONTENT_STALE_SECONDS` | `600` | 🔴 OFF | in-effect |
| `V9_CHART_TZ` | `America/Chicago` | 🔴 OFF | in-effect |

(The 11 flags rendered `🔢 param` — `RISK_DAILY_LOSS_CAP=800`, `DAYTYPE_CONFIRM_BARS=2`,
`EXTREME_CHASE_SCOPE=CONT` etc. — are handled correctly; the registry marks them as params.
So the fix pattern already exists in the tool.)

### F-3 🟡 Inline-comment values in `.env` — currently harmless, latent hazard

```
$ grep -nE '^[A-Z][A-Z0-9_]*=[^#]*#' .env
83:TREND_DIRECTION_GATE=0  # OFF Michael 2026-07-02 ~20:00 — …
89:REACTIVE_LOCATION_GATE=0  # OFF Michael 2026-07-02 ~20:00 — …
$ grep -nE '^[A-Z][A-Z0-9_]*=\s*(1|true|yes|on)\s+#' .env
(no matches)
```

`backend/env_loader.py` does not strip inline comments, so the runtime value is the literal
`"0  # OFF Michael…"`. Both flags evaluate OFF in code and OFF in the index — **correct by
luck**. Had either been `1  # …`, the runtime value would be `"1  # …"` ∉ `("1","true","yes")`
→ the flag would be **silently OFF while every human reader believes it is ON**. Zero such
lines today; this is a landmine, not a live bug.

| ISSUE | Severity | file:line | Smallest correct fix |
|---|---|---|---|
| `SYSTEM6_AUTOCORRECT=protective` shown 🔴 OFF | 🔴 HIGH | `scripts/gen_flag_index.py:53` · `docs/FLAG_INDEX.md:168` | Let a flag declare its truthy set in `FLAG_REGISTRY.yaml` (e.g. `extra_truthy: [protective]`), or read the accepted-values tuple out of the code site. Minimal stopgap: add `"protective"` to `TRUTHY` and regenerate. |
| 13 further in-effect settings shown 🔴 OFF | 🟠 MED | `scripts/gen_flag_index.py:177` | When the `.env` value is non-boolean, render `🔢 param` (+ value) instead of 🔴 OFF — the `param` path already exists; widen it to any non-boolean value rather than only registry-declared params. |
| `env_loader` keeps inline comments | 🟡 LOW | `backend/env_loader.py` | Strip trailing ` #…` on unquoted values; add a regression test. (Trading-risk-adjacent → verify before enabling.) |
| Secret values printed into a git-tracked index | 🟠 MED | `docs/FLAG_INDEX.md` (`MOBILE_ACCESS_KEY`, `NTFY_TOPIC`) | Add to the `INFRA` skip-list at `gen_flag_index.py:56-75`; rotate `MOBILE_ACCESS_KEY`. |

---

## G. SYSTEM_MANIFEST — the out-of-git map

```
$ ls -la docs/SYSTEM_MANIFEST.md
-rw-r--r--@ 1 michael staff 5381 Jul 16 20:44 docs/SYSTEM_MANIFEST.md      ← 32 days stale
```

### G-1 🟠 4 of 9 live LaunchAgents are unmapped

```
$ ls ~/Library/LaunchAgents/ | grep -i mems
com.mems26.activity_feed.plist    com.mems26.backend.plist
com.mems26.bridge.plist           com.mems26.eod_handoff.plist      ← not in manifest
com.mems26.export_promoter.plist  com.mems26.frontend.plist
com.mems26.mobile_relay.plist     ← not in manifest
com.mems26.startup_check.plist    ← not in manifest
com.mems26.update_check.plist     ← not in manifest
```

Mitigating: `scripts/mems26_snapshot.sh:52` copies `com.mems26.*.plist` by glob, so all 9
**are** snapshotted. The gap is documentation-only — but §3 "Services + how to verify" gives
no check command for four agents, one of which (`mobile_relay`) is Michael's phone alerting
path, and `phone_alert` dying silently already cost money on 08-12.

### G-2 🟠 Three mandated indexes are missing from the manifest's own index table

`§1` (lines 19-28) lists 6 indexes. Absent:
- `config/RULED_FLAGS.yaml` + `scripts/flag_guard.py` — CLAUDE.md calls these "the enforcing
  memory" for every ruled flag. `RULED_FLAGS.yaml` was modified **yesterday** (Aug 16 20:01);
  `flag_guard.py` has not been touched since Jul 16.
- `docs/handoff/LIVE_CHANNEL.md` — CLAUDE.md's **first** required read each session.
  484 KB, modified Aug 16 22:33.
- `docs/FLAG_REGISTRY.yaml` — the hand-authored input to `FLAG_INDEX.md`.

```
$ for k in RULED_FLAGS LIVE_CHANNEL MACHINE_TAG exit_verifier contract_size scale_in trend_step; do printf "%-16s " $k; grep -c $k docs/SYSTEM_MANIFEST.md; done
RULED_FLAGS      0
LIVE_CHANNEL     0
MACHINE_TAG      0
exit_verifier    0
contract_size    0
scale_in         0
trend_step       0
```

### G-3 🟠 The manifest describes a one-machine system; two machines trade

Per the 08-13 standing ruling both Macs may run LIVE in parallel, and `MACHINE_TAG` is now a
flag in the code (undocumented — see §A-2). Mac-2's `.env` and LaunchAgents are exactly the
"out-of-git surface needing a snapshot" this document exists to enumerate, and there is
already a `docs/handoff/env_reference/ENV_REFERENCE_MAC1_2026-08-13.txt`. The manifest's §2
and §3 tables have no machine column.

| ISSUE | Severity | file:line | Smallest correct fix |
|---|---|---|---|
| 4 LaunchAgents unmapped (incl. `mobile_relay`) | 🟠 MED | `docs/SYSTEM_MANIFEST.md:36,46-52` | Add the 4 rows + a check command each. |
| `RULED_FLAGS.yaml`/`flag_guard.py`/`LIVE_CHANNEL.md`/`FLAG_REGISTRY.yaml` absent from §1 | 🟠 MED | `docs/SYSTEM_MANIFEST.md:19-28` | Add 3 rows. |
| No Mac-2 surfaces despite parallel-LIVE ruling | 🟠 MED | `docs/SYSTEM_MANIFEST.md:30-39` | Add a machine column, or a §2b for Mac-2. |
| Stale 32 days | 🟡 LOW | — | Add a dated footer like the SoT map has. |

---

## WHAT AN AGENT WOULD GET WRONG TOMORROW IF IT TRUSTED THE INDEX AS-IS

1. **It would believe System 6 is not auto-correcting.** `FLAG_INDEX.md:168` says 🔴 OFF.
   CLAUDE.md says LIVE. Faced with that contradiction the agent either flips the flag to `1`
   — escalating from the `protective` tier to the full tier that CLAUDE.md gates behind
   EXIT-v2 — or "fixes" the supervisor. Both write to a live position. This is the single
   highest-consequence finding, and it is the one Michael's protocol was built to prevent:
   the index is supposed to be consulted *instead of* memory, and here memory is right and
   the index is wrong.

2. **It would read a dozen live risk parameters as disabled.** `RR_MIN_ROTATION=0.65`,
   `T1_BANK_R=1.5`, `STOP_FLOOR_ROTATION_ATR=0.8`, `MARGIN_BUFFER_USD=50` all render 🔴 OFF.
   An agent tuning entries or stops would conclude no floor is active and set one — silently
   changing a threshold Michael already ruled on. Same class as F-1, thirteen times over.

3. **It would open `backend/v9/app.py` believing it is the running server.** The old
   `backend/v9/main.py` trap is gone, but the index gives the decoy 8 importers to the real
   entrypoint's 5, describes it as "MEMS26 V9 FastAPI application", and never marks
   `backend/main.py` as live. The 2026-06-05 false "S1 not wired" diagnosis is reproducible
   today with a one-directory substitution.

4. **It would declare the bar feed dead at 07:00.** `v9_bars_5min` shows Friday's timestamp
   every morning until 13:30 IDT. The SoT map's own instruction — "always check the last bar
   is recent" — produces a 🔴 on a healthy system. A pre-open agent would raise a NO-GO, or
   worse, "fix" the ingest path.

5. **It would dismiss the `v9_bars_5min_continuous` warning as obsolete.** The map claims 3
   corrupt rows were deleted; a two-second query shows 929 still present and the table fresh
   and correct-looking. An agent that checks the claim finds it false and reasonably
   downgrades the whole warning — then wires a consumer over a column whose minimum is `1`.
   A false *justification* is more dangerous than no justification.

6. **It would not know four LaunchAgents exist**, including `mobile_relay` — the phone
   alerting path that already failed silently on 08-12. It is snapshotted by glob, so it is
   recoverable; it is simply invisible to anyone reading the manifest.

7. **It would treat `--check` green as proof.** It is currently red (exit 1, 22 flags),
   including today's `EXIT_VERIFY_V1`. Nothing in the workflow surfaces that.

---

### Files touched by this audit
- Regenerated (uncommitted): `SYSTEM_INDEX.md` + 118 `_INDEX.md` (`gen_index.py`);
  `docs/FLAG_INDEX.md` regenerated with **zero diff**.
- Created: this report.
- No flags changed, no services restarted, no source edited, `~/SierraChart_Data` untouched.
