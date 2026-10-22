#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""trade_zoom.py — zoom-in on ONE trade along Michael's six doctrine dimensions (22.10.2026):

  volume · candle size · location · time · Woodies state · pattern + tree path
  — plus: what happened before the entry, T0/T1 realisation, System-6 actions, MFE/MAE,
  what was available (hindsight exit models) and a one-line class verdict.

Michael 22.10: "לא לדבר בסכומים — לדבר לפי עסקאות ספציפיות; בכל פעם שיש משהו לא תקין לעשות זום-אין
ולמצוא איפה הפערים, הטעויות, התיקונים שהובילו לכך." Read-only on the DB (safe inside RTH).

  python3 scripts/trade_zoom.py 3582 3515                 # specific trades
  python3 scripts/trade_zoom.py --since 2026-10-19 --mode demo
  python3 scripts/trade_zoom.py --since 2026-10-19 --mode shadow --pattern TREND_STEP
  python3 scripts/trade_zoom.py --since 2026-10-19 --mode demo --md docs/reports/day_reviews/TRADE_ZOOM_2026-10-22.md

Sources: v9_trades (quality.metadata.situation = the vector the gateway saw, stop_initial),
cross_context[0].systems.tpo_system (POC/VAH/VAL/IB the system had), v9_bars_5min_woodies (+delta),
v9_woodies_signals, v9_decision_vectors (DECISION + TREE_SHADOW = the tree row), v9_trade_management_log.
Signal bar = the last 5-min bar CLOSED before entry_ts; the entry is at the open of the next bar.
"""
import os, sys, json, argparse, statistics, collections, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scripts")); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
import oracle_engine as oe
import review_lib as rl
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem")
PT = 5.0  # $ per MES point per contract

ap = argparse.ArgumentParser()
ap.add_argument("ids", nargs="*", type=int)
ap.add_argument("--since", default=None, help="IL date: all trades with entry_ts >= this date")
ap.add_argument("--until", default=None, help="IL date (exclusive)")
ap.add_argument("--mode", default=None, help="demo | live | shadow (default: demo+live)")
ap.add_argument("--pattern", default=None, help="pattern_id_at_entry substring filter")
ap.add_argument("--md", default=None, help="also write the report to this .md path")
ap.add_argument("--bars-before", type=int, default=6)
ap.add_argument("--json", default=None, help="also dump the per-trade dimension dicts to this .json path")
args = ap.parse_args()

# ── trades ───────────────────────────────────────────────────────────────────
where = []; prm = {}
if args.ids: where.append("id = any(:ids)"); prm["ids"] = args.ids
if args.since: where.append("entry_ts >= :since"); prm["since"] = dt.datetime.combine(dt.date.fromisoformat(args.since), dt.time(0, 0), IL)
if args.until: where.append("entry_ts < :until"); prm["until"] = dt.datetime.combine(dt.date.fromisoformat(args.until), dt.time(0, 0), IL)
if args.mode: where.append("mode = :mode"); prm["mode"] = args.mode
elif not args.ids: where.append("mode in ('demo','live')")
if args.pattern: where.append("pattern_id_at_entry ilike :pat"); prm["pat"] = "%%%s%%" % args.pattern
if not where: sys.exit("give trade ids or --since")
trades = read_all("""select id, mode, firing_system, direction, state, entry_ts, entry_price, stop, t1, t2, t3, t4,
  t1_hit_ts, t2_hit_ts, t3_hit_ts, stop_hit_ts, exit_ts, exit_price, exit_reason, pnl_usd, pnl_r, pnl_sierra, outcome,
  quality, cross_context, pattern_id_at_entry pat, day_type_at_entry dt_entry, session_at_entry sess
  from v9_trades where %s order by entry_ts""" % " and ".join(where), prm)
if not trades: sys.exit("no trades")

# ── bars (RTH, IL) for every day we need + the previous session of each ───────
d0 = min(t["entry_ts"] for t in trades).astimezone(IL).date() - dt.timedelta(days=12)
d1 = max(t["entry_ts"] for t in trades).astimezone(IL).date() + dt.timedelta(days=1)
bars = read_all("""select b.ts, (b.ts at time zone 'Asia/Jerusalem')::date d, (b.ts at time zone 'Asia/Jerusalem')::time t,
 b.open o, b.high h, b.low l, b.close c, b.volume v, cd.delta
 from v9_bars_5min_woodies b left join (select distinct on (ts) ts, delta from v9_bars_cumulative_delta order by ts, created_at desc) cd on cd.ts=b.ts
 where b.symbol='MES' and b.ts >= :a and b.ts < :b and (b.ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by b.ts""",
 {"a": dt.datetime.combine(d0, dt.time(0, 0), IL), "b": dt.datetime.combine(d1, dt.time(0, 0), IL)})
by_day = collections.defaultdict(list)
for b in bars: by_day[str(b["d"])].append(b)
days = [d for d in sorted(by_day) if len(by_day[d]) >= 30]

def prev_session(d):
    p = [x for x in days if x < d]
    return p[-1] if p else None

def prev_ctx(d):
    p = prev_session(d)
    if not p: return {}
    pb = by_day[p]
    va = oe.compute_developing_va(pb, len(pb) - 1) if len(pb) > 5 else {}
    return dict(day=p, va=va, high=max(x["h"] for x in pb), low=min(x["l"] for x in pb), close=pb[-1]["c"])

# ── per-trade context rows ───────────────────────────────────────────────────
def q_rows(sql, **p): return read_all(sql, p)

def fmt(x, n=2):
    if x is None: return "—"
    try: return ("%%.%df" % n) % float(x)
    except Exception: return str(x)

def hhmm(ts): return ts.astimezone(IL).strftime("%H:%M") if ts else "—"

def zoom(t):
    d = t["entry_ts"].astimezone(IL).date().isoformat()
    bs = by_day.get(d) or []
    if len(bs) < 3: return {"id": t["id"], "error": "no bars for %s" % d}
    ets = t["entry_ts"]
    # signal bar = last bar closed before entry
    i = max((k for k, b in enumerate(bs) if b["ts"] + dt.timedelta(minutes=5) <= ets), default=None)
    if i is None: i = 0
    sb = bs[i]; short = t["direction"] == "SHORT"; sgn = -1 if short else 1
    q = t["quality"] or {}; md = q.get("metadata") or {}; sit = md.get("situation") or {}
    cc = t["cross_context"]
    if isinstance(cc, str):
        try: cc = json.loads(cc)
        except Exception: cc = None
    tpo = {}
    if isinstance(cc, list) and cc and isinstance(cc[0], dict): tpo = ((cc[0].get("systems") or {}).get("tpo_system") or {})
    elif isinstance(cc, dict): tpo = ((cc.get("systems") or {}).get("tpo_system") or {})
    atr = oe.compute_atr(bs, i) or sit.get("atr_causal") or oe.compute_atr(bs, len(bs) - 1) or 6.0
    ep = float(t["entry_price"]); stop0 = md.get("stop_initial") or q.get("entry_stop") or t["stop"]
    stop0 = float(stop0) if stop0 is not None else None
    risk = abs(ep - stop0) if stop0 else None
    # 1 volume
    v = float(sb["v"] or 0); prev20 = [float(x["v"] or 0) for x in bs[max(0, i - 20):i]]; prev5 = prev20[-5:]
    vol20 = (v / statistics.mean(prev20)) if prev20 and statistics.mean(prev20) > 0 else None
    vol5 = (v / statistics.median(prev5)) if prev5 and statistics.median(prev5) > 0 else None
    deltas = [float(x["delta"]) for x in bs[:i] if x.get("delta") is not None]
    dmed = statistics.median([abs(x) for x in deltas]) if len(deltas) > 5 else None
    drat = (float(sb["delta"]) / dmed) if (sb.get("delta") is not None and dmed) else None
    # 2 candle
    rng = sb["h"] - sb["l"]; body = abs(sb["c"] - sb["o"]); cp = ((sb["c"] - sb["l"]) / rng) if rng > 0 else 0.5
    bar_dir = "up" if sb["c"] > sb["o"] else "down" if sb["c"] < sb["o"] else "flat"
    # what happened before: last-3-bar move, 6-bar range, bars since session extreme
    move3 = sb["c"] - bs[max(0, i - 3)]["c"]
    hi6 = max(x["h"] for x in bs[max(0, i - 5):i + 1]); lo6 = min(x["l"] for x in bs[max(0, i - 5):i + 1])
    sess_hi = max(x["h"] for x in bs[:i + 1]); sess_lo = min(x["l"] for x in bs[:i + 1])
    hi_i = max(range(i + 1), key=lambda k: bs[k]["h"]); lo_i = min(range(i + 1), key=lambda k: bs[k]["l"])
    # 3 location
    ib_h = tpo.get("ib_high") or max(x["h"] for x in bs[:12]); ib_l = tpo.get("ib_low") or min(x["l"] for x in bs[:12])
    poc, vah, val = tpo.get("poc"), tpo.get("vah"), tpo.get("val")
    dev = oe.compute_developing_va(bs, i) if i >= 4 else {}
    if poc is None and dev: poc, vah, val = dev.get("poc"), dev.get("vah"), dev.get("val")
    pc = prev_ctx(d); pva = pc.get("va") or {}
    zone_sys = sit.get("zone"); zone_calc = oe.classify_zone_vs_developing_va(ep, dev) if dev else None
    d_poc = (ep - poc) if poc is not None else None
    def near(lvl, tol): return lvl is not None and abs(ep - lvl) <= tol
    tol = 0.5 * atr
    loc_tags = []
    if near(poc, 2.0): loc_tags.append("על ה-POC")
    if near(vah, tol): loc_tags.append("ליד VAH")
    if near(val, tol): loc_tags.append("ליד VAL")
    if near(ib_h, tol): loc_tags.append("ליד IBH")
    if near(ib_l, tol): loc_tags.append("ליד IBL")
    if pva and near(pva.get("vah"), tol): loc_tags.append("ליד VAH-אתמול")
    if pva and near(pva.get("val"), tol): loc_tags.append("ליד VAL-אתמול")
    if pc and near(pc.get("high"), tol): loc_tags.append("ליד שיא-אתמול")
    if pc and near(pc.get("low"), tol): loc_tags.append("ליד שפל-אתמול")
    if ep >= sess_hi - 0.3 * atr: loc_tags.append("בתקרת-הסשן")
    if ep <= sess_lo + 0.3 * atr: loc_tags.append("ברצפת-הסשן")
    # edge test in the last 6 bars (did price test VAL/IBL before a long, VAH/IBH before a short)?
    edge_lvls = [x for x in ([val, ib_l] if not short else [vah, ib_h]) if x is not None]
    edge_test = any((lo6 <= lv + 0.25 * atr) if not short else (hi6 >= lv - 0.25 * atr) for lv in edge_lvls)
    # 4 time
    ph = "A" if i < 3 else "B" if i < 12 else "C" if i < 54 else "D"
    # 5 woodies
    w = q_rows("""select ts, signal_type, direction, cci_14, cci_prev, czi_state, swi_state, strength, persistence_bars
      from v9_woodies_signals where ts > :a and ts <= :b order by ts""", a=ets - dt.timedelta(minutes=30), b=ets + dt.timedelta(seconds=5))
    w_last = w[-1] if w else None
    w_same = [x for x in w if x["direction"] == t["direction"]]; w_opp = [x for x in w if x["direction"] and x["direction"] != t["direction"]]
    # 6 pattern + tree
    dv = q_rows("""select ts, kind, classification, direction, entry, phase, blocked_by, reason from v9_decision_vectors
      where kind in ('DECISION','TREE_SHADOW') and ts between :a and :b order by ts""", a=ets - dt.timedelta(minutes=10), b=ets + dt.timedelta(seconds=20))
    mine = [r for r in dv if abs((r["ts"] - ets).total_seconds()) <= 20 and r["direction"] == t["direction"]]
    tree = [r for r in mine if r["kind"] == "TREE_SHADOW"]
    tree_row = (tree[-1]["reason"] or "") if tree else None
    others = [r for r in dv if r["kind"] == "DECISION" and r not in mine]
    # management log
    ml = q_rows("select ts, action, value from v9_trade_management_log where trade_id = :id order by ts", id=t["id"])
    acts = collections.Counter(r["action"] for r in ml)
    be_moves = [r for r in ml if r["action"] in ("SMART_BE", "BE_RULE", "BE_AFTER_T1", "SWING_TRAIL", "NORMAL_DAY_RUNNER", "TARGET_REALISM")]
    t0_hit = acts.get("T0_HIT", 0) > 0; t1_hit = bool(t["t1_hit_ts"]) or acts.get("T1_HIT", 0) > 0
    # MFE / MAE from the entry bar to the exit bar (highs/lows), in pts and R
    xts = t["exit_ts"] or bs[-1]["ts"]
    path = [x for x in bs[i + 1:] if x["ts"] <= xts] or bs[i + 1:i + 2]
    mfe = max((((ep - x["l"]) if short else (x["h"] - ep)) for x in path), default=0.0)
    mae = max((((x["h"] - ep) if short else (ep - x["l"])) for x in path), default=0.0)
    mins = ((t["exit_ts"] - ets).total_seconds() / 60) if t["exit_ts"] else None
    # did T1 trade later in the session (after the exit)?
    t1 = t["t1"]; t1_later = None
    if t1 is not None and t["exit_ts"]:
        after = [x for x in bs if x["ts"] > t["exit_ts"]]
        hit = next((x for x in after if ((x["l"] <= t1) if short else (x["h"] >= t1))), None)
        t1_later = hhmm(hit["ts"]) if hit else "לא"
    # hindsight exit models from the signal bar (review_lib: stop 1×ATR, t1 1.5×ATR, chandelier, BE, time-stop)
    em = rl.exit_models(bs, i, short, atr) if i + 1 < len(bs) else {}
    # ── class flags (the C3 classes) ──
    flags = []
    # the edge was tested but the entry is ≥1 ATR away from the tested extreme = bought/sold the middle after the test
    late = (sgn * (ep - (lo6 if not short else hi6))) >= 1.0 * atr
    in_va = (zone_sys in ("mid_value", "IN_VA") or zone_calc == "IN_VA") and d_poc is not None and abs(d_poc) <= 7
    if in_va and (not edge_test or late): flags.append("MID_NO_EDGE_TEST" if not edge_test else "MID_LATE_AFTER_TEST")
    sb_body = sgn * (sb["c"] - sb["o"])
    chase = (sgn * move3 >= 1.0 * atr or sb_body >= 0.8 * atr) and ((ep >= hi6 - 0.3 * atr) if not short else (ep <= lo6 + 0.3 * atr))
    if chase: flags.append("CHASE_AFTER_PUSH")
    # fading INTO a fresh push: the last 6 bars moved ≥1.5 ATR against the entry (or one of the last 2 bars ranged
    # ≥1.5 ATR) and the 6-bar extreme on the entry's far side is 0–1 bars old = no pause, no test yet
    push6 = sb["c"] - bs[max(0, i - 6)]["c"]
    far_ext_i = max(range(max(0, i - 5), i + 1), key=lambda k: bs[k]["h"]) if short else min(range(max(0, i - 5), i + 1), key=lambda k: bs[k]["l"])
    big2 = max(x["h"] - x["l"] for x in bs[max(0, i - 1):i + 1])
    fade_push = (i - far_ext_i) <= 1 and ((-sgn * push6) >= 1.5 * atr or big2 >= 1.5 * atr)
    if fade_push: flags.append("FADE_INTO_PUSH")
    if rng >= 2.5 * atr and (vol20 or 0) >= 2.5: flags.append("CLIMAX_BAR_ENTRY")
    if t1 is not None and risk and abs(t1 - ep) / risk >= 2.5: flags.append("T1_FAR")
    sw3 = min(x["l"] for x in bs[max(0, i - 2):i + 1]) if not short else max(x["h"] for x in bs[max(0, i - 2):i + 1])
    micro = risk is not None and (risk <= 0.6 * atr or ((stop0 > sw3 - 0.25) if not short else (stop0 < sw3 + 0.25)))
    if micro: flags.append("STOP_IN_MICRO_SWING")
    open_edge = ph in ("A", "B") and str(t["pat"] or "").startswith("OPENING") and ((ep >= sess_hi - 0.3 * atr) if not short else (ep <= sess_lo + 0.3 * atr))
    if open_edge: flags.append("OPENING_AT_EXTREME")
    ext = sit.get("extension"); counter_ext = sit.get("ib_locked") and ext in ("up", "down") and ((ext == "up" and short) or (ext == "down" and not short))
    if counter_ext: flags.append("COUNTER_ACCEPTED_EXT")
    s6gap = (not t1_hit) and risk and mfe >= 1.5 * risk and not be_moves and (t["exit_reason"] or "").upper().startswith(("STOP", "FLAT", "EOD", "TIME"))
    if s6gap: flags.append("S6_NO_T1_GIVEBACK")
    return dict(id=t["id"], mode=t["mode"], day=d, time=hhmm(ets), pat=t["pat"], dir=t["direction"], sys=t["firing_system"], ep=ep, stop0=stop0, risk=risk,
                stop_now=t["stop"], t1=t["t1"], t2=t["t2"], t3=t["t3"], t1_r=((abs(t1 - ep) / risk) if (t1 is not None and risk) else None), has_t0=md.get("has_t0"),
                contracts=q.get("contracts") or md.get("contracts"), exit=t["exit_reason"], exit_price=t["exit_price"], exit_time=hhmm(t["exit_ts"]), pnl=t["pnl_usd"], pnl_r=t["pnl_r"], mins=mins,
                i=i, sig_bar=sb, bars=bs[max(0, i - args.bars_before):min(len(bs), i + 3)], atr=atr,
                vol=v, vol20=vol20, vol5=vol5, delta=sb.get("delta"), drat=drat, sys_vol_ratio=sit.get("vol_ratio"),
                rng=rng, body=body, cp=cp, bar_dir=bar_dir, move3=move3, hi6=hi6, lo6=lo6, sess_hi=sess_hi, sess_lo=sess_lo, bars_since_hi=i - hi_i, bars_since_lo=i - lo_i,
                ib_h=ib_h, ib_l=ib_l, poc=poc, vah=vah, val=val, d_poc=d_poc, zone_sys=zone_sys, zone_calc=zone_calc, loc_tags=loc_tags, edge_test=edge_test,
                prev=pc, ph=ph, ph_sys=sit.get("phase"), day_type=sit.get("day_type") or t["dt_entry"], dt_conf=sit.get("day_type_conf"), opening=sit.get("opening_type"),
                dir_hint=sit.get("dir_hint"), ext=ext, ext_pts=sit.get("extension_pts"), ib_locked=sit.get("ib_locked"), ib_width=sit.get("ib_width"),
                w=w, w_last=w_last, w_same=len(w_same), w_opp=len(w_opp), tree_row=tree_row, tree_rows=tree, others=others, ml=ml, acts=dict(acts), be_moves=be_moves,
                t0_hit=t0_hit, t1_hit=t1_hit, mfe=mfe, mae=mae, mfe_r=(mfe / risk) if risk else None, mae_r=(mae / risk) if risk else None, t1_later=t1_later, em=em, flags=flags)

ZONE_HEB = {"mid_value": "אמצע-הערך", "IN_VA": "בתוך הערך", "near_vah": "ליד VAH", "near_val": "ליד VAL", "above_value": "מעל הערך", "below_value": "מתחת לערך",
            "ABOVE_VA": "מעל הערך", "BELOW_VA": "מתחת לערך", "AT_POC": "על ה-POC"}
FLAG_HEB = {"MID_NO_EDGE_TEST": "אמצע-הטווח בלי מבחן-קצה", "MID_LATE_AFTER_TEST": "אמצע-הטווח — הקצה נבחן אבל הכניסה ≥1 ATR ממנו (קנה/מכר את האמצע)",
            "CHASE_AFTER_PUSH": "רדיפת-דחיפה (כניסה בקצה המהלך)", "FADE_INTO_PUSH": "פייד לתוך דחיפה טרייה (≥1.5 ATR בלי השהיה/מבחן)",
            "CLIMAX_BAR_ENTRY": "כניסה על בר-קליימקס (≥2.5 ATR, ווליום ≥2.5×)", "T1_FAR": "T1 רחוק (≥2.5R)",
            "STOP_IN_MICRO_SWING": "סטופ במיקרו-סווינג (≤0.6 ATR / בתוך 3 הברים)",
            "OPENING_AT_EXTREME": "פתיחה — קנייה/מכירה בקיצון הסשן", "COUNTER_ACCEPTED_EXT": "נגד הרחבה מקובלת (IB נעול)", "S6_NO_T1_GIVEBACK": "מערכת 6: ≥1.5R בלי T1 — הוחזר לשוק"}

def render(z):
    if "error" in z: return "## #%s — %s\n" % (z["id"], z["error"])
    L = []
    pnl = z["pnl"]; pr = z["pnl_r"]
    L.append("## #%d · %s %s · %s %s · %s · %s%s · %s $%s%s" % (z["id"], z["day"], z["time"], z["pat"], z["dir"], z["mode"],
             ("%dc " % z["contracts"]) if z["contracts"] else "", "S%s" % z["sys"] if z["sys"] else "", z["exit"] or z.get("state", "?"), fmt(pnl, 2),
             (" (%sR)" % fmt(pr, 2)) if pr is not None else ""))
    L.append("")
    L.append("| ממד | מה היה | קריאה |")
    L.append("|---|---|---|")
    sb = z["sig_bar"]
    L.append("| כניסה · סטופ · יעדים | כניסה %s · סטופ-מקורי %s (%s נק׳ = R) · T1 %s (%sR) · T2 %s · T3 %s%s | %s |" % (
        fmt(z["ep"]), fmt(z["stop0"]), fmt(z["risk"]), fmt(z["t1"]), fmt(z["t1_r"], 1), fmt(z["t2"]), fmt(z["t3"]), " · T0 ✓" if z["has_t0"] else "",
        ("T1 ✅" if z["t1_hit"] else "T1 ✗") + (" · T0 ✓" if z["t0_hit"] else "")))
    L.append("| 1 ווליום (בר-הסיגנל %s) | %s · ×%s מול ממוצע-20 · ×%s מול חציון-5 · דלתא %s (×%s מהחציון) · vol_ratio של המערכת %s | %s |" % (
        str(sb["t"])[:5], fmt(z["vol"], 0), fmt(z["vol20"]), fmt(z["vol5"]), fmt(z["delta"], 0), fmt(z["drat"]), fmt(z["sys_vol_ratio"]),
        "ווליום-אישור ✓" if (z["vol20"] or 0) >= 1.3 else "ווליום רגיל/נמוך"))
    L.append("| 2 גודל-הנר | טווח %s = %s×ATR14(%s) · גוף %s = %s×ATR · סגירה ב-%d%% מהטווח · בר %s | %s |" % (
        fmt(z["rng"]), fmt(z["rng"] / z["atr"], 2), fmt(z["atr"]), fmt(z["body"]), fmt(z["body"] / z["atr"], 2), int(z["cp"] * 100), z["bar_dir"],
        "טריגר חזק" if ((z["cp"] >= 0.7 and z["dir"] == "LONG") or (z["cp"] <= 0.3 and z["dir"] == "SHORT")) else "טריגר חלש (סגירה לא בקצה הנכון)"))
    L.append("| לפני הכניסה | 3 ברים: %+.2f נק׳ (%s×ATR) · טווח-6 %s–%s · שיא-סשן %s (%d ברים) · שפל-סשן %s (%d ברים) | %s |" % (
        z["move3"], fmt(abs(z["move3"]) / z["atr"], 1), fmt(z["lo6"]), fmt(z["hi6"]), fmt(z["sess_hi"]), z["bars_since_hi"], fmt(z["sess_lo"]), z["bars_since_lo"],
        "כניסה בקצה המהלך" if "CHASE_AFTER_PUSH" in z["flags"] else ("אחרי פולבק/מבחן" if z["edge_test"] else "המשך/ללא מבחן")))
    pv = z["prev"].get("va") or {}
    L.append("| 3 מיקום | POC %s (Δ%s) · VAH %s · VAL %s · IB %s–%s%s · אתמול VA %s–%s, H/L %s/%s · אזור: מערכת=%s, חישוב=%s · %s | %s |" % (
        fmt(z["poc"]), fmt(z["d_poc"]), fmt(z["vah"]), fmt(z["val"]), fmt(z["ib_l"]), fmt(z["ib_h"]), (" (נעול, %s)" % fmt(z["ib_width"], 1)) if z["ib_locked"] else "",
        fmt(pv.get("val")), fmt(pv.get("vah")), fmt(z["prev"].get("high")), fmt(z["prev"].get("low")), ZONE_HEB.get(z["zone_sys"], z["zone_sys"]), ZONE_HEB.get(z["zone_calc"], z["zone_calc"]),
        ", ".join(z["loc_tags"]) or "—", "מבחן-קצה ב-6 הברים ✓" if z["edge_test"] else "בלי מבחן-קצה"))
    L.append("| 4 זמן | שלב %s (בר %d של הסשן; המערכת: %s) · סוג-יום %s (conf %s) · פתיחה %s · dir_hint %s · הרחבה %s (%s נק׳) | %s |" % (
        z["ph"], z["i"], z["ph_sys"] or "—", z["day_type"] or "—", fmt(z["dt_conf"]), z["opening"] or "—", z["dir_hint"] or "—", z["ext"] or "—", fmt(z["ext_pts"], 1),
        ("עם ההרחבה" if (z["ext"] == "up" and z["dir"] == "LONG") or (z["ext"] == "down" and z["dir"] == "SHORT") else ("נגד ההרחבה ⚠" if z["ext"] in ("up", "down") else "אין הרחבה"))))
    wl = z["w_last"]
    L.append("| 5 וודי | %s · ב-30 הדק׳ לפני: %d סיגנלים (%d עם הכיוון, %d נגד) | %s |" % (
        ("אחרון %s %s %s · CCI %s (קודם %s) · CZI %s · SWI %s" % (hhmm(wl["ts"]), wl["signal_type"], wl["direction"] or "", fmt(wl["cci_14"], 0), fmt(wl["cci_prev"], 0), wl["czi_state"] or "—", wl["swi_state"] or "—")) if wl else "אין סיגנל-וודי ב-30 הדק׳",
        len(z["w"]), z["w_same"], z["w_opp"], ("וודי עם הכיוון" if (wl and wl["direction"] == z["dir"]) else ("וודי נגד ⚠" if (wl and wl["direction"]) else "וודי שותק"))))
    L.append("| 6 תבנית + מסלול-עץ | %s %s · שורת-עץ: %s · עוד החלטות ב-10 הדק׳: %s | %s |" % (
        z["pat"], z["dir"], z["tree_row"] or "— (אין TREE_SHADOW)",
        ", ".join("%s %s %s%s" % (hhmm(r["ts"]), r["classification"], r["direction"], (" [%s]" % r["blocked_by"]) if r["blocked_by"] else "") for r in z["others"][-4:]) or "אין",
        "שורת-עץ allow" if (z["tree_row"] or "").find("allow") >= 0 else "—"))
    acts = ", ".join("%s×%d" % (k, v) for k, v in sorted(z["acts"].items())) or "אין רשומות"
    bm = "; ".join("%s %s %s" % (hhmm(r["ts"]), r["action"], json.dumps(r["value"], ensure_ascii=False)[:90]) for r in z["be_moves"][:4]) or "לא הזיזה סטופ"
    L.append("| מערכת 6 | פעולות: %s · הזזות: %s | %s |" % (acts, bm, "נגעה" if z["be_moves"] else ("לא נגעה" if not z["t1_hit"] else "—")))
    em = z["em"] or {}
    L.append("| תוצאה | MFE %s נק׳ (%sR) · MAE %s נק׳ (%sR) · יציאה %s @%s אחרי %s דק׳ · T1 אחרי היציאה: %s | בראייה-מלאה מהבר הזה (סטופ 1×ATR): T1-קבוע %s · טרייל %s · BE %s · מקס %s נק׳ |" % (
        fmt(z["mfe"]), fmt(z["mfe_r"], 2), fmt(z["mae"]), fmt(z["mae_r"], 2), z["exit"] or "—", fmt(z["exit_price"]), fmt(z["mins"], 0), z["t1_later"] or "—",
        fmt(em.get("t1")), fmt(em.get("trail")), fmt(em.get("be")), fmt(em.get("max"))))
    L.append("| **מחלקות** | %s | |" % (" · ".join("**%s** (%s)" % (f, FLAG_HEB.get(f, f)) for f in z["flags"]) or "ללא דגל אוטומטי — לבדוק ביד"))
    L.append("")
    L.append("ברים (IL · O/H/L/C · V · Δ) — בר-הסיגנל מסומן ◀:")
    L.append("")
    L.append("| שעה | O | H | L | C | V | Δ | |")
    L.append("|---|---|---|---|---|---|---|---|")
    for b in z["bars"]:
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (str(b["t"])[:5], fmt(b["o"]), fmt(b["h"]), fmt(b["l"]), fmt(b["c"]), fmt(b["v"], 0), fmt(b["delta"], 0), "◀" if b["ts"] == sb["ts"] else ""))
    L.append("")
    return "\n".join(L)

out = []; zs = []
for t in trades:
    try: z = zoom(t)
    except Exception as e:
        import traceback; z = {"id": t["id"], "error": "zoom failed: %r\n%s" % (e, traceback.format_exc()[-600:])}
    zs.append(z); out.append(render(z))
# summary by class
cnt = collections.Counter(); pnl_by = collections.defaultdict(float); ids_by = collections.defaultdict(list)
for z in zs:
    for f in z.get("flags", []): cnt[f] += 1; pnl_by[f] += float(z.get("pnl") or 0); ids_by[f].append(z["id"])
head = ["# TRADE ZOOM — %d trades · generated %s IL" % (len(zs), dt.datetime.now(IL).strftime("%Y-%m-%d %H:%M")), "",
        "| מחלקה | עסקאות | Σ$ | ids |", "|---|---|---|---|"]
for f, n in cnt.most_common():
    head.append("| %s (%s) | %d | %s | %s |" % (f, FLAG_HEB.get(f, f), n, fmt(pnl_by[f], 2), ", ".join(str(i) for i in ids_by[f])))
head.append("")
txt = "\n".join(head + out)
print(txt)
if args.md:
    os.makedirs(os.path.dirname(args.md), exist_ok=True)
    open(args.md, "w", encoding="utf-8").write(txt + "\n")
    print("wrote", args.md, file=sys.stderr)
if args.json:
    def _j(o):
        if isinstance(o, (dt.datetime, dt.date, dt.time)): return o.isoformat()
        if isinstance(o, dt.timedelta): return o.total_seconds()
        try: return float(o)
        except Exception: return str(o)
    json.dump([{k: v for k, v in z.items() if k not in ("bars", "sig_bar", "w", "others", "ml", "be_moves", "tree_rows", "em")} for z in zs], open(args.json, "w"), ensure_ascii=False, default=_j, indent=1)
