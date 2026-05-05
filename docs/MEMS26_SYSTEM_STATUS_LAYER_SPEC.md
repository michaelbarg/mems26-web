# MEMS26 — System Status Layer Spec V1

**Version:** V1.0 — first complete spec
**Date:** 5 May 2026 EOD
**Status:** 📋 Spec ready → Phase 3.3 implementation
**Implementation target:** Phase 3.3 Day 1-2 (8-9 May)
**LIVE blocker:** Yes — required for LIVE 21/5

---

## 📑 Table of Contents

1. [Vision & Purpose](#1-vision)
2. [Architecture Overview](#2-arch)
3. [Status Banner (top bar)](#3-banner)
4. [Components Panel](#4-components)
5. [Auto-Dim Behavior](#5-auto-dim)
6. [Backend `/system/status` Endpoint](#6-endpoint)
7. [Component Thresholds](#7-thresholds)
8. [Frontend Implementation](#8-frontend)
9. [Failure Mode Catalog](#9-failures)
10. [Acceptance Criteria](#10-acceptance)

---

<a name="1-vision"></a>
## 1. Vision & Purpose

> **כשהמערכת חולה — אסור לסחור.**

V8.1.4 has no system-level health monitoring on the dashboard. If Bridge is dead, you find out only when no setups appear. If Backend is laggy, trades get queued. If DB writes fail silently, journal becomes corrupt.

**Status Layer purpose:**
1. Continuous health visibility on the trading screen
2. Block trade execution when any critical component fails
3. Auto-dim setup signals so user doesn't act on stale data
4. Loud alerts for partial degradation (data lag, etc.)

---

<a name="2-arch"></a>
## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  FRONTEND (blasttt.com — Next.js)                                │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  STATUS BANNER (top of dashboard, full width)              │ │
│  │  [🟢 ALL SYSTEMS GO] OR [🔴 SYSTEM DEGRADED]                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────┐                                    │
│  │  Components Panel       │  ← collapsible, default expanded   │
│  │  (left sidebar)         │                                    │
│  │                         │                                    │
│  │  Bridge       🟢        │                                    │
│  │  Backend      🟢        │                                    │
│  │  Sierra DLL   🟡        │  ← warning state                   │
│  │  Database     🟢        │                                    │
│  │  Redis        🟢        │                                    │
│  └─────────────────────────┘                                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Setup Signals Area (auto-dimmed if components fail)        │ │
│  │  [signals appear here, but greyed out when system unhealthy]│ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
              │
              │ polls every 5s
              ↓
┌──────────────────────────────────────────────────────────────────┐
│  BACKEND (mems26-web.onrender.com)                               │
│  GET /system/status → aggregate health JSON                      │
└──────────────────────────────────────────────────────────────────┘
              │
              │ checks
              ↓
┌──────────────────────────────────────────────────────────────────┐
│  COMPONENT CHECKS                                                │
│  • Bridge alive (last seen in Redis)                             │
│  • Backend alive (Render uptime)                                 │
│  • Sierra DLL alive (last JSON write)                            │
│  • Database connectivity (SELECT 1)                              │
│  • Redis connectivity (PING)                                     │
└──────────────────────────────────────────────────────────────────┘
```

---

<a name="3-banner"></a>
## 3. Status Banner (Top Bar)

### 3.1 Visual States

```
🟢 ALL SYSTEMS GO  
   ┌────────────────────────────────────────────────────────────────┐
   │ 🟢 ALL SYSTEMS GO • RTH • TREND_DAY 92% conf • Trades: 2/5     │
   └────────────────────────────────────────────────────────────────┘
   Background: dark green (#10B981 dim)
   
🟡 PARTIAL DEGRADATION
   ┌────────────────────────────────────────────────────────────────┐
   │ 🟡 DATA LAG: Bridge 8s old • Trading PAUSED until <3s          │
   └────────────────────────────────────────────────────────────────┘
   Background: dark amber (#F59E0B dim)
   
🔴 SYSTEM DEGRADED — DO NOT TRADE
   ┌────────────────────────────────────────────────────────────────┐
   │ 🔴 BRIDGE OFFLINE 47s • SIERRA DLL UNREACHABLE • TRADING HALTED│
   └────────────────────────────────────────────────────────────────┘
   Background: dark red (#DC2626 dim) — ANIMATED pulse
   PLUS: blocking modal "System down — close positions if any open"
```

### 3.2 Banner Content

```
[STATUS_ICON] [PRIMARY_MESSAGE] • [SECONDARY_INFO]

Examples:
  🟢 ALL SYSTEMS GO • RTH • TREND_DAY • Trades: 2/5
  🟢 ALL SYSTEMS GO • DEVELOPING (skip phase) • Watching only
  🟡 BACKEND LAG 1.4s • Trading reduced to half size
  🟡 DATA AGE 12s • Setups dimmed
  🔴 BRIDGE OFFLINE • TRADING HALTED — manual close required
  🔴 SIERRA DLL DEAD • All orders frozen
```

### 3.3 Implementation Notes

- Sticky top, full width, always visible
- Click → expand to detailed Components Panel
- Animation: pulse on RED state only (don't be annoying when GREEN)
- Don't autohide

---

<a name="4-components"></a>
## 4. Components Panel

### 4.1 Visual Layout

```
┌─────────────────────────────────────────┐
│  System Components                  [▼] │  ← collapse toggle
├─────────────────────────────────────────┤
│                                         │
│  🟢 Bridge          (uptime 35h)        │
│     last data: 1.2s ago                 │
│     CPU: 4%  RAM: 38MB                  │
│                                         │
│  🟢 Backend          (Render OK)        │
│     latency: 142ms                      │
│     last request: 0.8s ago              │
│                                         │
│  🟡 Sierra DLL       (warning)          │
│     last JSON: 6s ago                   │
│     ⚠ data lag — re-add Study?          │
│                                         │
│  🟢 Database         (Postgres)         │
│     latency: 32ms                       │
│     last write: 1.1s ago                │
│                                         │
│  🟢 Redis            (Upstash)          │
│     latency: 8ms                        │
│     keys: 47                            │
│                                         │
│  ───────────────────────────────────    │
│                                         │
│  Trading State:                         │
│    Mode: SIM                             │
│    Day Type: TREND_DAY (92%)            │
│    Time Phase: RTH                      │
│    Trades today: 2/5                    │
│    PnL: +$87                            │
│    Daily cap: -$200 max                 │
│                                         │
└─────────────────────────────────────────┘
```

### 4.2 Color Coding

| State | Color | Meaning |
|-------|-------|---------|
| 🟢 GREEN | #10B981 | Healthy, all thresholds met |
| 🟡 YELLOW | #F59E0B | Warning, degraded but operational |
| 🔴 RED | #DC2626 | Failed, blocks trading |
| ⚫ GREY | #6B7280 | Unknown/checking |

### 4.3 Per-Component Details

Each component card shows:
- Status indicator (color + emoji)
- Component name
- Primary metric (uptime, latency, etc.)
- Secondary metric (last activity time)
- If 🟡 or 🔴: actionable message ("re-add Study?" / "restart Bridge")

---

<a name="5-auto-dim"></a>
## 5. Auto-Dim Behavior

When system is 🟡 or 🔴, the dashboard auto-dims:

### 5.1 🟡 Yellow State (degraded)

```
- Setup signal cards: 60% opacity (visible but muted)
- "Execute Trade" button: disabled, grey
- Tooltip on hover: "System degraded — refresh and verify before trading"
- Component icons in dashboard: amber tint
```

### 5.2 🔴 Red State (failed)

```
- Setup signal cards: 25% opacity (almost invisible)
- "Execute Trade" button: hidden entirely
- Modal overlay: "🔴 SYSTEM DOWN
                  Component: [name]
                  Last known good: [timestamp]
                  Manual action: [recommendation]"
- Background: dark red wash
- Audio alert: 1 chime on transition to RED (only on transition, not continuous)
```

### 5.3 🟢 Recovery

- All UI returns to full opacity
- Brief banner: "🟢 SYSTEMS RESTORED" (5 seconds, then back to normal)
- No audio chime on recovery (silence is the reward)

---

<a name="6-endpoint"></a>
## 6. Backend `/system/status` Endpoint

### 6.1 Specification

```
GET /system/status

Response 200 OK:
{
  "overall_status": "GREEN" | "YELLOW" | "RED",
  "overall_message": "ALL SYSTEMS GO",
  "checked_at": "2026-05-05T10:42:18Z",
  "trade_blocked": false,
  
  "components": {
    "bridge": {
      "status": "GREEN",
      "last_seen": "2026-05-05T10:42:17Z",
      "data_age_seconds": 1.2,
      "uptime_hours": 35.4,
      "cpu_pct": 4,
      "memory_mb": 38,
      "message": null
    },
    "backend": {
      "status": "GREEN",
      "last_check": "2026-05-05T10:42:18Z",
      "latency_ms": 142,
      "uptime_hours": 168.0,
      "message": null
    },
    "sierra_dll": {
      "status": "YELLOW",
      "last_json_write": "2026-05-05T10:42:12Z",
      "data_age_seconds": 6.0,
      "message": "data lag — re-add Study?"
    },
    "database": {
      "status": "GREEN",
      "last_write": "2026-05-05T10:42:17Z",
      "latency_ms": 32,
      "message": null
    },
    "redis": {
      "status": "GREEN",
      "last_check": "2026-05-05T10:42:18Z",
      "latency_ms": 8,
      "key_count": 47,
      "message": null
    }
  },
  
  "trading_state": {
    "mode": "SIM",
    "day_type": "TREND_DAY",
    "day_type_confidence": 92,
    "time_phase": "RTH",
    "trades_today": 2,
    "max_trades_per_day": 5,
    "pnl_today": 87,
    "daily_cap_remaining": 287,
    "active_positions": 0
  }
}

Response 503 Service Unavailable (if backend itself down):
{
  "overall_status": "RED",
  "overall_message": "Backend unreachable",
  "trade_blocked": true
}
```

### 6.2 Implementation

```python
# backend/app/system_status.py

from datetime import datetime, timezone
from typing import Dict, Any
import asyncio

from app.deps import get_redis, get_db

async def check_bridge() -> Dict[str, Any]:
    redis = get_redis()
    last_heartbeat = await redis.get("mems26:bridge:heartbeat")
    if not last_heartbeat:
        return {"status": "RED", "message": "Bridge heartbeat missing"}
    
    last_ts = datetime.fromisoformat(last_heartbeat)
    age = (datetime.now(timezone.utc) - last_ts).total_seconds()
    
    if age > 30:
        return {"status": "RED", "data_age_seconds": age, "message": f"Bridge silent {age:.0f}s"}
    if age > 5:
        return {"status": "YELLOW", "data_age_seconds": age, "message": f"Bridge lag {age:.1f}s"}
    return {"status": "GREEN", "data_age_seconds": age, "last_seen": last_heartbeat}

async def check_sierra_dll() -> Dict[str, Any]:
    redis = get_redis()
    last_write = await redis.get("mems26:dll:last_write")
    if not last_write:
        return {"status": "RED", "message": "DLL never wrote"}
    
    last_ts = datetime.fromisoformat(last_write)
    age = (datetime.now(timezone.utc) - last_ts).total_seconds()
    
    if age > 15:
        return {"status": "RED", "data_age_seconds": age, "message": "DLL silent — re-add Study"}
    if age > 5:
        return {"status": "YELLOW", "data_age_seconds": age, "message": "data lag — re-add Study?"}
    return {"status": "GREEN", "data_age_seconds": age, "last_json_write": last_write}

async def check_database() -> Dict[str, Any]:
    db = get_db()
    try:
        start = asyncio.get_event_loop().time()
        await db.execute("SELECT 1")
        latency_ms = (asyncio.get_event_loop().time() - start) * 1000
        if latency_ms > 1000:
            return {"status": "YELLOW", "latency_ms": latency_ms, "message": f"DB slow {latency_ms:.0f}ms"}
        return {"status": "GREEN", "latency_ms": latency_ms}
    except Exception as e:
        return {"status": "RED", "message": f"DB connection failed: {e}"}

async def check_redis() -> Dict[str, Any]:
    redis = get_redis()
    try:
        start = asyncio.get_event_loop().time()
        await redis.ping()
        latency_ms = (asyncio.get_event_loop().time() - start) * 1000
        keys = await redis.dbsize()
        if latency_ms > 500:
            return {"status": "YELLOW", "latency_ms": latency_ms, "key_count": keys}
        return {"status": "GREEN", "latency_ms": latency_ms, "key_count": keys}
    except Exception as e:
        return {"status": "RED", "message": f"Redis ping failed: {e}"}

async def check_backend_self() -> Dict[str, Any]:
    # Backend is responding if we got here
    return {"status": "GREEN", "latency_ms": 0, "message": "self"}

async def aggregate_status() -> Dict[str, Any]:
    bridge = await check_bridge()
    sierra = await check_sierra_dll()
    db = await check_database()
    redis = await check_redis()
    backend = await check_backend_self()
    
    components = {
        "bridge": bridge,
        "backend": backend,
        "sierra_dll": sierra,
        "database": db,
        "redis": redis,
    }
    
    # Aggregate overall: RED if any RED, YELLOW if any YELLOW, GREEN otherwise
    statuses = [c["status"] for c in components.values()]
    if "RED" in statuses:
        overall = "RED"
        red_components = [k for k, v in components.items() if v["status"] == "RED"]
        message = f"DOWN: {', '.join(red_components)}"
    elif "YELLOW" in statuses:
        overall = "YELLOW"
        yellow_components = [k for k, v in components.items() if v["status"] == "YELLOW"]
        message = f"DEGRADED: {', '.join(yellow_components)}"
    else:
        overall = "GREEN"
        message = "ALL SYSTEMS GO"
    
    return {
        "overall_status": overall,
        "overall_message": message,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "trade_blocked": (overall == "RED"),
        "components": components,
        "trading_state": await get_trading_state(),
    }
```

### 6.3 Polling Strategy

- Frontend polls `/system/status` every **5 seconds**
- Cache backend response for **2 seconds** (avoid hammering Redis)
- On 🔴 transition: poll every **2 seconds** until recovery
- Bridge writes heartbeat to Redis every **1 second** (`mems26:bridge:heartbeat`)
- DLL writes timestamp to JSON file every **1 second** → Bridge updates Redis

---

<a name="7-thresholds"></a>
## 7. Component Thresholds

| Component | GREEN | YELLOW | RED |
|-----------|-------|--------|-----|
| **Bridge** | data_age < 3s | 3s ≤ age < 30s | age ≥ 30s |
| **Backend** | latency < 500ms | 500-1500ms | > 1500ms or no response |
| **Sierra DLL** | last_write < 3s | 3s ≤ age < 15s | age ≥ 15s |
| **Database** | latency < 200ms | 200-1000ms | > 1000ms or fail |
| **Redis** | latency < 100ms | 100-500ms | > 500ms or fail |

### 7.1 Trade Blocking Rules

```
trade_blocked = (overall_status == "RED")

Specifically:
  Bridge RED      → trade_blocked (no data flowing)
  Sierra DLL RED  → trade_blocked (orders won't reach Sierra)
  Database RED    → trade_blocked (can't journal trades)
  Redis RED       → trade_blocked (Bridge can't communicate with Backend)
  Backend YELLOW  → ALLOW with warning (latency tolerable for limit orders)
```

### 7.2 Manual Override

User can override RED state with:
```
1. Click status banner → "Acknowledge degraded state" modal
2. Type confirmation: "I UNDERSTAND TRADE AT OWN RISK"
3. Override expires in 5 minutes (auto-revert)
4. Override logged to DB with timestamp
```

**Use case:** Sometimes during quick lag spikes, you want to keep position management active. Override allows it but logs everything.

---

<a name="8-frontend"></a>
## 8. Frontend Implementation

### 8.1 Components

```
frontend/src/components/StatusLayer/
├── StatusBanner.tsx          ← top bar
├── ComponentsPanel.tsx        ← left sidebar
├── ComponentCard.tsx          ← single component display
├── AutoDimWrapper.tsx         ← wraps SetupSignals to apply opacity
└── DegradedModal.tsx          ← RED state blocking overlay
```

### 8.2 Hook

```typescript
// frontend/src/hooks/useSystemStatus.ts
import { useEffect, useState } from 'react';

interface SystemStatus {
  overall_status: 'GREEN' | 'YELLOW' | 'RED';
  overall_message: string;
  trade_blocked: boolean;
  components: Record<string, ComponentStatus>;
  trading_state: TradingState;
}

export function useSystemStatus(): SystemStatus | null {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  
  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    
    const fetchStatus = async () => {
      try {
        const res = await fetch('https://mems26-web.onrender.com/system/status');
        if (!res.ok) {
          setStatus({
            overall_status: 'RED',
            overall_message: 'Backend unreachable',
            trade_blocked: true,
            components: {},
            trading_state: {} as TradingState,
          });
          return;
        }
        const data = await res.json();
        setStatus(data);
      } catch (err) {
        setStatus({
          overall_status: 'RED',
          overall_message: 'Network error',
          trade_blocked: true,
          components: {},
          trading_state: {} as TradingState,
        });
      } finally {
        // Faster polling on RED, normal on others
        const interval = status?.overall_status === 'RED' ? 2000 : 5000;
        timeoutId = setTimeout(fetchStatus, interval);
      }
    };
    
    fetchStatus();
    
    return () => clearTimeout(timeoutId);
  }, [status?.overall_status]);
  
  return status;
}
```

### 8.3 Banner Component

```tsx
// frontend/src/components/StatusLayer/StatusBanner.tsx
'use client';
import { useSystemStatus } from '@/hooks/useSystemStatus';

const COLORS = {
  GREEN: 'bg-green-900/40 border-green-500/50 text-green-200',
  YELLOW: 'bg-amber-900/40 border-amber-500/50 text-amber-200',
  RED: 'bg-red-900/60 border-red-500/70 text-red-200 animate-pulse',
};

const ICONS = { GREEN: '🟢', YELLOW: '🟡', RED: '🔴' };

export function StatusBanner() {
  const status = useSystemStatus();
  if (!status) return null;
  
  const cls = COLORS[status.overall_status];
  const icon = ICONS[status.overall_status];
  
  return (
    <div className={`sticky top-0 z-50 w-full border-b px-4 py-2 ${cls}`}>
      <div className="flex items-center justify-between text-sm font-medium">
        <span>
          {icon} {status.overall_message}
        </span>
        {status.trading_state?.day_type && (
          <span className="text-xs opacity-80">
            {status.trading_state.time_phase} • {status.trading_state.day_type}
            {status.trading_state.day_type_confidence &&
              ` ${status.trading_state.day_type_confidence}% conf`}
            {status.trading_state.trades_today !== undefined &&
              ` • Trades: ${status.trading_state.trades_today}/${status.trading_state.max_trades_per_day}`}
          </span>
        )}
      </div>
    </div>
  );
}
```

### 8.4 Auto-Dim Wrapper

```tsx
// frontend/src/components/StatusLayer/AutoDimWrapper.tsx
'use client';
import { useSystemStatus } from '@/hooks/useSystemStatus';
import { ReactNode } from 'react';

const OPACITY = { GREEN: 1.0, YELLOW: 0.6, RED: 0.25 };

export function AutoDimWrapper({ children }: { children: ReactNode }) {
  const status = useSystemStatus();
  const opacity = status ? OPACITY[status.overall_status] : 1.0;
  
  return (
    <div
      style={{ opacity, transition: 'opacity 0.3s ease' }}
      className={status?.trade_blocked ? 'pointer-events-none' : ''}
    >
      {children}
    </div>
  );
}
```

---

<a name="9-failures"></a>
## 9. Failure Mode Catalog

### 9.1 Bridge Crashes

```
Symptom:  data_age > 30s
Status:   🔴 RED
Action:   Trade blocked. Modal: "Bridge offline. Run pkill + restart."
Recovery: Bridge restart command (in memory)
ETA:      Manual restart ~30s
```

### 9.2 Sierra DLL Loses Connection

```
Symptom:  last_json_write > 15s
Status:   🔴 RED
Action:   Trade blocked. Modal: "Sierra DLL silent. Re-add Study."
Recovery: User performs "Re-add Study" in Sierra Chart
ETA:      30-60s
```

### 9.3 Backend Render Cold Start

```
Symptom:  latency 500ms-1500ms (Render free tier wakes up)
Status:   🟡 YELLOW
Action:   Auto-dim, allow trades but warn
Recovery: Auto (warm-up takes 10-20s)
ETA:      < 30s
```

### 9.4 Database Slow Queries

```
Symptom:  DB latency 200ms-1000ms
Status:   🟡 YELLOW
Action:   Auto-dim, allow trades, log slow query alerts
Recovery: Auto (transient) or manual (vacuum/analyze)
ETA:      Variable
```

### 9.5 Redis Out-of-Memory

```
Symptom:  Redis ping fails or > 500ms
Status:   🔴 RED
Action:   Trade blocked. Modal: "Redis full or down."
Recovery: Manual cleanup or upgrade plan
ETA:      Manual (15+ min)
```

### 9.6 Network Partition

```
Symptom:  Frontend can't reach Backend
Status:   🔴 RED (frontend-side fallback)
Action:   Block all UI actions. Show "Network error — check connection."
Recovery: Wait for network restoration
ETA:      Variable
```

---

<a name="10-acceptance"></a>
## 10. Acceptance Criteria

For LIVE 21/5 deployment:

- [ ] Banner displayed sticky-top on all dashboard routes
- [ ] Components panel shows all 5 components with correct colors
- [ ] Auto-dim activates within 5s of YELLOW transition
- [ ] Trade button hides within 5s of RED transition
- [ ] Audio chime plays once on GREEN→RED transition
- [ ] No chime on transitions other than GREEN→RED
- [ ] `/system/status` endpoint returns within 200ms (p95)
- [ ] Manual override flow works and logs to DB
- [ ] Override auto-expires after 5 minutes
- [ ] Bridge heartbeat to Redis verified
- [ ] DLL last_write timestamp captured and exposed
- [ ] All 6 failure modes from §9 tested in synthetic scenarios
- [ ] Status persists across page refresh (no flicker)
- [ ] Performance: Status polling adds < 1% CPU on frontend

---

## Document History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 5 May 2026 EOD | Initial spec — banner + panel + auto-dim + endpoint |

---

**Maintained by:** Michael (with Claude assistance)
**Status:** LOCKED — input to Phase 3.3 implementation
**Next review:** After first deployment in Phase 3.3 Day 2
