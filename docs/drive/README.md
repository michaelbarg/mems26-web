# MEMS26 — Google Drive mirror

**Agent:** [`docs/handoff/agents/AGENT_DRIVE_SYNC.md`](../handoff/agents/AGENT_DRIVE_SYNC.md)  
**Manifest:** [`DRIVE_SYNC_MANIFEST.yaml`](./DRIVE_SYNC_MANIFEST.yaml)  
**Script:** [`scripts/drive_sync_upload.py`](../../scripts/drive_sync_upload.py)

## Purpose

Repo markdown under `docs/` is the **write source**. Drive holds **always-current copies** for Michael, CC, and agents without local repo access.

## One-time setup (Michael)

1. In Google Drive, create folder: **MEMS26_Repo_Mirror** (under your existing MEMS26 project tree).
2. Copy the folder ID from the URL:  
   `https://drive.google.com/drive/folders/<FOLDER_ID>`
3. Add to `.env` (do not commit):

```bash
MEMS26_DRIVE_MIRROR_FOLDER_ID=<folder_id>
# Optional — service account JSON path:
# MEMS26_DRIVE_SA_JSON=/Users/michael/.config/mems26/drive_service_account.json
```

4. OAuth (first run only):

```bash
cd /Users/michael/Downloads/mems26_web_git
python3 scripts/drive_sync_upload.py --auth
```

Opens browser; token saved to `~/.config/mems26/drive_token.json` (mode 600).

## Commands

```bash
python3 scripts/drive_sync_upload.py --dry-run   # plan only
python3 scripts/drive_sync_upload.py             # changed files
python3 scripts/drive_sync_upload.py --all       # full manifest
```

## CC / cloud agent

Paste the block from **AGENT_DRIVE_SYNC.md** § Handoff phrase.  
CC should run after every wave and post `docs/reports/P30_DRIVE_SYNC_*.md`.

## State files (gitignored)

- `docs/drive/.sync_state.json` — file SHA → Drive file ID
- `docs/drive/.sync_log.jsonl` — append-only run log
