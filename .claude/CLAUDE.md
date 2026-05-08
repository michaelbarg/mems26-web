# MEMS26 — Claude Code Operating Instructions

## Project Context

MEMS26 is a real-time MES futures trading system. See root `CLAUDE.md` for full architecture.

## CC Permission Tiers

### Tier 0 — Auto-Allowed (no confirmation needed)
- **Read**: Any file in the repo (except `.env*`)
- **Search**: Glob, Grep across entire repo
- **Edit/Write**: `tools/**`, `docs/**`, `.claude/**`, `MEMS26_FIRST.md`
- **Git**: status, log, diff, add, commit, branch, checkout
- **Run**: Python/bash scripts under `tools/`
- **Shell**: ls, mkdir, cat, python3 -c (validation)

### Tier 1 — Requires Confirmation
- **Edit/Write**: Any file not in Tier 0 scope
- **Git**: Operations not listed in Tier 0

### Tier 2 — Denied (never attempt)
- **Push/Force**: `git push`, `git push --force`
- **Merge/Reset**: `git merge`, `git reset --hard`
- **Destructive**: `rm -rf`
- **Install**: `pip install`, `npm install`, `brew install`
- **Secrets**: Read/write any `.env` file
- **Production code**: `app/`, `backend/`, `bridge/`, `frontend/`, `sc_study/`

## Operating Rules

1. **Never read or write `.env` files** — secrets are managed by Michael only
2. **Never push** — all pushes are manual by Michael after review
3. **Never touch production code** — `app/`, `backend/`, `bridge/`, `frontend/`, `sc_study/`
4. **Never install packages** — no pip, npm, or brew
5. **Commit freely** in `tools/` and `docs/` scope — these are safe
6. **Ask before deciding** — if a task requires architectural decisions not documented in specs, write a `BLOCKED.md` instead of guessing
7. **Hebrew is OK** — Michael writes notes and specs in Hebrew. Preserve Hebrew text as-is.
8. **LaunchD jobs** — create plist files but NEVER install them. Michael installs manually.
9. **Test with --dry-run** — never run backup/restore scripts for real without explicit approval

## Decision Log

All significant decisions are tracked in `MEMS26_FIRST.md` using the D-XXX schema.

## Branch Strategy

- `main` — production (auto-deploys to Netlify + Render)
- `feature/*` — development branches
- Never force-push. Never push to main directly from CC.
