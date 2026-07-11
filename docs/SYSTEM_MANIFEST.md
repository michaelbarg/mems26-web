# MEMS26 System Manifest — the index of everything + the change-safety protocol

_The single map of every surface in the system: what is version-controlled, what lives
**outside** git (and therefore needs snapshotting), how to back up / roll back / verify.
Created 2026-06-26 after the Wine-rename feed incident exposed that the riskiest surfaces
(the deployed DLL) had no rollback point. Keep this current when a surface is added/moved._

## 0. Change-safety protocol (MANDATORY — every agent: Cowork, CC, Cursor)
**Before changing ANY out-of-git surface (DLL deploy, `.env` edit, LaunchAgent change):**
```
scripts/mems26_snapshot.sh "why-label"      # snapshots DLL+.env+LaunchAgents+git HEAD → ~/mems26_snapshots/
```
Then make the change. To roll back: `scripts/mems26_restore.sh <snapshot-dir>` (dry-run; add
`--confirm` to apply). To check the whole system is consistent: `scripts/mems26_verify.sh`.
The DLL deploy script auto-snapshots first (`build_monolithic_cpp.sh --deploy`), but run the
snapshot manually before `.env` / LaunchAgent / Sierra-Input changes too. In-repo code is
covered by git (commit before changing); this protocol is for the surfaces git does NOT track.

## 1. Version-controlled (git) — the existing indexes (source of truth for code)
| Index | Path | What it maps |
|-------|------|--------------|
| Code locator | `SYSTEM_INDEX.md` + `*/_INDEX.md` | every dir/file purpose + orphans (`scripts/gen_index.py`) |
| Source-of-truth | `docs/SOURCE_OF_TRUTH.md` | which data source is canonical-LIVE per signal (bars/day-type/levels/trades) |
| Flags | `docs/FLAG_INDEX.md` | every behavior/trading flag state+default+file:line (`scripts/gen_flag_index.py`, `--check`) |
| Issues | `docs/MEMS26_ISSUES_REGISTER.md` | open/closed issues (I-NN) |
| Status / roadmap | `docs/plans/STATUS_BOARD.md` · `docs/plans/ROADMAP_TO_LIVE.html` | source-of-record log + at-a-glance to-LIVE |
| Guardrails | `CLAUDE.md` · `.cursor/rules/mems26-pre-live-protocol.mdc` | standing decisions + pre-LIVE discipline |
Regenerate after structural/flag changes: `python3 scripts/gen_index.py` · `python3 scripts/gen_flag_index.py`.

## 2. OUT-OF-GIT surfaces — what actually runs (these need snapshots)
| Surface | Live location | Built/managed by | Snapshotted? |
|---------|---------------|------------------|--------------|
| **DLL source (monolith)** | `~/SierraChart{,2}/ACS_Source/MES_AI_DataExport.cpp` | `scripts/build_monolithic_cpp.sh` merges `sc_study/{v9_types.h,v9_exports.h,v9_woodies_export.h,MES_AI_DataExport.cpp}` → `sc_study/MES_AI_DataExport_merged.cpp` → deploys | ✅ snapshot |
| **DLL binary (compiled)** | `~/SierraChart{,2}/Data/MES_AI_DataExport_64.dll` | Sierra "Remote Build" (manual, in Sierra UI) | ✅ snapshot |
| **.env (live flags)** | `<repo>/.env` (gitignored) | hand-edited; loaded by `backend/env_loader.py` (Python) at boot | ✅ snapshot |
| **LaunchAgents** | `~/Library/LaunchAgents/com.mems26.{backend,bridge,export_promoter}.plist` | hand-installed; `launchctl load -w` | ✅ snapshot (repo copies in `scripts/launchagents/`) |
| **Sierra Inputs** | per-chart in Sierra UI | manual | ⚠️ documented below, not file-snapshotted |
| **Postgres DB** | `postgresql://localhost/mems26` | `scripts/db_backup.sh` / `db_restore.sh` | separate (DB has its own backup) |
| **Export feed** | `~/SierraChart_Data/v9_export/*.json` | DLL writes `.tmp`; **promoter** (`scripts/v9_export_promoter.py`) renames `.tmp→.json` (Wine workaround) | regenerated live (no snapshot needed) |

**Sierra study Input map** (set in Sierra UI, persists per chart): 0=ExportPath · 4=V9 Export Dir
(`~/SierraChart_Data/v9_export/`) · 7=V9 Lookback · 11=TradeCommandPath · 12=TradeResultPath ·
18=Woodies same-chart · 21=EnableOrderPlacement (**default 0/OFF**) · 22=TradeFillsPath.

## 3. Services + how to verify
| Service | Process / port | LaunchAgent | Check |
|---------|----------------|-------------|-------|
| Backend | `uvicorn backend.main:app` :8000 | `com.mems26.backend` | `curl :8000/health` → 200 |
| Bridge | `bridge/json_bridge.py` → localhost:8000 only | `com.mems26.bridge` | `pgrep -f json_bridge.py` |
| Export promoter | `scripts/v9_export_promoter.py` | `com.mems26.export_promoter` | feed `.json` ≤2s fresh |
| Activity feed | `scripts/trade_activity_feed.py` (per-account offset) | `com.mems26.activity_feed` | `/tmp/activity_feed.log` |
| Frontend | `next dev` :3000 | `com.mems26.frontend` | `curl :3000` → 200 |
One-shot: **`scripts/mems26_verify.sh`** checks all of the above + DLL-deployed↔repo + index drift + DB lag.

## 4. Backup / rollback / verify tooling (new 2026-06-26)
| Tool | Purpose |
|------|---------|
| `scripts/mems26_snapshot.sh "label"` | snapshot DLL(src+bin)+`.env`+LaunchAgents+git HEAD+checksums → `~/mems26_snapshots/<ts>_<label>/`, append `INDEX.md` |
| `scripts/mems26_restore.sh <dir> [--only dll\|env\|launchagents] [--confirm]` | roll a surface back (dry-run default; backs up current as `.pre-restore-*` before applying) |
| `scripts/mems26_verify.sh` | one-shot consistency: services · DLL deployed↔monolith · index drift · feed fresh · DB lag |
| `scripts/db_backup.sh` / `db_restore.sh` | Postgres backup/restore (pre-existing) |
Snapshots live in `~/mems26_snapshots/` (out of git — contains `.env` + binaries). Index: `~/mems26_snapshots/INDEX.md`.
