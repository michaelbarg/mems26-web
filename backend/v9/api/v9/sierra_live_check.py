"""sierra_live_check — T1 (Michael 2026-07-14): READ-ONLY proof the system
DETECTS the live Sierra state. NO order commands — safe on a live day.

  1. Sierra alive        — sierra_state.json fresh (< STALE_S).
  2. mode + armed        — is_sim (SIMULATION/LIVE) + order_placement_armed (In:22).
  3. open trade          — position_qty != 0, plus the open trade's FULL plan (TM):
                           dir/contracts/entry/stop/T1-T3/pattern (Michael: "עסקה בפתיחה").
  4. closure-on-fill     — today's CLOSED real trades + exit_reason (T1/T2/T3/STOP/FLATTEN).
  5. records == reality  — TM net (records) vs Sierra qty (reality).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/api/v9/agent", tags=["v9-sierra-live-check"])

STATE = Path(os.path.expanduser("~/SierraChart_Data/v9_export/sierra_state.json"))
STALE_S = 10.0


def _read_state() -> Dict[str, Any]:
    try:
        age = time.time() - STATE.stat().st_mtime
        data = json.loads(STATE.read_text().strip() or "{}")
        return {"ok": True, "age_s": round(age, 1), **data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/sierra_live_check")
def sierra_live_check() -> Dict[str, Any]:
    checks = []

    def add(key: str, ok: bool, detail: str):
        checks.append({"check": key, "ok": bool(ok), "detail": detail})

    st = _read_state()
    alive = bool(st.get("ok")) and st.get("age_s", 999) < STALE_S
    add("sierra_alive", alive,
        f"state age {st.get('age_s')}s (<{STALE_S})" if st.get("ok") else f"no state: {st.get('error')}")

    is_sim = st.get("is_sim")
    armed = st.get("order_placement_armed")
    add("mode_known", is_sim is not None,
        f"is_sim={is_sim} ({'SIMULATION' if is_sim else 'LIVE' if is_sim == 0 else '?'}) · "
        f"armed(In:22)={armed} ({'ישלח הזמנות' if armed else 'לא-מזוין'})")

    # open position + the open trade's full plan
    qty = st.get("position_qty")
    working = st.get("working_orders")
    open_trade = None
    try:
        from backend.v9.db.read import read_all
        ot = read_all("""
            SELECT id, direction, entry_price, stop, t1, t2, t3, pnl_usd, state,
                   COALESCE((quality->>'contracts')::int, 3) AS contracts,
                   quality->>'pattern' AS pattern, day_type_at_entry
            FROM v9_trades WHERE mode != 'shadow'
              AND state NOT IN ('CLOSED','CANCELLED') ORDER BY id DESC LIMIT 1""", {})
        if ot:
            open_trade = ot[0]
    except Exception:
        pass
    add("position_detect", qty is not None,
        f"position_qty={qty} · working_orders={working} · avg={st.get('avg_price')} "
        f"→ {'עסקה פתוחה' if qty else 'שטוח'}"
        + (f" · TM #{open_trade['id']} {open_trade['direction']} {open_trade['contracts']}c "
           f"entry {open_trade['entry_price']} stop {open_trade['stop']} "
           f"T1/T2/T3 {open_trade['t1']}/{open_trade['t2']}/{open_trade['t3']} "
           f"pat={open_trade['pattern']} day={open_trade['day_type_at_entry']}"
           if open_trade else ""))

    # closure-on-fill: today's CLOSED real trades
    closures = []
    try:
        from backend.v9.db.read import read_all
        rows = read_all("""
            SELECT id, direction, entry_price, exit_price, pnl_usd, exit_reason,
                   (entry_ts AT TIME ZONE 'Asia/Jerusalem')::time AS t_in,
                   (exit_ts  AT TIME ZONE 'Asia/Jerusalem')::time AS t_out
            FROM v9_trades WHERE mode != 'shadow' AND state='CLOSED'
              AND (entry_ts AT TIME ZONE 'Asia/Jerusalem')::date =
                  (now() AT TIME ZONE 'Asia/Jerusalem')::date
            ORDER BY id DESC LIMIT 10""", {})
        closures = rows or []
        add("closure_on_fill", True,
            f"{len(closures)} עסקאות-אמת נסגרו היום; סיבות-יציאה: "
            + (", ".join(sorted({str(r.get('exit_reason')) for r in closures})) or "—"))
    except Exception as e:
        add("closure_on_fill", False, f"DB read error: {e}")

    # records == reality
    try:
        from backend.v9.db.read import read_all
        tm = read_all("""SELECT COALESCE(SUM(
                CASE WHEN direction='LONG' THEN 1 ELSE -1 END), 0) AS net
            FROM v9_trades WHERE mode!='shadow'
              AND state NOT IN ('CLOSED','CANCELLED')""", {})
        tm_net = (tm[0]["net"] if tm else 0) or 0
        match = (qty is not None) and (int(qty) == int(tm_net))
        add("records_eq_reality", match,
            f"TM net={tm_net} (רשומות) vs Sierra qty={qty} (מציאות) → "
            f"{'MATCH' if match else 'DIVERGENCE'}")
    except Exception as e:
        add("records_eq_reality", False, f"reconcile unavailable: {e}")

    all_ok = all(c["ok"] for c in checks)
    today_pnl = sum(float(r.get("pnl_usd") or 0) for r in closures)
    return {
        "verdict": "🟢 GREEN — הזיהוי מלא ומדויק" if all_ok else "🟡 בדוק — שער לא-ירוק",
        "all_ok": all_ok,
        "checks": checks,
        "open_trade": (dict(open_trade) if open_trade else None),
        "today_closures": [
            {"id": r.get("id"), "dir": r.get("direction"), "entry": r.get("entry_price"),
             "exit": r.get("exit_price"), "pnl": r.get("pnl_usd"), "why": r.get("exit_reason"),
             "in": str(r.get("t_in")), "out": str(r.get("t_out"))}
            for r in closures],
        "today_pnl_usd": round(today_pnl, 2),
        "note": "read-only · אין פקודות · In:22=חימוש (לא סים/לייב); סים/לייב = is_sim",
    }
