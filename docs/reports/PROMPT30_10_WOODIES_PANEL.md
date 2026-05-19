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

## Bridge (optional)

Panel does **not** require bridge (file read like TPO/CVD). For S4 system hydration:

```bash
cd bridge && CLOUD_URL=http://localhost:8000 V9_SKIP_HISTORY=1 \
  python3 json_bridge.py --streams=bars_5min,woodies_5min
```

## UAT

```bash
# After backend restart (new route)
curl -s "http://127.0.0.1:8000/api/v9/woodies/chart?limit=30" | python3 -m json.tool | head -25
```

Browser: `http://127.0.0.1:3000` → **5m** → teal panel bottom-left with CCI title.

## Deferred (not blocking GREEN)

- Full design spec §5.3 fidelity (480×360, data column, ProjHi/Lo, 9LE badge)
- Bridge in `--bars-5min-only` preset (use `--streams=` above)
