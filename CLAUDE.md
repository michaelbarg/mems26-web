# MEMS26 Agent Guardrails

This repository controls the local MEMS26 trading stack. Treat post-reboot
stability settings as production safety controls.

## Sierra real-time data (**DONE** — Michael 2026-05-20)

Sierra DLL + time-axis fixes are **already shipped** (see inbox §2). §7a is
**anti-regression**: do not change `sc_study/`, bridge, or market-data routes
without reading `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` §7a and verifying
live exports under `~/SierraChart_Data/v9_export/`.

**Source of truth:** live values come from **Sierra Chart exports**, through
the bridge into the API/DB — not from backend or frontend synthesizing OHLC,
TPO, CVD, or Woodies study fields. Allowed: normalize, dedup, display TZ,
trading logic on ingested bars. Forbidden without explicit approval: inventing
`proj_*`, synthetic time grids, or rolling-window price levels when the DLL
omits them.

## Pre-LIVE Discipline (mandatory)

We are heading to LIVE futures trading. Apply minimum-mistakes discipline:

- **Diagnose first, fix second.** Verify the hypothesis with data
  (DB query, log read, probe) BEFORE touching code. Don't repeat
  P27.5d Option A — proposing a fix already in the code.
- **Read the current code** before proposing any change. No edits from
  memory.
- **Audit existing surfaces before building.** Before adding a component,
  endpoint, schema, report, or UI surface, search/read what already exists and
  classify it as KEEP / ADAPT / REPLACE / DEFER. Do not work blind or create a
  duplicate implementation when existing code can be adapted.
- **Smallest correct change.** No "while I'm here" refactors. Add a
  regression test for every bug fix.
- **Verify the four UAT axes** for any data/chart endpoint:
  1. Quality — the bad-data condition is gone (`bad_count=0`).
  2. Recency — `endpoint.latest_ts == MAX(ts) FROM DB`.
  3. Cardinality — `len(rows) == requested_limit`.
  4. Latency — response time under documented threshold.
  P27.5a shipped with only Quality verified and silently truncated
  the 20 newest bars. Never again.
- **No silent failures.** Replace `logger.debug` on push/connect
  errors with `logger.warning` (rate-limited). Surface drift early.
- **One thread at a time.** Finish + report before opening the next
  P-ID.
- **Update reports immediately** when state changes — do not let
  `docs/reports/PROMPT_*.md` lag behind reality.
- **Strategic stop and ask Michael** at phase gates, on plan
  contradictions, or before any change that affects trading logic
  or risk surface.

The Cursor agent's full protocol is in
`.cursor/rules/mems26-pre-live-protocol.mdc`. Same rules apply here.

## Bridge Local-Only Rule

- The bridge MUST push only to `http://localhost:8000`. Never to
  `mems26-web.onrender.com` or any other remote host.
- `CLOUD_URL` defaults to `http://localhost:8000` in
  `bridge/v9_streams/base_stream.py`, and the bridge **refuses to start** if
  `CLOUD_URL` is not `localhost` or `127.0.0.1`.
- The LaunchAgent (`~/Library/LaunchAgents/com.mems26.bridge.plist`) and
  `scripts/start_all.sh` both hard-export `CLOUD_URL=http://localhost:8000`.
  Do not change either back to a render/cloud URL.
- If you ever see `[<stream>] API push FAILED to https://...` in
  `/tmp/bridge.err.log`, stop the bridge and ask Michael — that means a
  config drift slipped through.

## LaunchAgent Stability

- Do not change `~/Library/LaunchAgents/com.mems26.bridge.plist` back to
  `KeepAlive=true`.
- The bridge LaunchAgent must use conditional KeepAlive:

```xml
<key>KeepAlive</key>
<dict>
    <key>SuccessfulExit</key>
    <false/>
</dict>
```

- The bridge LaunchAgent command must export:

```bash
export V9_DISABLE_WATCHDOG="${V9_DISABLE_WATCHDOG:-1}"
```

## Frontend Polling Floors (P30 Forensics — Michael approved)

Do NOT increase these intervals without Michael's explicit approval.
The backend is single-worker uvicorn; aggressive polling chokes it.
These values are the tested safe floor — fast enough for trading,
slow enough to keep health <100ms.

| Component | File | Interval | Reason |
|-----------|------|----------|--------|
| `useSystemStatePolling` | `V9Dashboard.tsx` | **5000ms** | Fires/ZLR need <5s visibility |
| `SoundProvider` | `SoundProvider.tsx` | **10000ms** | Fire ding must reach trader <10s |
| `useLivePricePoll` | `useLivePricePoll.ts` | **5000ms** | WS fallback only — skips when WS connected |
| `WoodiesCciPanel` | `WoodiesCciPanel.tsx` | **5000ms** | CCI chart updates on 5-min bars |
| `StreamHealthPanel` | `StreamHealthPanel.tsx` | **15000ms** | Diagnostic only |
| `Layer0Strip` | `Layer0Strip.tsx` | **15000ms** | Chop score changes slowly |
| `TopBar` heartbeat | `TopBar.tsx` | **15000ms** | Health indicator |
| `TradeHistoryStrip` | `TradeHistoryStrip.tsx` | **30000ms** | History, not real-time |

## Service Bring-Up

- Do not start MEMS26 services unless explicitly asked.
- Do not run `npm run dev`, `next dev`, or `scripts/start_all.sh` during a
  stability audit.
- Before starting services, check for existing listeners on `127.0.0.1:3000`
  and `127.0.0.1:8000` to avoid duplicate frontend/backend instances.

## Generated Files

- Do not commit Python bytecode (`*.pyc`) or `__pycache__/` files.
- If bytecode appears in git status, treat it as generated state unless the
  user explicitly asks to preserve it.

## Sierra DLL (CC maintenance)

- Canonical ops log: `docs/runbooks/SIERRA_DLL_OPS.md`
- Before editing: cross-check `docs/PROMPT_1_HOTFIX_REPORT.md`, `docs/ENVIRONMENT.md`, `docs/reports/PROMPT30_8_5MIN_JSON_EXPORT.md`, this handoff’s P30 sections.
- Deploy path: `sc_study/` → `./scripts/build_monolithic_cpp.sh --deploy` → `~/SierraChart/ACS_Source/MES_AI_DataExport.cpp` → Remote Build → reload study.
- Study **Input 4** (`V9 Export Directory`) persists per chart in Sierra UI — Mac path `/Users/michael/SierraChart_Data/v9_export/`.

## Reporting Workflow

- For every completed prompt, bug fix, UAT, or phase gate, ask Claude Code to
  prepare or update the relevant report before moving to the next task.
- Prefer Claude Code for structured reports because it is efficient at turning
  test output, diffs, and UAT evidence into concise handoff docs.
- The working agent should focus on implementation, verification, and deciding
  when to stop for strategic questions; report writing should be delegated to
  Claude Code whenever practical.
- Do not advance to the next P-ID until the report exists or Claude Code has
  explicitly said what is missing.
