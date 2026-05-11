# MEMS26 — Environment Reference

## Hardware / OS
- **Machine:** Mac (Apple Silicon / Intel)
- **OS:** macOS (Darwin 24.5.0)
- **Sierra Chart:** Runs via CrossOver (Wine layer) — all file paths are Mac-native

## Runtime
| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.9.7 | System install at /Library/Frameworks/Python.framework |
| Node.js | 23.x | For Next.js frontend |
| npm | 10.x | Package manager |
| pip | via pip3 | Python packages |

## Key Directories
| Path | Purpose |
|------|---------|
| `/Users/michael/Downloads/mems26_web_git` | Main repo |
| `/Users/michael/SierraChart_Data/v9_export/` | DLL JSON exports |
| `/Users/michael/SierraChart/ACS_Source/` | DLL C++ source (outside repo) |

## Environment Variables (.env)
| Variable | Purpose |
|----------|---------|
| `UPSTASH_REDIS_REST_URL` | Redis endpoint for Event Bus + Bridge |
| `UPSTASH_REDIS_REST_TOKEN` | Redis auth token |
| `BRIDGE_TOKEN` | Auth token for Bridge -> Backend API |
| `V9_EXPORT_DIR` | Path to DLL export directory |
| `CLOUD_URL` | Backend URL (localhost for dev, Render for prod) |

## Frontend (.env.local)
| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL |
| `NEXT_PUBLIC_WS_URL` | WebSocket base URL |
| `NEXT_PUBLIC_BRIDGE_TOKEN` | Auth token for WS connections |

## Python Dependencies (requirements.txt)
fastapi, uvicorn[standard], sqlalchemy, psycopg2-binary, redis, pydantic, httpx, websockets

## Node Dependencies (frontend/v9/package.json)
next, react, react-dom, zustand, @tanstack/react-query, lightweight-charts, lucide-react, react-resizable-panels

## Sierra Chart DLL Rules
- NO `std::max`/`std::min` — use `v9_max`/`v9_min` (AP-T01)
- NO Windows paths — use `/Users/michael/...` (AP-T03)
- NO `sc.GetPersistentString` — use `sc.GetPersistentSCString` (AP-T04)
- Build: Analysis menu -> Build Advanced Custom Study DLL
