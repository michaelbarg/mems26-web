# CC — Run the replay/brain-view tool on the Mac (produce real data) · 2026-06-22

**Owner:** Cowork (built the tool, read-only) → CC (run it against the live DB on the Mac).
**Risk:** none to trading — this is a READ-ONLY viewer. SELECT-only, no logic changes.

## Context (read first)
Cowork built a per-day replay/brain-view tool. The files are in `tools/` in the working tree at
`/Users/michael/Downloads/mems26_web_git`, **uncommitted**. Cowork's VM can't reach the DB, so the real
volume / POC/VAH/VAL / CVD / per-bar day-type are still placeholders — only a Mac run fills them.
- `tools/export_replay_data.py` — DB→JSON exporter (SELECT-only, localhost-guarded, columns pinned vs ORM models).
- `tools/replay_brain_view.py` — JSON→HTML renderer (stdlib + lightweight-charts CDN).
Read `docs/handoff/SESSION_HANDOFF_2026-06-22.md`, `docs/SOURCE_OF_TRUTH.md`, and
`docs/handoff/CC_HANDOFF_CONTRACT.md` before running.

## Task
1. From the repo root, in the backend's Python env (psycopg2 + `DATABASE_URL=postgresql://localhost/mems26`),
   run for these dates — 06-09 validates vs Cowork's demo; **06-16 is the calibration target** (clean
   down day the brain missed); 06-22 is today:
   ```bash
   cd /Users/michael/Downloads/mems26_web_git
   for d in 2026-06-09 2026-06-16 2026-06-19 2026-06-22; do
     python3 tools/export_replay_data.py --date $d && \
     python3 tools/replay_brain_view.py --date $d
   done
   ```
2. **SELECT-only.** Do NOT write to the DB; do NOT touch any `backend/` or `config/` trading logic. If a
   pinned column name doesn't match the live schema, fix it in the exporter (smallest change) and note it.
3. **Do NOT start services.** If the backend is already up on `:8000`, the exporter pulls the canonical
   per-bar 7-type day-type from `/api/v9/day_type/classify_replay`; if not, it falls back automatically
   (`v9_day_type_state` → trade-stamped). Don't start it just for this.
4. **Verify (Rule 5) — paste raw output per date:** bars count, the levels (IBH/IBL/POC/VAH/VAL values),
   CVD point count, `day_type` + `day_type_source`, trades count, and that the HTML's synthetic banner is OFF.
5. **Sanity vs source-of-truth:** confirm exported POC/VAH/VAL equal `v9_tpo_sessions` for that date
   (canonical levels), and bar count ≈ expected RTH 5-min count. Flag any date where `v9_bars_5min` gapped
   (CVD missing) — that's known feed bug #0.

## Report (per the contract)
A short table — date · bars · IBH/IBL/POC/VAH/VAL · cvd-pts · day_type(source) · trades · banner-off? —
plus a **NOT-DONE** section: any date that failed/gapped, any column you had to fix. Optionally commit the
three `tools/*.py` scripts (gitignore the generated `replay_data_*.json` / `replay_*.html`). Don't claim
success without the pasted raw output.
