"""agent_chat — in-dashboard Claude chat with live system context (Michael 07-12).

POST /api/v9/agent/chat  {message, history?}  →  {reply}

The route gathers a LIVE system snapshot (day type, active trade, flags of
interest, recent alerts, health) and sends it as context to the Anthropic API
so the answer is grounded in the machine's actual state — not generic.

Security: ANTHROPIC_API_KEY lives in .env (out-of-git), read server-side only,
never logged, never returned. Route requires the same bearer auth as the rest
of the API. Missing key → honest 503 (the UI shows how to add it).
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.v9.api.v9.trade_commands import verify_bridge_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v9/agent", tags=["v9-agent-chat"])

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.getenv("AGENT_CHAT_MODEL", "claude-sonnet-5")
MAX_TOKENS = int(os.getenv("AGENT_CHAT_MAX_TOKENS", "700"))


class ChatTurn(BaseModel):
    role: str          # "user" | "assistant"
    content: str


class ChatIn(BaseModel):
    message: str
    history: Optional[List[ChatTurn]] = None


def _live_context() -> str:
    """Best-effort live snapshot; every section fails soft (honest gaps)."""
    parts = []
    try:
        import importlib
        app = importlib.import_module("backend.v9.app").app
        dtm = getattr(app.state, "day_type_machine", None)
        if dtm is not None:
            dt = getattr(dtm, "day_type", None)
            parts.append(f"day_type: {getattr(dt, 'value', dt)}")
    except Exception:
        pass
    try:
        from backend.v9.db.read import read_all
        rows = read_all("""
            SELECT id, direction, entry_price, stop, t1, t2, pnl_usd, state,
                   quality->>'pattern' AS pattern
            FROM v9_trades WHERE mode != 'shadow'
              AND state NOT IN ('CLOSED','CANCELLED') ORDER BY id DESC LIMIT 3""", {})
        parts.append(f"open_trades: {rows if rows else 'none'}")
        day = read_all("""
            SELECT COALESCE(SUM(pnl_usd),0) AS pnl, COUNT(*) AS n FROM v9_trades
            WHERE mode != 'shadow' AND state='CLOSED'
              AND (entry_ts AT TIME ZONE 'Asia/Jerusalem')::date =
                  (now() AT TIME ZONE 'Asia/Jerusalem')::date""", {})
        if day:
            parts.append(f"today_closed: {day[0]}")
    except Exception:
        pass
    try:
        keys = ("FIXED_CONTRACTS_3", "RISK_DAILY_LOSS_CAP", "S1_TREND_CONTROL_V1",
                "S1_NONCONVICTION_V1", "S1_DD_INVALIDATION_V1", "TARGET_REALISM_V1",
                "STOP_PERBAR_STRUCT_V1", "NONTREND_DISABLE_ALL")
        parts.append("flags: " + ", ".join(f"{k}={os.getenv(k, 'unset')}" for k in keys))
    except Exception:
        pass
    try:
        from pathlib import Path
        alerts = Path(os.path.expanduser(
            "~/Downloads/mems26_web_git/docs/reports/ALERTS_LIVE.md"))
        if alerts.exists():
            tail = alerts.read_text(encoding="utf-8", errors="ignore").splitlines()[-5:]
            parts.append("recent_alerts: " + " | ".join(tail))
    except Exception:
        pass
    return "\n".join(parts) or "(no live context available)"


SYSTEM_PROMPT = """אתה הסוכן של MEMS26 — מערכת מסחר אוטונומית ב-MES (Market Profile/דלתון,
מערכות S1-S6, סטופים מבניים, יעדי-ריאליזם). ענה למייקל בעברית, קצר ומדויק,
תמיד על בסיס ההקשר-החי המצורף — אל תמציא נתונים שאינם בו. אם המידע לא בהקשר,
אמור זאת והפנה למקום הנכון (דשבורד /trades, DEV_BACKLOG.md, STATUS_BOARD.md).
אל תמליץ לבצע פעולות מסחר ואל תשנה שום דבר — אתה עונה ומסביר בלבד.

הקשר חי:
{context}"""


@router.post("/chat")
async def agent_chat(body: ChatIn, _token: str = Depends(verify_bridge_token)):
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail=(
            "ANTHROPIC_API_KEY חסר ב-.env — הוסף שורה ANTHROPIC_API_KEY=sk-ant-... "
            "ועשה ריסטארט לבקאנד."))

    messages = []
    for t in (body.history or [])[-10:]:
        if t.role in ("user", "assistant") and t.content.strip():
            messages.append({"role": t.role, "content": t.content[:4000]})
    messages.append({"role": "user", "content": body.message[:4000]})

    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT.format(context=_live_context()),
        "messages": messages,
    }
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(ANTHROPIC_URL, json=payload, headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            })
        if r.status_code != 200:
            logger.warning("[agent_chat] Anthropic API %s: %s", r.status_code, r.text[:200])
            raise HTTPException(status_code=502,
                                detail=f"Anthropic API error {r.status_code}")
        data = r.json()
        reply = "".join(b.get("text", "") for b in data.get("content", [])
                        if b.get("type") == "text")
        return {"reply": reply or "(תשובה ריקה)", "model": MODEL}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("[agent_chat] error: %s", e)
        raise HTTPException(status_code=502, detail=f"chat error: {e}")
