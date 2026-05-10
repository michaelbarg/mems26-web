"""MEMS26 V9 FastAPI application."""

from fastapi import FastAPI
from backend.v9.api.v9 import bars, signals, markers, trades, configs, websocket

app = FastAPI(title="MEMS26 V9", version="9.0.0")

app.include_router(bars.router)
app.include_router(signals.router)
app.include_router(markers.router)
app.include_router(trades.router)
app.include_router(configs.router)
app.include_router(websocket.router)


@app.get("/api/v9/health")
def health():
    return {"status": "ok", "version": "v9.0.0"}
