# Agent: Drive-Sync (permanent role)

**Role:** `Drive-Sync-Agent` — **only** uploads/updates repo docs on Google Drive  
**Owner:** Claude Code (cloud terminal + Drive access) or Cursor Task with network  
**Schedule:** After every P30 wave, every doc commit batch, and **daily** during SHADOW soak  
**Authority:** `docs/drive/DRIVE_SYNC_MANIFEST.yaml`, `docs/drive/README.md`

---

## Mission

Keep a **live Drive mirror** of MEMS26 handoff/report/decision docs so Michael and CC always read the **same version** as the repo — without manual copy-paste.

**Repo is source of truth for content.** Drive is the **active reading surface** for humans and agents without repo access.

---

## Hard scope

| DO | DO NOT |
|----|--------|
| Upload/update files in manifest | Edit trading code, gateway, bridge, DLL |
| Create subfolders under mirror root | Delete Drive files without Michael OK |
| Write sync log + index doc on Drive | Push to `main` (D-067) |
| Report `UPLOADED` / `SKIPPED` / `FAILED` per file | Echo secrets or `.env` values |

---

## Preconditions (Michael one-time)

1. Create Drive folder **MEMS26_Repo_Mirror** (or use existing project folder).
2. Set folder ID in `.env` as `MEMS26_DRIVE_MIRROR_FOLDER_ID=...` (see `docs/drive/README.md`).
3. OAuth token at `~/.config/mems26/drive_token.json` **or** service account JSON path in `MEMS26_DRIVE_SA_JSON`.
4. CC credentials skill on Drive: `1gJzthhg7WKNUWtDOphNtV8RhrsXP4b02ICZOr8FXty4`

---

## Execution (preferred)

```bash
cd /Users/michael/Downloads/mems26_web_git

# Dry-run (no API calls if no token — prints plan)
python3 scripts/drive_sync_upload.py --dry-run

# Full sync (changed files only)
python3 scripts/drive_sync_upload.py

# Force all manifest paths
python3 scripts/drive_sync_upload.py --all
```

---

## Deliverables (every run)

| Output | Location |
|--------|----------|
| Sync report | `docs/reports/P30_DRIVE_SYNC_YYYYMMDD.md` |
| Machine log | `docs/drive/.sync_log.jsonl` (gitignored) |
| Drive index | Google Doc **`MEMS26 Repo Mirror Index`** in mirror root (create/update) |

### Report template

```markdown
# P30 Drive Sync — YYYY-MM-DD HH:MM

**Verdict:** PASS / PARTIAL / FAIL
**Folder ID:** … (last 6 chars only)
**Uploaded:** N · **Skipped:** N · **Failed:** N

| Path | Action | Drive file ID |
|------|--------|---------------|
| docs/reports/P30_ROAD_START_TO_LIVE.md | UPDATED | … |

## Failures
- …

## Next run
- Trigger: after Wave N / daily / Michael request
```

---

## Manifest groups (priority order)

1. **P30 active** — `docs/reports/P30_*`, `docs/decisions/D-08*.md`, all `docs/handoff/agents/WAVE_*`
2. **Handoff** — `docs/handoff/P30_*`, `docs/handoff/CC_*`, `docs/handoff/INVESTIGATE_*`, `docs/handoff/agents/AGENT_S*`
3. **Roadmap** — `P30_ROAD_*`, `P30_PRIORITY*`, `P30_MISSING*`
4. **PROMPT30 series** — `docs/reports/PROMPT30_*`, `docs/reports/PROMPT_P30_*`
5. **Spec authority** — `docs/spec_authority/*.{md,markdown,txt}`
6. **Shadow soak** — `docs/reports/shadow/*` (when present)

Full list: `docs/drive/DRIVE_SYNC_MANIFEST.yaml`

---

## “Always active” policy

| Trigger | Who |
|---------|-----|
| Michael says “sync Drive” | Drive-Sync-Agent immediately |
| End of Wave 0/1/2/3 report | Parent delegates this agent |
| CC end-of-day during SHADOW | CC runs script + posts summary to Slack optional |
| New `docs/decisions/D-*.md` | Sync within same session |

**Parent rule:** Any Cursor/CC session that creates/updates manifest docs → **append task**: “Drive-Sync-Agent: run sync.”

---

## Conversion rules

| Repo type | Drive format |
|-----------|--------------|
| `.md`, `.markdown` | Google Doc (editable) |
| `.txt` | Google Doc |
| `.docx` | Binary upload (native) |
| `.png` under `docs/handoff/assets/` | Image file (optional group `assets`) |

---

## Link-back to Master Index (optional)

After sync, add one row to Drive **Spec Registry** or **Master Index V2** § Repo Mirror:

`MEMS26 Repo Mirror Index` → `<Drive doc ID of index>`

Do not change locked spec bodies — index pointer only.

---

## Handoff phrase (paste to CC)

```text
TASK: Drive-Sync-Agent — full manifest upload per docs/handoff/agents/AGENT_DRIVE_SYNC.md
Run: python3 scripts/drive_sync_upload.py
Report: docs/reports/P30_DRIVE_SYNC_<today>.md
STOP on auth failure — ask Michael for MEMS26_DRIVE_MIRROR_FOLDER_ID + token setup.
```

---

*Permanent agent · pre-LIVE · 2026-05-20*
