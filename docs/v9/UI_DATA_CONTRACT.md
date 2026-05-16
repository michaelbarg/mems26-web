# MEMS26 UI Data Contract

**Date:** 2026-05-16  
**Purpose:** Give the Cockpit UI and designer a stable data shape before LIVE.

## Modes

| Mode | UI meaning | Sierra |
|------|------------|--------|
| SHADOW | Recorded setup/trade only; used for system analysis | No orders |
| DEMO | Sierra Sim / demo command path | `trade_command.json` |
| LIVE | Real account command path | Explicit Michael approval only |

## Core Panels

### 1. System Status Strip

Endpoint source:
- `GET /api/v9/day_type/v9/current`
- `GET /api/v9/five_min/current`
- `GET /api/v9/footprint/current`
- `GET /api/v9/woodies/current`
- `GET /api/v9/tpo/current`
- `GET /api/v9/killzone/current`

Shape:

```json
{
  "system_id": 4,
  "name": "woodies",
  "role": "FIRING",
  "status": "READY|PENDING|BLOCKED|ERROR",
  "classification": "NO_SETUP|TACTICAL|STRATEGIC",
  "direction": "LONG|SHORT|NEUTRAL",
  "confidence": 0.82,
  "top_gap": "A4 touch-points pending"
}
```

### 2. Active Trade Card

Endpoint source:
- `GET /api/v9/gateway/status`
- `GET /api/v9/trades/active` (or current active trade endpoint)

Shape:

```json
{
  "trade_id": "abc123",
  "mode": "shadow|demo|live",
  "firing_system": 4,
  "direction": "LONG",
  "entry_price": 5250.0,
  "stop": 5247.0,
  "t1": 5253.0,
  "t2": 5256.0,
  "state": "OPEN|CLOSED|BLOCKED",
  "slot": {
    "demo_occupied": true,
    "live_occupied": false
  }
}
```

### 3. Reason Tree

Endpoint source:
- `GET /api/v9/woodies/fire`
- future equivalents for S2/S3

Shape:

```json
{
  "system": "woodies",
  "ready_to_route": true,
  "entry_classification_spec": "REACTIVE",
  "decision_tree": {
    "pre_fire": [
      {"stage_id": "A1", "status": "PASS", "message": "trend_state=BLUE"},
      {"stage_id": "A4", "status": "PENDING", "message": "touch-points not HTTP-wired yet"},
      {"stage_id": "A7", "status": "PASS", "message": "pre_fire OK"}
    ],
    "active_trade": [
      {"stage_id": "B1", "status": "DELEGATED", "owner": "trade_manager"}
    ],
    "failed_stages": []
  }
}
```

### 4. Designer Mock Trade

The designer can work from a mock object using the same shape as Active Trade
Card and Reason Tree. No Sierra, SHADOW, DEMO, or LIVE is required for visual
work.

## UI Readiness Gates

| Gate | Meaning |
|------|---------|
| UI-MOCK | Designer can work from mock JSON |
| UI-SHADOW | UI can show recorded setups/trades from DB |
| UI-DEMO | UI shows Sierra Sim command status |
| UI-LIVE | UI shows real account status (explicit Michael approval only) |

