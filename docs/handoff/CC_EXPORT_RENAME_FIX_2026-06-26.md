# CC Handoff — permanent fix for the Wine `.tmp→.json` promotion freeze (2026-06-26)

_Author: Cowork. Contract: `docs/handoff/CC_HANDOFF_CONTRACT.md`. Severity: P0 data-feed
(silent-staleness). A native sidecar is ALREADY LIVE and keeping the feed up 24/7 — this
handoff is the **source-level** fix so the DLL stops needing the sidecar. Do the DLL change
+ deploy **out of trading hours** (a DLL reload is what triggered the original freeze)._

## What happened (root cause, verified Rule 2/5)
Sierra runs under **CrossOver/Wine**. The DLL atomic-write helper
`v9_write_json` (`sc_study/v9_types.h:122`; mirrored in
`sc_study/MES_AI_DataExport_merged.cpp:126`) does:
```cpp
std::ofstream f(tmp_path); f << json; f.close();
return std::rename(tmp_path.c_str(), path.c_str()) == 0;   // <-- fails under Wine
```
**Wine's `rename()` can create a NEW file but cannot REPLACE an existing one** (Windows
MSVCRT semantics). So the first write of each `<name>.json` works; every promotion after
that fails → `<name>.json.tmp` stays fresh, `<name>.json` freezes. `live_price`/`mes_ai_data`
write directly (no `.tmp`) so the tick feed masks it. Empirically proven: delete the stale
`.json` → Sierra recreates it once (rename onto non-existent OK) → re-freezes next cycle
(rename onto existing FAILS); native macOS rename-over works; a fresh Wine PID still froze.

## The fix — replace `std::rename` with an atomic Win32 replace
In `v9_write_json`, swap the POSIX `std::rename` for the Win32 API that explicitly allows
replacing an existing target (works correctly under Wine):
```cpp
#include <windows.h>   // already available in ACSIL builds
// ... after writing + closing tmp_path:
if (MoveFileExA(tmp_path.c_str(), path.c_str(),
                MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
    return true;
}
// Fallback for non-Windows/native test builds:
std::remove(path.c_str());
return std::rename(tmp_path.c_str(), path.c_str()) == 0;
```
- `MOVEFILE_REPLACE_EXISTING` = atomically replace the existing `.json` (the missing capability).
- `MOVEFILE_WRITE_THROUGH` = don't return until the rename is flushed (durability).
- Keep the `.tmp` write exactly as-is — only the rename step changes. Smallest correct change.
- This preserves the torn-read protection the helper was added for (the consumer only ever
  sees a complete file, never a half-written one).

## Verify (paste raw, Rule 5) — out of trading hours
1. Build + deploy per `docs/runbooks/SIERRA_DLL_OPS.md`
   (`./scripts/build_monolithic_cpp.sh --deploy` → Remote Build → reload study). Do it during
   the CME maintenance break (17:00-18:00 ET) or a weekend so a reload can't hurt a live bar.
2. **Before** relying on it, TEMPORARILY stop the sidecar so you're testing the DLL alone:
   `launchctl unload -w ~/Library/LaunchAgents/com.mems26.export_promoter.plist`.
3. Watch `~/SierraChart_Data/v9_export/`: confirm `<name>.json` mtime + last-ts track
   `<name>.json.tmp` continuously for ≥10 min across at least one new 5-min bar (paste a
   sampled `stat -f %m` + last-ts table for `woodies_5min`/`5min`/`cumulative_delta`).
4. Confirm the dir mtime advances (= renames are landing) and NO `.json.tmp` is left newer
   than its `.json` by more than one bar.
5. **Re-enable the sidecar afterward** (`launchctl load -w …plist`) as belt-and-suspenders
   until ≥1 full session proves the DLL fix holds, then decide whether to retire it.

## NOT-DONE / guardrails
- Do NOT touch Pipeline-5 order-placement code here — this is purely the export write path.
- Do NOT reload the DLL during RTH. The sidecar already protects the feed, so there is no
  urgency to rush a trading-hours deploy.
- The sidecar (`scripts/v9_export_promoter.py`) is the safety net; leave it running until this
  DLL fix is verified over a full session.
