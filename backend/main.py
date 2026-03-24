"""
backend/main.py
================
FastAPI Server — רץ על Render (ענן).

Endpoints:
  POST /ingest          ← מ-Bridge המקומי
  GET  /ws              ← WebSocket ל-Dashboard
  GET  /health          ← Health check
  GET  /signals/latest  ← REST API לדשבורד
"""

import os
import json
import asyncio
import logging
from datetime import datetime, date
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from engine.signal_engine import SignalEngine
from engine.models import MarketData, SignalResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("api")

BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "change-me-secret")

# ── WebSocket connection manager ─────────────────────────────
class ConnectionManager:
    def __init__(self):
        self._clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.append(ws)
        log.info(f"WS client connected. Total: {len(self._clients)}")

    def disconnect(self, ws: WebSocket):
        if ws in self._clients:
            self._clients.remove(ws)
        log.info(f"WS client disconnected. Total: {len(self._clients)}")

    async def broadcast(self, data: dict):
        dead = []
        for ws in self._clients:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
engine  = SignalEngine()

# Cache last payload for new connections
_last_payload: Optional[dict] = None
_last_signal:  Optional[dict] = None


# ── App lifecycle ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("MEMS26 API starting...")
    yield
    log.info("MEMS26 API shutting down.")


app = FastAPI(title="MEMS26 AI Trader API", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Ingest endpoint (from local bridge) ─────────────────────
@app.post("/ingest")
async def ingest(
    request: Request,
    x_bridge_token: Optional[str] = Header(None)
):
    """מקבל enriched payload מה-Bridge המקומי"""
    global _last_payload, _last_signal

    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid bridge token")

    raw = await request.json()
    _last_payload = raw

    # Parse into typed model
    try:
        market_data = MarketData.from_dict(raw)
    except Exception as e:
        log.error(f"Parse error: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    # ── Run AI analysis (async, non-blocking) ──────────────
    signal: Optional[SignalResult] = await engine.analyze(market_data)

    # Build broadcast message
    message = {
        "type":       "market_update",
        "ts":         raw.get("ts"),
        "price":      raw["bar"]["c"],
        "session":    raw["session"]["phase"],
        "ses_min":    raw["session"]["min"],
        "features":   raw.get("features", {}),
        "woodi":      raw.get("woodi", {}),
        "levels":     raw.get("levels", {}),
        "cvd":        raw.get("cvd", {}),
        "bar":        raw.get("bar", {}),
        "signal":     signal.to_dict() if signal else None,
        "daily_stats":engine.get_daily_stats(),
    }

    if signal:
        _last_signal = signal.to_dict()
        log.info(f"Signal: {signal.direction} score={signal.score} conf={signal.confidence}")

    # Broadcast to all WebSocket clients
    await manager.broadcast(message)

    return {"ok": True, "signal": bool(signal)}


# ── WebSocket endpoint (for Dashboard) ──────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        # Send last known state immediately on connect
        if _last_payload:
            await ws.send_json({
                "type":    "init",
                "payload": _last_payload,
                "signal":  _last_signal,
                "daily_stats": engine.get_daily_stats(),
            })

        while True:
            # Keep alive — receive pings from client
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                if data == "ping":
                    await ws.send_text("pong")
            except asyncio.TimeoutError:
                await ws.send_text("ping")   # server-side keepalive

    except WebSocketDisconnect:
        manager.disconnect(ws)


# ── REST endpoints ───────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "clients": len(manager._clients),
        "last_price": _last_payload["bar"]["c"] if _last_payload else None,
        "trades_today": engine.get_daily_stats().get("trades_taken", 0),
    }

@app.get("/signals/latest")
async def latest_signal():
    return _last_signal or {"signal": None}

@app.get("/signals/history")
async def signal_history():
    return engine.get_signal_history()

@app.get("/market/latest")
async def market_latest():
    """מחזיר נתון מלא לדשבורד (polling)"""
    if not _last_payload:
        return {"status": "no_data"}
    return {
        "type":        "market_update",
        "ts":          _last_payload.get("ts"),
        "price":       _last_payload["bar"]["c"],
        "session":     _last_payload["session"]["phase"],
        "ses_min":     _last_payload["session"]["min"],
        "features":    _last_payload.get("features", {}),
        "woodi":       _last_payload.get("woodi", {}),
        "levels":      _last_payload.get("levels", {}),
        "cvd":         _last_payload.get("cvd", {}),
        "bar":         _last_payload.get("bar", {}),
        "signal":      _last_signal,
        "daily_stats": engine.get_daily_stats(),
    }
