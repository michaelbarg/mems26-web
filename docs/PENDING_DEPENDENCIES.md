# Frontend Pending Dependencies

Components that are built but awaiting backend/bridge data:

## AWAITING_DEPENDENCY: Bridge Fix (T1 — load_dotenv)

All real-time data depends on Bridge pushing to Redis. Until Bridge is fixed:
- All chart data uses mock fallback
- All sidebar tabs show placeholder/empty state
- System panels show "No active signal"

**Components affected:** ChartArea, VolumePanel, all tab contents, all system panels

## AWAITING_DEPENDENCY: V9 Backend Routes (T2 — Render deploy)

V9 API routes (`/api/v9/*`) not deployed on Render. Frontend REST calls return 404.

**Components affected:**
- `MarketTab` — StreamHealth polls `/api/v9/health/streams` (404)
- `ChartArea` — fetches from `/api/v9/bars/5min` (404 → mock fallback)
- All data loading in `api.ts`

## AWAITING_DEPENDENCY: WebSocket Server

WS endpoints (`/ws/v9/*`) not confirmed working. Frontend WSManager connects but may get no data.

**Components affected:** Real-time bar updates, level updates, trade events, signal events

## Status

| Component | Built | Data Source | Status |
|-----------|-------|-------------|--------|
| ChartArea | Yes | REST + WS + mock | Working (mock data) |
| VolumePanel | Yes | Store (from ChartArea) | Working (mock data) |
| TopBar | Yes | Store | Working |
| 9 Sidebar Tabs | Yes | Store + REST | Working (empty state) |
| 6 System Panels | Yes | Store | Working (no signal state) |
| TradesView | Yes | REST | Working (empty) |
| StreamHealth | Yes (in MarketTab) | REST polling | 404 until V9 routes deployed |
