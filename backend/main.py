"""MEMS26 unified backend — serves V8-compatible routes + V9 API.

Entry point for Render:
    web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
"""

import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.v9.app import v9_router, init_event_dispatcher

# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title="MEMS26",
    version="9.0.0",
    description="Unified backend: V8 compat + V9 trading API",
)

# ── CORS ─────────────────────────────────────────────────────

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount V9 routes ──────────────────────────────────────────

app.include_router(v9_router)


@app.on_event("startup")
def _startup_event_dispatcher():
    """Initialize EventDispatcher with all 6 systems at unified app startup."""
    init_event_dispatcher()


# ── Health (unified) ─────────────────────────────────────────

_START_TS = time.time()


@app.get("/health")
def health():
    """Top-level health check — used by Render zero-downtime deploys."""
    uptime = time.time() - _START_TS
    return {
        "status": "ok",
        "service": "mems26-unified",
        "version": "9.0.0",
        "uptime_s": round(uptime, 1),
        "v9_mounted": True,
    }
