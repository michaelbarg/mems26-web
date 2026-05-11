# MEMS26 RUNBOOK

## Prompt 1: Foundation Layer (Event Bus + Schema + live_price)

### Start / Stop

| Component | Start Command | Stop |
|-----------|--------------|------|
| Backend (FastAPI) | `cd backend && uvicorn backend.main:app --reload --port 8000` | Ctrl+C |
| Bridge | `cd bridge && python json_bridge.py` | Ctrl+C |
| Frontend (Next.js) | `cd frontend/v9 && npm run dev` | Ctrl+C |
| Sierra Chart DLL | Re-add Study in Sierra Chart | Remove Study |

### Verify Pipeline

```bash
# 1. Check live_price.json is being written
ls -la ~/SierraChart_Data/v9_export/live_price.json

# 2. Check Event Bus has price ticks (Upstash)
# Via bridge logs: look for "price.tick" events

# 3. Check WebSocket endpoint
# wscat -c ws://localhost:8000/ws/v9/price

# 4. Check frontend console
# Open http://localhost:3000, DevTools console shows price.tick events
```

### Troubleshooting

| Symptom | Check |
|---------|-------|
| No live_price.json | Sierra Chart study not loaded, or export dir wrong |
| Bridge not publishing | Check .env UPSTASH_REDIS_REST_URL/TOKEN |
| WS not receiving | Backend not running, or Redis pub/sub down |
| Frontend blank | Check NEXT_PUBLIC_WS_URL in frontend/.env.local |

---
*Filled per prompt. Skeleton created Prompt 1.*
