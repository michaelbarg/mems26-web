#!/usr/bin/env python3
"""N9-hot — Sierra-sim FILL layer for the day-type × pattern matrix (2026-07-17).

Builds ON TOP of scripts/sim_matrix.py (cowork's logic matrix: 104 cells,
KEEP=61/SKIP=43, management invariants — decision layer PROVEN). This driver
proves the *fill* layer per day type on the REAL Sierra sim (is_sim=1):

  per day_type:
    DAY_TYPE_MANUAL_OVERRIDE=<today-ET>:<day_type> → backend restart →
    fire a FULL-cell representative + a REDUCED-cell representative
    (pre-RTH the session gate forces debug_gateway_fire's FIRED_DIRECT
    path = _execute_demo → real op=PLACE → Sierra sim fills; the gate
    DECISIONS are already covered by the logic matrix) →
    verify: entry fill (qty>0) · OCO pairs (working=2×qty) · MODIFY_STOP
    moves ALL stops · FLATTEN → flat · registration: trade_command mtime ·
    fills-journal ENTRY · v9_trades row · /trades/recent API.

SAFETY GATE (hard): is_sim==1 read fresh from sierra_state.json before EVERY
fire; abort the whole run otherwise. Never op=EXIT. Sierra back to LIVE only
in the N6 morning protocol.

The remaining KEEP cells share this exact fill path (command_from_setup →
DLL op=PLACE); they inherit fill-truth from their day-type's proof cells —
marked "✅ נתיב-משותף" in the report. Negatives (SKIP cells) are decision-layer
and remain covered by the logic matrix (43 blocks + 6 counter-trend).

Run:  .venv/bin/python3 scripts/sim_matrix_e2e.py [--day-types A,B] [--keep-env]
Out:  appends fill-truth table to docs/reports/SIM_MATRIX_<date>.md + OPS_LOG.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from scripts.ops_log import log_event  # noqa: E402

EXPORT = Path("/Users/michael/SierraChart_Data/v9_export")
ENV_PATH = REPO / ".env"
API = "http://localhost:8000"
DAY_TYPES = ["Trend_Normal", "Trend_DD", "Variation", "Normal",
             "Neutral_Center", "Neutral_Extreme"]  # Nontrend/Nonconviction: all-SKIP → no fill cells


def _env_token() -> str:
    for line in ENV_PATH.read_text().splitlines():
        if line.startswith("BRIDGE_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no BRIDGE_TOKEN")


def _sierra():
    return json.loads((EXPORT / "sierra_state.json").read_text() or "{}")


def _require_sim(stage: str):
    s = _sierra()
    if s.get("is_sim") not in (1, True):
        log_event("sim_matrix_e2e", "CRITICAL", f"is_sim!=1 at {stage} — ABORT")
        raise SystemExit(f"SAFETY ABORT: is_sim={s.get('is_sim')} at {stage}")
    return s


def _http(method: str, path: str, body: dict | None = None, token: str | None = None, timeout=12):
    req = urllib.request.Request(API + path, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode()
    with urllib.request.urlopen(req, data, timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")


def _set_override(day_type: str):
    today = dt.datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    txt = ENV_PATH.read_text()
    line = f"DAY_TYPE_MANUAL_OVERRIDE={today}:{day_type}"
    if re.search(r"^DAY_TYPE_MANUAL_OVERRIDE=.*$", txt, re.M):
        txt = re.sub(r"^DAY_TYPE_MANUAL_OVERRIDE=.*$", line, txt, flags=re.M)
    else:
        txt += f"\n{line}\n"
    ENV_PATH.write_text(txt)
    return line


def _restart_backend():
    uid = subprocess.run(["id", "-u"], capture_output=True, text=True).stdout.strip()
    subprocess.run(["launchctl", "kickstart", "-k", f"gui/{uid}/com.mems26.backend"], check=True)
    for _ in range(30):
        time.sleep(2)
        try:
            if _http("GET", "/api/v9/health").get("status") == "ok":
                return True
        except Exception:
            pass
    return False


def _flat(token: str, trade_id: str = "") -> bool:
    _http("POST", "/api/v9/trade/command", {"action": "FLATTEN_ACCOUNT", "trade_id": trade_id}, token)
    for _ in range(10):
        time.sleep(2)
        s = _sierra()
        if s.get("position_qty") == 0 and s.get("working_orders", 0) == 0:
            return True
    return False


def _fire_cell(day_type: str, pattern: str, sizing: str, token: str) -> dict:
    """One E2E fill cycle. Returns evidence dict."""
    ev = {"day_type": day_type, "pattern": pattern, "sizing": sizing, "steps": {}}
    _require_sim(f"fire {day_type}/{pattern}")
    cmd_file = EXPORT / "trade_command.json"
    m0 = cmd_file.stat().st_mtime if cmd_file.exists() else 0

    r = _http("POST",
              f"/api/v9/trade/debug_gateway_fire?sizing={sizing}&direction=LONG&stop_pts=8"
              f"&classification=N9_{pattern}_{day_type[:6]}&pattern={pattern}", token=token, timeout=20)
    trade_id = str((r.get("demo_result") or {}).get("trade_id") or "")
    ev["steps"]["fired"] = r.get("status")
    ev["trade_id"] = trade_id

    # entry fill + pairs
    qty = pairs_ok = None
    for _ in range(12):
        time.sleep(2)
        s = _sierra()
        qty = s.get("position_qty", 0)
        if qty and qty > 0:
            orders = s.get("orders", [])
            pairs_ok = (s.get("working_orders") == 2 * qty == len(orders))
            break
    ev["steps"]["entry_fill_qty"] = qty
    ev["steps"]["oco_pairs"] = bool(pairs_ok)
    ev["steps"]["command_written"] = cmd_file.stat().st_mtime > m0 if cmd_file.exists() else False

    # MODIFY_STOP all stops +2 ticks
    mod_ok = False
    if qty:
        s = _sierra()
        stops = [o for o in s.get("orders", []) if o.get("type") in (2, 3) and o.get("bs") in (2, None) or o.get("type") == 2]
        stops = [o for o in s.get("orders", []) if o.get("type") in (2, 3)]
        ids = [o["id"] for o in stops]
        if ids:
            base = max(float(o["price"]) for o in stops)
            new_stop = round((base + 0.5) * 4) / 4
            os.environ["MEMS26_SIGNALS_DIR"] = str(EXPORT)
            from backend.v9.services.sierra_command import write_modify_stop
            write_modify_stop(trade_id=trade_id or "0", order_id=ids[0],
                              new_stop=new_stop, stop_ids=ids, mode="demo")
            for _ in range(6):
                time.sleep(2)
                s2 = _sierra()
                prices = {float(o["price"]) for o in s2.get("orders", []) if o.get("type") in (2, 3)}
                if prices == {new_stop}:
                    mod_ok = True
                    break
    ev["steps"]["modify_stop_all"] = mod_ok

    # FLATTEN + flat
    ev["steps"]["flatten_flat"] = _flat(token, trade_id)

    # registration
    time.sleep(2)
    jrn = (EXPORT / "trade_fills_journal.jsonl")
    tail = jrn.read_text().splitlines()[-8:] if jrn.exists() else []
    ev["steps"]["journal_entry"] = any('"ENTRY"' in l for l in tail)
    try:
        rec = _http("GET", "/api/v9/trades/recent", token=token)
        ev["steps"]["v9_trades_api"] = bool(rec and str(rec[0].get("id")) == trade_id)
    except Exception as e:
        ev["steps"]["v9_trades_api"] = f"ERR {e}"
    ok = all(v is True or (isinstance(v, int) and v > 0) or v == "FIRED_DIRECT" or v == "FIRED"
             for v in ev["steps"].values())
    ev["ok"] = ok
    log_event("sim_matrix_e2e", "INFO" if ok else "ERROR",
              f"{day_type}/{pattern}/{sizing}: {'PASS' if ok else 'FAIL'} {ev['steps']}")
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day-types", default=",".join(DAY_TYPES))
    args = ap.parse_args()
    token = _env_token()
    _require_sim("start")

    # KEEP cells from the live playbook config
    from backend.v9.systems.daytype_playbook import decide, _cfg
    patterns = list((_cfg().get("patterns") or {}).keys())
    results = []
    for day in [d.strip() for d in args.day_types.split(",") if d.strip()]:
        full = reduced = None
        for p in patterns:
            d = decide(pattern=p, day_type=day, direction="LONG",
                       trend_state="BLUE" if day in ("Trend_Normal", "Trend_DD", "Variation") else "GRAY")
            if d.allow:
                mode = getattr(d, "mode", "FULL")
                if mode == "FULL" and full is None:
                    full = p
                elif mode != "FULL" and reduced is None:
                    reduced = p
            if full and reduced:
                break
        line = _set_override(day)
        log_event("sim_matrix_e2e", "INFO", f"override set: {line}")
        if not _restart_backend():
            log_event("sim_matrix_e2e", "CRITICAL", f"backend restart failed at {day}")
            raise SystemExit("restart failed")
        for pat, sz in ((full, "full"), (reduced, "half")):
            if pat:
                results.append(_fire_cell(day, pat, sz, token))

    # append fill-truth to the matrix report
    out = REPO / "docs/reports" / f"SIM_MATRIX_{dt.date.today().isoformat()}.md"
    lines = ["", "## N9-hot — שכבת-fill על Sierra-סים (E2E, is_sim=1)", "",
             "| סוג-יום | תבנית | sizing | ירי | entry | זוגות-OCO | MODIFY×all | FLATTEN | journal | v9_trades | פסק |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for ev in results:
        s = ev["steps"]
        lines.append("| {day_type} | {pattern} | {sizing} | {f} | {q} | {p} | {m} | {fl} | {j} | {v} | {ok} |".format(
            day_type=ev["day_type"], pattern=ev["pattern"], sizing=ev["sizing"],
            f=s.get("fired"), q=s.get("entry_fill_qty"), p="✅" if s.get("oco_pairs") else "❌",
            m="✅" if s.get("modify_stop_all") else "❌", fl="✅" if s.get("flatten_flat") else "❌",
            j="✅" if s.get("journal_entry") else "❌", v="✅" if s.get("v9_trades_api") is True else s.get("v9_trades_api"),
            ok="✅" if ev["ok"] else "❌"))
    lines.append("")
    lines.append("שאר תאי-ה-KEEP חולקים נתיב-fill זהה (command_from_setup→op=PLACE→OCO) — **✅ נתיב-משותף** מכוח תא-ההוכחה של סוג-היום שלהם. שליליים (SKIP/קאונטר) מכוסים במטריצת-הלוגיקה (43+6).")
    with open(out, "a") as f:
        f.write("\n".join(lines) + "\n")
    n_ok = sum(1 for e in results if e["ok"])
    print(f"E2E cells: {n_ok}/{len(results)} PASS → {out}")
    log_event("sim_matrix_e2e", "INFO", f"N9-hot done: {n_ok}/{len(results)} PASS")
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
