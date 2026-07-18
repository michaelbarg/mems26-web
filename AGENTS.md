# AGENTS.md

The primary agent guardrails for this repo live in `CLAUDE.md` (read it first —
it covers trading-risk rules, standing decisions, source-of-truth discipline,
and the codebase index protocol). This file adds only environment/run notes for
Cursor Cloud agents.

## Cursor Cloud specific instructions

This repo is normally a **Mac-hosted local trading stack** (see `docs/ENVIRONMENT.md`).
On the Cursor Cloud VM it runs on **Linux** with three runnable services; the
Sierra Chart DLL + live market feed are **not runnable here** (no Sierra/CrossOver),
so there is no live tick/bar data unless you inject it yourself.

### What the update script already does (on VM startup)
Installs Python deps (`requirements.txt` **plus `pytz`**, which the backend imports
but is missing from `requirements.txt`) and frontend deps (`npm install` in
`frontend/v9`). It does **not** start any service or database — do that manually.

### Services & how to run them (dev mode)
- **PostgreSQL 16** is the canonical DB (`postgresql://localhost/mems26`, no
  password — localhost `trust` auth is configured in `pg_hba.conf`; role `ubuntu`
  owns DB `mems26`). It is installed but **not auto-started**. Start it each session:
  `sudo pg_ctlcluster 16 main start`. First-time table creation: `bash scripts/db_init.sh`.
- **Backend** (FastAPI, port 8000): `python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`.
  `backend/main.py` auto-loads the root `.env` via its own stdlib loader, so you do
  **not** need to `source .env` first (env still wins if you do).
- **Frontend** (Next.js 16, port 3000): `cd frontend/v9 && npm run dev`.
  Note `frontend/v9/AGENTS.md`: this is a newer Next.js with breaking changes.
- Check `127.0.0.1:3000` / `127.0.0.1:8000` for existing listeners before starting.
- **Do not use `scripts/start_all.sh` on the cloud VM** — it hardcodes a macOS
  path (`/Users/michael/...`) and `screen`. Run the three commands above instead.

### Env files (gitignored — not recreated by the update script)
Root `.env` and `frontend/v9/.env.local` must exist. If missing, recreate from
`install/env.template`: set `DATABASE_URL=postgresql://localhost/mems26`,
`CLOUD_URL=http://localhost:8000`, `BRIDGE_TOKEN=michael-mems26-2026`,
`V9_EXPORT_DIR=/home/ubuntu/SierraChart_Data/v9_export`, plus the trading-flag
baseline from the template. Frontend `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000`,
`NEXT_PUBLIC_WS_URL=ws://localhost:8000`, `NEXT_PUBLIC_BRIDGE_TOKEN=michael-mems26-2026`.

### Ingesting data without Sierra (for manual testing)
POST bars straight to the bridge endpoint the same way the bridge would, e.g.
`POST /api/v9/bars/5min` with header `Authorization: Bearer $BRIDGE_TOKEN` and a
JSON list of `{ts,symbol,o,h,l,c,vol}`. Ingest guards to respect: bars must be
within RTH 09:30–16:00 ET, not in the future, `vol<=100000`, and (for fresh bars)
within `MAX_STALE_HOURS` (24h). Ingested bars appear via `/api/v9/chart/bars5min`
and on the dashboard chart. The dashboard's "WS DISCONNECTED"/price panel stays
idle without a live price stream — that is expected here (the WS transport itself
works; `/api/v9/ws/status` shows connected clients).

### Tests & lint
- Run pytest in a **clean env with only `BRIDGE_TOKEN` set** — do NOT `source .env`
  into the test shell, because the trading-flag exports flip default-OFF behavior
  and cause ~200 false failures. Example:
  `env -i HOME="$HOME" PATH="$PATH" BRIDGE_TOKEN=michael-mems26-2026 python3 -m pytest tests/ -q`.
- ~200 full-suite failures are a **pre-existing test-isolation issue** on this
  branch (files pass in isolation, fail in the full run from leaked global state),
  not an environment problem — CLAUDE.md tracks this as a known residual. ~3500 pass.
- Frontend `npm run lint` runs but has pre-existing `no-explicit-any` errors.
