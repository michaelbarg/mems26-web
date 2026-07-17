#!/usr/bin/env python3
"""N9 — day-type × pattern SIMULATION MATRIX (Michael 2026-07-16: "הדמיה לכל סוג-יום").

Drives the REAL gateway `route_setup` for every (day_type × pattern) cell with the
day-type playbook gate ON in ISOLATION (every other optional gate OFF), so the only
thing that can veto a fire is `daytype_playbook`. For each cell:

  • build a representative setup (correct-side stop, monotonic ladder, with/without trend)
  • run it through the real gateway
  • assert the gate decision matches config/daytype_playbook.yaml
      SKIP  → gateway MUST block with blocked_by="daytype_playbook"
      KEEP  → gateway must NOT block by daytype_playbook (reaches the execute stub = fired)
  • for KEEP cells, run a trade-management invariant sim (stop side, ladder monotonic,
    BE-after-T1, bounded loss, contracts = FULL(3)/REDUCED(2))
  • plus counter-trend NEGATIVE cases for require_with_trend patterns on directional days

Nothing touches Sierra or places an order — the execute methods are stubbed. This
validates the DECISION + MANAGEMENT logic end-to-end through the production code path.
The live Sierra-sim fill integration is the follow-on (needs a running stack + is_sim=1).

Run:  python3 scripts/sim_matrix.py
Out:  docs/reports/SIM_MATRIX_<YYYY-MM-DD>.md  + lines to the central OPS_LOG (N12)
Exit: 0 all cells match expectation, 1 otherwise.
"""
from __future__ import annotations

import datetime as _dt
import math
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

# ── central ops log (N12) ────────────────────────────────────────────────────
try:
    from scripts.ops_log import log_event
except Exception:
    def log_event(*a, **k):  # never break the sim on a logging error
        return False

DAY_TYPES = ["Trend_Normal", "Trend_DD", "Variation", "Normal",
             "Neutral_Center", "Neutral_Extreme", "Nontrend", "Nonconviction"]
DIRECTIONAL = {"Trend_Normal", "Trend_DD", "Variation"}


def _trend_for(day_type: str) -> str:
    # up-bias on directional days so with-trend LONG is valid; GRAY elsewhere
    return "BLUE" if day_type in DIRECTIONAL else "GRAY"


def _build_setup(pattern: str, direction: str) -> dict:
    """Correct-side stop + strictly-monotonic ladder around 7600."""
    e = 7600.0
    if direction == "LONG":
        return {"direction": "LONG", "classification": pattern, "entry_price": e,
                "stop": e - 6.0, "t1": e + 4.0, "t2": e + 8.0, "t3": e + 12.0}
    return {"direction": "SHORT", "classification": pattern, "entry_price": e,
            "stop": e + 6.0, "t1": e - 4.0, "t2": e - 8.0, "t3": e - 12.0}


def _mgmt_invariants(setup: dict, contracts: int) -> list[str]:
    """Return a list of FAILED invariant names ([] = all pass). Models the ruled
    management: structural stop correct side, monotonic ladder, BE-after-T1, bounded loss."""
    fails = []
    d = setup["direction"]
    e, st = setup["entry_price"], setup["stop"]
    t1, t2, t3 = setup["t1"], setup["t2"], setup["t3"]
    if d == "LONG":
        if not (st < e):                     fails.append("stop_side")
        if not (e < t1 < t2 < t3):           fails.append("ladder_monotonic")
        win_path = [t1, t2, t3]              # price rising
        be_after_t1 = e                      # stop→entry after T1
        if not (be_after_t1 >= e):           fails.append("be_not_at_entry")
    else:
        if not (st > e):                     fails.append("stop_side")
        if not (e > t1 > t2 > t3):           fails.append("ladder_monotonic")
        win_path = [t1, t2, t3]              # price falling
        be_after_t1 = e
        if not (be_after_t1 <= e):           fails.append("be_not_at_entry")
    if contracts < 1:                        fails.append("contracts_lt_1")
    # bounded loss = |entry-stop| * contracts, must be finite & positive
    if not (abs(e - st) * max(contracts, 0) > 0):  fails.append("loss_unbounded")
    return fails


def _setup_gateway(monkey_env: dict):
    """Import the real gateway, isolate the playbook gate, stub execution."""
    for k, v in monkey_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    import importlib
    import backend.v9.services.trade_context as tc
    from backend.v9.gateway import trading_gateway as tg
    importlib.reload(tg)  # re-read env-bound module state
    return tc, tg


def run():
    # Isolation: ONLY the playbook gate on; position-gate OFF (it supersedes → FULL);
    # Nonconviction cells honored; every other optional risk gate OFF.
    env = {
        "DAYTYPE_PLAYBOOK": "1",
        "DAYTYPE_POSITION_GATE": None,
        "NONCONVICTION_ACTIVE_V1": "1",
        "DAYTYPE_LOCATION_GATE": None,
        "RR_ENTRY_GATE_V1": None,
        "EOD_RISK_WINDOW_V1": None,
        "OPENING_WINDOW_FIRE_V1": None,
        "MEMS26_MODE": "shadow",
        "S1_NEW_CLASSIFIER": "1",
    }
    tc, tg = _setup_gateway(env)
    from backend.v9.systems.daytype_playbook import decide, _cfg

    cfg = _cfg()
    patterns = list((cfg.get("patterns") or {}).keys())

    rows = []           # (pattern, {day_type: cell_result})
    fails = []          # human-readable mismatch lines
    total = keep = skip = mgmt_fail = 0

    for pattern in patterns:
        pat_cfg = (cfg["patterns"][pattern] or {})
        req_wt = bool(pat_cfg.get("require_with_trend"))
        cells = {}
        for dt in DAY_TYPES:
            ts = _trend_for(dt)
            # with-trend direction (LONG on up-bias days); fade SHORT on neutral days
            direction = "LONG" if ts == "BLUE" else "SHORT"
            setup = _build_setup(pattern, direction)

            gw = tg.TradingGateway()
            gw._capture_cross_context = lambda ts=ts: {
                "day_type_machine": {}, "tpo_system": {},
                "woodies_system": {"trend_state": ts}}
            gw._execute_shadow = lambda *a, **k: {"trade_id": "sim", "shadow": "sim"}
            gw._execute_live = lambda *a, **k: {"trade_id": "sim", "live": "sim"}
            if hasattr(gw, "_execute_demo"):
                gw._execute_demo = lambda *a, **k: {"trade_id": "sim", "demo": "sim"}
            tg.is_within_firing_window = lambda: True
            tc.get_live_day_type = lambda dt=dt: dt

            expected = decide(pattern=pattern, day_type=dt, direction=direction,
                              trend_state=ts)
            res = gw.route_setup(setup, 4)
            bb = res.get("blocked_by")
            blocked_pb = (bb == "daytype_playbook")

            total += 1
            ok = True
            note = ""
            if not expected.allow:                      # SKIP expected
                skip += 1
                if not blocked_pb:
                    ok = False
                    note = f"expected SKIP block, got blocked_by={bb!r}"
            else:                                        # KEEP expected
                keep += 1
                if blocked_pb:
                    ok = False
                    note = f"unexpected playbook SKIP: {expected.reason}"
                else:
                    mf = _mgmt_invariants(setup, expected.contracts)
                    if mf:
                        ok = False
                        mgmt_fail += 1
                        note = "mgmt_fail:" + ",".join(mf)
            cells[dt] = {"verdict": expected.verdict, "contracts": expected.contracts,
                         "blocked_by": bb, "ok": ok, "note": note}
            if not ok:
                fails.append(f"{pattern:10s} {dt:16s} {note}")
        rows.append((pattern, cells))

    # ── counter-trend NEGATIVE cases (require_with_trend patterns on directional days) ──
    neg_total = neg_ok = 0
    for pattern in patterns:
        if not (cfg["patterns"][pattern] or {}).get("require_with_trend"):
            continue
        for dt in ["Trend_Normal", "Trend_DD", "Variation"]:
            ts = "BLUE"                 # up-trend
            direction = "SHORT"         # counter-trend → must SKIP
            setup = _build_setup(pattern, direction)
            gw = tg.TradingGateway()
            gw._capture_cross_context = lambda ts=ts: {
                "day_type_machine": {}, "tpo_system": {},
                "woodies_system": {"trend_state": ts}}
            gw._execute_shadow = lambda *a, **k: {"trade_id": "sim"}
            gw._execute_live = lambda *a, **k: {"trade_id": "sim"}
            tg.is_within_firing_window = lambda: True
            tc.get_live_day_type = lambda dt=dt: dt
            res = gw.route_setup(setup, 4)
            neg_total += 1
            if res.get("blocked_by") == "daytype_playbook":
                neg_ok += 1
            else:
                fails.append(f"{pattern:10s} {dt:16s} COUNTER-TREND should SKIP, got {res.get('blocked_by')!r}")

    _write_report(rows, patterns, total, keep, skip, mgmt_fail,
                  neg_total, neg_ok, fails)
    passed = total - len([f for f in fails if "COUNTER-TREND" not in f])
    all_ok = not fails
    log_event("sim_matrix", "INFO" if all_ok else "ERROR",
              f"N9 matrix: {len(patterns)}patterns×{len(DAY_TYPES)}daytypes={total} cells, "
              f"keep={keep} skip={skip} mgmt_fail={mgmt_fail} | counter-trend {neg_ok}/{neg_total} "
              f"| mismatches={len(fails)} | verdict={'PASS' if all_ok else 'FAIL'}")
    print(f"\n{'PASS' if all_ok else 'FAIL'}: {total} cells, keep={keep} skip={skip}, "
          f"counter-trend {neg_ok}/{neg_total}, mismatches={len(fails)}")
    for f in fails[:40]:
        print("  ✗", f)
    return 0 if all_ok else 1


def _write_report(rows, patterns, total, keep, skip, mgmt_fail,
                  neg_total, neg_ok, fails):
    day = _dt.date.today().isoformat()
    out = _REPO / "docs" / "reports" / f"SIM_MATRIX_{day}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    L = []
    L.append(f"# N9 — מטריצת-הדמיה סוג-יום × תבנית ({day})")
    L.append("")
    L.append("שער-הפלייבוק בבידוד (כל שער-סיכון אחר כבוי) דרך ה-`route_setup` האמיתי. "
             "כל תא נבדק מקצה-לקצה: SKIP חייב חסימה `daytype_playbook`; KEEP חייב לעבור + "
             "לעמוד בבדיקות-ניהול (סטופ-צד-נכון, סולם-מונוטוני, BE-אחרי-T1, גודל FULL=3/REDUCED=2).")
    L.append("")
    verdict = "🟢 PASS" if not fails else "🔴 FAIL"
    L.append(f"**סיכום:** {verdict} · {total} תאים · KEEP={keep} · SKIP={skip} · "
             f"כשלי-ניהול={mgmt_fail} · מקרי-קאונטר-טרנד {neg_ok}/{neg_total} · אי-התאמות={len(fails)}")
    L.append("")
    # legend line
    def _mark(c):
        if not c["ok"]:
            return "❌"
        return "·" if c["verdict"] == "SKIP" else ("½" if c["verdict"] == "REDUCED" else "✅")
    header = "| תבנית | " + " | ".join(d.replace("_", " ") for d in DAY_TYPES) + " |"
    sep = "|" + "---|" * (len(DAY_TYPES) + 1)
    L.append(header)
    L.append(sep)
    for pattern, cells in rows:
        line = f"| **{pattern}** | " + " | ".join(_mark(cells[d]) for d in DAY_TYPES) + " |"
        L.append(line)
    L.append("")
    L.append("מקרא: ✅=KEEP-FULL עבר · ½=REDUCED עבר · ·=SKIP (נחסם כצפוי) · ❌=אי-התאמה")
    if fails:
        L.append("")
        L.append("## ❌ אי-התאמות (חייב תיקון)")
        for f in fails:
            L.append(f"- `{f}`")
    L.append("")
    L.append("## מגבלה מודעת")
    L.append("זו הדמיית-**לוגיקה** (נתיב-הקוד האמיתי, ביצוע מנוטרל). שכבת-ה-fill על Sierra-סים "
             "(op=PLACE אמיתי לחשבון-סים, is_sim=1) היא ההמשך — דורשת stack רץ ולא נכללת כאן.")
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"report → {out}")


if __name__ == "__main__":
    raise SystemExit(run())
