# P30.10 — Woodies 5m CCI Panel

**Date:** 2026-05-19  
**Status:** **GREEN** (MVP panel)  
**Replay head (context):** `2026-05-18 10:30:00 ET`

---

## Delivered

| Layer | Item |
|-------|------|
| API | `GET /api/v9/woodies/chart?limit=30` — reads Sierra `woodies_5min.json` |
| Frontend | `WoodiesCciPanel.tsx` — bottom-left on 5m chart (CCI-14 black, TCCI yellow, histogram by trend) |
| Tests | `tests/v9/api/test_woodies_chart_routes.py` (3 passed) |
| Lens | Woodies → Chart tab points to panel |

## Bridge (cockpit-minimal)

```bash
cd bridge && CLOUD_URL=http://localhost:8000 V9_SKIP_HISTORY=1 V9_DISABLE_WATCHDOG=1 \
  python3 json_bridge.py --cockpit-minimal
```

(`bars_5min` + `woodies_5min` only — not P30.11 full bridge.)

## UAT (2026-05-19 live)

```
GET /api/v9/woodies/chart?limit=30 → 30/30, bad=0, 25ms, source=sierra_woodies_5min_json
Browser: Woodies CCI panel visible, title [CCI:-143.95] matches API
pytest: test_woodies_chart_routes + bridge Woodies5Min PASS
```

## Deferred (not blocking GREEN)

- Full design spec §5.3 fidelity (480×360, data column, ProjHi/Lo, 9LE badge)
- Bridge in `--bars-5min-only` preset (use `--streams=` above)
