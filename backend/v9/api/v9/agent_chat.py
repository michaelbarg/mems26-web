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
        # עין-סיירה הנטיבית (FIX-13): מה הברוקר באמת מחזיק — עדיפה על כל DB
        from pathlib import Path as _P
        import json as _json, time as _t
        sf = _P(os.path.expanduser("~/SierraChart_Data/v9_export/sierra_state.json"))
        if sf.exists():
            age = _t.time() - sf.stat().st_mtime
            data = _json.loads(sf.read_text().strip() or "{}")
            parts.append(f"sierra_broker_state (age {age:.0f}s{' — STALE>10s' if age > 10 else ''}): "
                         f"is_sim={data.get('is_sim')} position_qty={data.get('position_qty')} "
                         f"avg={data.get('avg_price')} working_orders={data.get('working_orders')} "
                         f"orders={data.get('orders')}")
        else:
            parts.append("sierra_broker_state: file missing (DLL not exporting)")
    except Exception:
        pass
    try:
        from pathlib import Path
        alerts = Path(os.path.expanduser(
            "~/Downloads/mems26_web_git/docs/reports/ALERTS_LIVE.md"))
        if alerts.exists():
            import datetime as _dt
            mtime = _dt.datetime.fromtimestamp(alerts.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            tail = alerts.read_text(encoding="utf-8", errors="ignore").splitlines()[-5:]
            parts.append(f"recent_alerts (file last modified {mtime}; lines may be OLD/resolved — trust RESOLVED markers): "
                         + " | ".join(tail))
    except Exception:
        pass
    return "\n".join(parts) or "(no live context available)"


REPO_ROOT = os.path.expanduser("~/Downloads/mems26_web_git")

# מפת-הידע של המערכת (מייקל 07-12): הצ'אט יודע איפה הכל מסודר, וטוען
# קטעים רלוונטיים לפי נושא-השאלה (חסכוני בטוקנים — לא הכל בכל הודעה).
KNOWLEDGE_MAP = """מפת-הידע של המערכת (הכל מאונדקס ומסודר):
- SYSTEM_INDEX.md + _INDEX.md בכל תיקייה — מיקום כל קובץ/מערכת בקוד (792 קבצים).
- docs/FLAG_INDEX.md — כל 130+ הדגלים: מצב, ברירת-מחדל, מה+למה, file:line.
- config/RULED_FLAGS.yaml — 50 הדגלים הפסוקים ע"י מייקל (החוק).
- docs/plans/DEV_BACKLOG.md — לוח-המשימות: לפיתוח/ממתין/בוצע, בעדיפויות.
- docs/plans/STATUS_BOARD.md — יומן-הראיות: כל סגירה עם שורש+תיקון+אימות.
- docs/plans/ROADMAP_TO_LIVE.html — מבט-על "אתה כאן".
- docs/spec_authority/DALTON_DOCTRINE.md — התורה של S1 (דלתון) + נספח-סטטוס.
- docs/reports/TARGETS_STOPS_TABLE_2026-07-13.md — איך נקבעים יעדים/סטופ פר יום×תבנית.
- docs/SOURCE_OF_TRUTH.md — איזה מקור-דאטה קנוני פר אות.
- docs/runbooks/ — פרוטוקולים (בוקר, קידום-למסחר, מק-שני, DLL)."""

_TOPIC_FILES = [
    (("משימ", "פיתוח", "בקלוג", "backlog", "תור", "עדיפו"), "docs/plans/DEV_BACKLOG.md", 3500),
    (("דגל", "flag", "פסיק"), "docs/FLAG_INDEX.md", 3000),
    (("יעד", "סטופ", "target", "stop", "מימוש"), "docs/reports/TARGETS_STOPS_TABLE_2026-07-13.md", 3500),
    (("דלתון", "דוקטרינ", "סוג יום", "סוג-יום", "day type", "נייטרל", "trend", "מגמה"),
     "docs/spec_authority/DALTON_DOCTRINE.md", 3000),
    (("סטטוס", "מה קרה", "תקרית", "היסטורי", "אתמול"), "docs/plans/STATUS_BOARD.md", 3000),
]


def _knowledge_context(message: str) -> str:
    """Load excerpts of the indexed docs relevant to the question's topic."""
    msg = (message or "").lower()
    chunks = []
    for keywords, rel, budget in _TOPIC_FILES:
        if any(k in msg for k in keywords):
            try:
                from pathlib import Path
                p = Path(REPO_ROOT) / rel
                if p.exists():
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    # STATUS_BOARD: the tail is the recent truth; others: the head
                    excerpt = text[-budget:] if "STATUS_BOARD" in rel else text[:budget]
                    chunks.append(f"--- {rel} (קטע) ---\n{excerpt}")
            except Exception:
                pass
        if len(chunks) >= 2:  # token budget: at most two docs per question
            break
    return "\n\n".join(chunks)


SYSTEM_PROMPT = """אתה הסוכן של MEMS26 — מערכת מסחר אוטונומית ב-MES (Market Profile/דלתון,
מערכות S1-S6, סטופים מבניים, יעדי-ריאליזם). ענה למייקל בעברית, קצר ומדויק,
תמיד על בסיס ההקשר המצורף — אל תמציא נתונים שאינם בו. אם המידע לא בהקשר,
אמור זאת והפנה למקום הנכון לפי מפת-הידע.
אל תמליץ לבצע פעולות מסחר ואל תשנה שום דבר — אתה עונה ומסביר בלבד.

{knowledge_map}

הקשר חי:
{context}

{topic_docs}"""


@router.get("/backlog_board")
async def backlog_board():
    """הלוח החי לדף /board — נפרס מ-DEV_BACKLOG.md בכל קריאה (לא יכול להתיישן).
    ‏read-only ללא-טוקן, כמו health — מוגש רק על localhost."""
    try:
        from backend.v9.services.backlog_board import build_board
        return build_board()
    except Exception as e:
        logger.warning("[backlog_board] %s", e)
        raise HTTPException(status_code=500, detail=f"backlog parse error: {e}")


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
        "system": SYSTEM_PROMPT.format(
            knowledge_map=KNOWLEDGE_MAP,
            context=_live_context(),
            topic_docs=_knowledge_context(body.message),
        ),
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
