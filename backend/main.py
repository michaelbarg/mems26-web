import os
import json
import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# הגדרת לוגים - כדי שנוכל לראות הכל ב-Render
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("api")

# טוקן אבטחה - חייב להתאים למה שמוגדר ב-Bridge
BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "michael-mems26-2026")

# משתנים גלובליים לשמירת המצב האחרון
_last_payload = None
_last_signal  = None

class ConnectionManager:
    def __init__(self):
        self._clients: list[WebSocket] = []
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.append(ws)
    def disconnect(self, ws: WebSocket):
        if ws in self._clients: self._clients.remove(ws)
    async def broadcast(self, data: dict):
        for ws in self._clients:
            try: await ws.send_json(data)
            except: pass

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("MEMS26 API Started")
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ingest")
async def ingest(request: Request, x_bridge_token: Optional[str] = Header(None)):
    global _last_payload
    
    # בדיקת אבטחה
    if x_bridge_token != BRIDGE_TOKEN:
        log.warning(f"Unauthorized: {x_bridge_token}")
        raise HTTPException(status_code=401, detail="Invalid token")

    # שמירת הנתונים
    raw = await request.json()
    _last_payload = raw
    
    log.info(f"✅ Received Data: Price {raw.get('bar', {}).get('c')}")
    
    # שליחה לכל מי שמחובר ב-WebSocket
    await manager.broadcast({"type": "market_update", **raw})
    
    return {"ok": True}

@app.get("/market/latest")
async def market_latest():
    global _last_payload
    if not _last_payload:
        return {"type": "no_data", "status": "waiting_for_bridge"}
    return _last_payload

@app.get("/health")
async def health():
    return {"status": "ok", "has_data": _last_payload is not None}
