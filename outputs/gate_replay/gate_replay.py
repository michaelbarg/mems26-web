#!/usr/bin/env python3
"""GATE_REPLAY 2026-09-07 — serial single-slot replay of the gateway candidate stream,
5 variants (V0..V4) + per-gate isolation, 10 live days 24.08→04.09. READ-ONLY.

Inputs : ~/SierraChart_Data/v9_export/decisions_archive/gateway_decisions.<date>.jsonl (+ live file)
         v9_bars_5min_woodies (bars), v9_trades (as-fired levels of routed candidates, ids only)
Sim    : entry = candidate `entry`; 5 contracts ladder (1,2,1,1) = [T0(1) T1(2) T2(1) T3(1)],
         T0 = entry±3.0; stop checked BEFORE targets on every bar (touch == fill);
         target fills only when price passes THROUGH the level (H>T / L<T);
         BE (stop→entry) from the bar after T1; None target ⇒ runner (BE stop, EOD flatten);
         flatten at the close of the 14:45 CT bar (=14:50 CT, the live SIERRA_FLAT time);
         one slot, serial by decision time; pattern_stop_cooldown re-evaluated on sim stops;
         no commissions, no slippage (broker P&L records are gross too).
Run    : cd <repo> && export PATH=... && set -a && . ./.env && set +a && python3 outputs/gate_replay/gate_replay.py
"""
import os, sys, json, glob, statistics, collections, datetime as dt
from zoneinfo import ZoneInfo
import psycopg2, psycopg2.extras

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
from backend.v9.systems import release_gate as rg  # pure; params read from env at call time

UTC = dt.timezone.utc
CT = ZoneInfo("America/Chicago")
NY = ZoneInfo("America/New_York")
DATES = ["2026-08-24", "2026-08-25", "2026-08-26", "2026-08-27", "2026-08-28",
         "2026-08-31", "2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"]
EXPORT = os.path.expanduser("~/SierraChart_Data/v9_export")
DB_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
OUT = os.path.dirname(os.path.abspath(__file__))

PT = 5.0
TICK = 0.25
T0_PTS = float(os.environ.get("T0_TARGET_PTS", "3.0"))
LADDER = {1: (1, 0, 0, 0), 2: (1, 1, 0, 0), 3: (1, 1, 1, 0), 4: (1, 1, 1, 1), 5: (1, 2, 1, 1)}
EOD_CUTOFF_CT = dt.time(14, 20)
LAST_BAR_CT = dt.time(14, 45)
DAILY_CAP = float(os.environ.get("RISK_DAILY_LOSS_CAP", "800"))
COOLDOWN_MIN, COOLDOWN_PTS = 30, 4.0
RR_HARD, RR_MIN = 0.30, 0.65

# Broker truth per live trade — $ from Sierra fills, per leg (exit−entry)×qty×$5 (FIFO-immune).
# scripts/sierra_activity_join.py --json `pnl_reconstructed` + the unattached FLATTEN fills matched
# by time/qty: 848←10730, 963←10909, 968←10922 (+T0 leg), 981←10951, 939←10813, 862←10759,
# 812/818/820←10662 (cluster Σ=+166.25, split by contract order). Day sums == REPLAY_AFTER_FIXES.
BROKER_TRADE = {809: -47.5, 812: 96.25, 818: 76.25, 820: -6.25, 822: -95.0, 824: 97.5, 828: 45.0,
                830: 103.75, 831: 52.5, 838: 107.5, 840: 56.25, 841: -70.0, 848: -72.5, 851: 201.25,
                853: 62.5, 859: 143.75, 862: 8.75, 873: -8.75, 875: -100.0, 877: 116.25, 881: 40.0,
                885: -57.5, 936: -55.0, 939: -35.0, 942: 45.0, 948: -128.75, 950: -156.25,
                953: 162.5, 963: -137.5, 968: -70.0, 971: 76.25, 981: -127.5, 987: -156.25,
                998: -125.0, 1008: 13.75, 1069: 68.75, 1073: 70.0, 1141: -143.75}
SCALE_IN_CHILDREN = {818, 820, 831, 840, 841, 853, 881, 885}
ELQ3 = {("2026-09-03", "TREND_STEP", "LONG", 7722.0), ("2026-09-03", "GB100", "LONG", 7718.25),
        ("2026-09-03", "S2_DELTA_DBL_LONG", "LONG", 7722.5)}
V3_GATES = ("cont_trend_filter", "extreme_chase_guard", "location_gate")
GATE_ORDER = ["kill_switch", "session_gate_closed", "cold_start_guard", "eod_entry_cutoff", "feed_watchdog",
              "cooldown", "suffering_side_veto", "duplicate_fire", "chop_searching", "opening_type_gate",
              "drive_exhaustion_veto", "daytype_playbook", "trend_direction_gate", "reactive_location",
              "location_gate", "daytype_position_gate", "entry_location_quality", "cont_trend_filter",
              "direction_context", "direction_compass", "multiday_veto", "lsma_flat", "day_entry_budget",
              "extreme_chase_guard", "pattern_stop_cooldown", "system7_score", "awaiting_release",
              "news_blackout", "day_direction_doctrine", "structural_targets_wrong_side",
              "entry_not_confirmed", "t1_wrong_side", "rr_hard_floor", "rr_entry_gate",
              "zone_limit_late_entry", "daily_loss_halt", "consecutive_loss_halt", "cluster_guard",
              "trading_paused"]
REL_POS = GATE_ORDER.index("awaiting_release")


def floor5(t):
    return t.replace(minute=t.minute // 5 * 5, second=0, microsecond=0)


def tick(x):
    return round(round(x / TICK) * TICK, 2)


# ───────────────────────────── data ─────────────────────────────
def connect():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def load_bars(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT ts, open, high, low, close, volume FROM v9_bars_5min_woodies
                       WHERE symbol='MES' AND ts >= '2026-08-23 00:00+00' AND ts < '2026-09-05 00:00+00'
                       ORDER BY ts""")
        bars = []
        for r in cur.fetchall():
            b = dict(r)
            b["ts"] = b["ts"].astimezone(UTC)
            b["ct"] = b["ts"].astimezone(CT)
            b["ny"] = b["ts"].astimezone(NY)
            for k in ("open", "high", "low", "close"):
                b[k] = float(b[k])
            b["volume"] = float(b["volume"] or 0)
            bars.append(b)
    return bars


def load_trades(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT id, mode, direction, entry_price, stop, t1, t2, t3, pattern_id_at_entry, day_type_at_entry,
                              entry_ts, exit_reason, quality->'metadata'->>'stop_initial' AS stop_initial,
                              quality->>'initial_stop' AS initial_stop, quality->'target_spacing_shadow'->'before' AS before,
                              quality->'metadata'->'spacing_levels' AS spacing, quality->>'has_t0' AS has_t0,
                              quality->>'contracts' AS contracts
                       FROM v9_trades WHERE entry_ts >= '2026-08-23 00:00+00' AND entry_ts < '2026-09-05 00:00+00'""")
        out = {}
        for r in cur.fetchall():
            r = dict(r)
            stop = r["stop_initial"] or r["initial_stop"] or r["stop"]
            bef = r["before"] if isinstance(r["before"], dict) else {}
            lv = {"stop": float(stop) if stop is not None else None}
            for k in ("t1", "t2", "t3"):
                v = bef.get(k) if bef.get(k) is not None else r[k]
                lv[k] = float(v) if v not in (None, 0, "0") else None
            struct = {}
            if isinstance(r["spacing"], list):
                for name, px in r["spacing"]:
                    struct[name] = float(px)
            r["levels"] = lv
            r["struct_c3"] = struct.get("struct_c3")
            r["has_t0"] = str(r["has_t0"]).lower() == "true"
            r["contracts_live"] = int(r["contracts"]) if r["contracts"] else None
            r["entry_ct"] = r["entry_ts"].astimezone(CT) if r["entry_ts"] else None
            out[int(r["id"])] = r
        return out


def load_candidates(trades):
    files = sorted(glob.glob(f"{EXPORT}/decisions_archive/gateway_decisions.2026-0[89]-*.jsonl")) + \
        [f"{EXPORT}/gateway_decisions.jsonl"]
    prio = {"live": 4, "slot": 3, "presend": 3, "blocked": 1, "policy_shadow": 0, "other": 0}
    best = {}
    raw_n = collections.Counter()
    for f in files:
        for line in open(f):
            try:
                r = json.loads(line)
            except Exception:
                continue
            ts = r.get("ts")
            if not ts or r.get("event_type") not in (None, "GATE_DECISION", "ROUTED"):
                continue
            d = ts[:10]
            if d not in DATES:
                continue
            tsd = dt.datetime.fromisoformat(ts).astimezone(UTC)
            out, lbb = r.get("outcome"), r.get("live_blocked_by")
            if out == "blocked":
                kind = "blocked"
            elif out == "live":
                kind = "live"
            elif out == "shadow_only":
                kind = {"live_slot_occupied": "slot", "pre_send_entry_guard": "presend"}.get(
                    lbb, "policy_shadow" if lbb is None else "other")
            else:
                kind = "other"
            raw_n[kind] += 1
            c = {"date": d, "ts": tsd, "ct": tsd.astimezone(CT), "system": r.get("system"),
                 "pattern": r.get("pattern") or "", "direction": (r.get("direction") or "").upper(),
                 "entry": float(r["entry"]) if r.get("entry") is not None else None,
                 "kind": kind, "blocked_by": r.get("blocked_by"), "reason": r.get("reason") or "",
                 "live_blocked_by": lbb, "trade_id": r.get("trade_id"), "levels": None,
                 "struct_c3": None, "day_type": None, "contracts_live": None, "has_t0": None,
                 "sec_in_bar": (tsd.minute % 5) * 60 + tsd.second}
            mt = r.get("mfe_track")
            if kind == "blocked":
                if isinstance(mt, dict) and mt.get("stop") is not None:
                    c["levels"] = {k: (float(mt[k]) if mt.get(k) is not None else None)
                                   for k in ("stop", "t1", "t2", "t3")}
            else:
                tid = r.get("trade_id")
                tr = trades.get(int(tid)) if isinstance(tid, (int, str)) and str(tid).isdigit() else None
                if tr and tr["levels"]["stop"] is not None:
                    c["levels"] = dict(tr["levels"])
                    c["struct_c3"] = tr["struct_c3"]
                    c["day_type"] = tr["day_type_at_entry"]
                    c["contracts_live"] = tr["contracts_live"]
                    c["has_t0"] = tr["has_t0"]
                    c["trade_id"] = int(tid)
            key = (d, c["pattern"], c["direction"], floor5(tsd))
            cur = best.get(key)
            if cur is None or (prio[kind], -tsd.timestamp()) > (prio[cur["kind"]], -cur["ts"].timestamp()):
                best[key] = c
    cands = sorted(best.values(), key=lambda c: c["ts"])
    return cands, raw_n


# ───────────────────────────── gates replayed offline ─────────────────────────────
def release_verdict(c, bars_by_ny, min_hl):
    """Re-run the repo's check_release on CLOSED bars as of the decision (live passes the last 30
    bars of the NY date incl. the building bar; here: closed bars only)."""
    cutoff = floor5(c["ts"]) - dt.timedelta(minutes=5)
    rows = [b for b in bars_by_ny.get(c["ts"].astimezone(NY).date(), []) if b["ts"] <= cutoff][-30:]
    os.environ["RELEASE_MIN_HIGHER_LOWS"] = str(min_hl)
    v = rg.check_release(rg.bars_from_rows(rows), c["direction"], accepted_break=None)
    os.environ["RELEASE_MIN_HIGHER_LOWS"] = "2"
    return v


def late_gates(c, rth, idx_of, skip=None):
    """Gates AFTER awaiting_release that are computable offline. Returns blocking gate or None.
    skip = the gate being switched off in an isolation run (must not re-block its own candidates)."""
    lv, e = c["levels"], c["entry"]
    if lv is None or e is None:
        return "no_levels"
    if lv.get("t1") is None:
        return "no_t1"
    long_ = c["direction"] == "LONG"
    sd = abs(e - lv["stop"])
    t1d = (lv["t1"] - e) if long_ else (e - lv["t1"])
    if t1d <= 0 and skip != "structural_targets_wrong_side":
        return "structural_targets_wrong_side"
    if sd <= 0 or ((lv["stop"] >= e) if long_ else (lv["stop"] <= e)):
        return "stop_wrong_side"
    rr = t1d / sd
    if rr < RR_HARD and skip != "rr_hard_floor":
        return "rr_hard_floor"
    if rr < RR_MIN and skip not in ("rr_entry_gate", "rr_hard_floor"):
        return "rr_entry_gate"
    if c["ct"].time() >= EOD_CUTOFF_CT and skip != "eod_entry_cutoff":
        return "eod_entry_cutoff"
    # entry confirm (S4_ENTRY_CONFIRM_V1=1): last closed bar must not close against the direction by > tol
    sig_ts = floor5(c["ts"]) - dt.timedelta(minutes=5)
    i = idx_of.get(sig_ts)
    if skip != "entry_not_confirmed" and i is not None and i >= 1:
        prev = rth[max(0, i - 14):i]
        tol = max(0.10 * statistics.mean(b["high"] - b["low"] for b in prev), 0.5) if prev else 0.5
        sb = rth[i]
        if (long_ and sb["close"] <= sb["open"] - tol) or ((not long_) and sb["close"] >= sb["open"] + tol):
            return "entry_not_confirmed"
    return None


# ───────────────────────────── trade simulation ─────────────────────────────
def simulate(c, rth, idx_of, contracts=5, has_t0=True, runner_struct=False):
    """Bar-by-bar, pessimistic. Returns dict or None if no bars."""
    long_ = c["direction"] == "LONG"
    sgn = 1 if long_ else -1
    e = c["entry"]
    lv = c["levels"]
    ebar = floor5(c["ts"])
    i0 = idx_of.get(ebar)
    if i0 is None:
        # decision between bars (should not happen inside RTH) → next available bar
        later = [j for j, b in enumerate(rth) if b["ts"] >= ebar]
        if not later:
            return None
        i0 = later[0]
    start = i0 if c["sec_in_bar"] < 60 else i0 + 1
    if start >= len(rth):
        return None
    lad = LADDER[contracts]
    t0 = tick(e + sgn * T0_PTS) if has_t0 else None
    t3 = lv.get("t3")
    if runner_struct and c.get("struct_c3") is not None:
        s3 = c["struct_c3"]
        if (s3 - e) * sgn > 0:
            t3 = s3
    legs = [("T0", t0, lad[0]), ("T1", lv.get("t1"), lad[1]), ("T2", lv.get("t2"), lad[2]), ("T3", t3, lad[3])]
    if not has_t0:  # pre-T0 era ladders: contracts spread over T1,T2,T3 one each (+runner)
        legs = [("T1", lv.get("t1"), 1), ("T2", lv.get("t2"), 1), ("T3", t3, 1), ("R", None, 1)][:contracts]
    legs = [(n, p, q) for n, p, q in legs if q > 0]
    stop = lv["stop"]
    pnl = 0.0
    remaining = sum(q for _, _, q in legs)
    open_legs = [[n, p, q] for n, p, q in legs]
    fills = []
    be_pending = False
    exit_i, exit_reason = None, None
    for i in range(start, len(rth)):
        b = rth[i]
        if be_pending:
            stop = e if (long_ and e > stop) or ((not long_) and e < stop) else stop
            be_pending = False
        # 1. stop first (touch == fill; a bar touching stop and target == stop)
        if (long_ and b["low"] <= stop) or ((not long_) and b["high"] >= stop):
            pts = (stop - e) * sgn
            pnl += pts * remaining * PT
            fills.append(("STOP" if stop != e else "BE", stop, remaining))
            remaining = 0
            exit_i, exit_reason = i, ("STOP" if stop != e else "BE")
            break
        # 2. targets in ladder order — fill only when price passes THROUGH the level
        for leg in open_legs:
            n, p, q = leg
            if q <= 0 or p is None:
                continue
            if (long_ and b["high"] > p) or ((not long_) and b["low"] < p):
                pts = (p - e) * sgn
                pnl += pts * q * PT
                fills.append((n, p, q))
                remaining -= q
                leg[2] = 0
                if n == "T1":
                    be_pending = True
        if remaining <= 0:
            exit_i, exit_reason = i, fills[-1][0]
            break
    if remaining > 0:
        last = rth[-1]
        pts = (last["close"] - e) * sgn
        pnl += pts * remaining * PT
        fills.append(("EOD", last["close"], remaining))
        exit_i, exit_reason = len(rth) - 1, "EOD"
    return {"pnl": round(pnl, 2), "exit_i": exit_i, "exit_reason": exit_reason, "fills": fills,
            "entry_i": i0, "start_i": start}


def run_day(cands, rth, idx_of, bars_by_ny, eligible, contracts_fn=None, runner_struct=False,
            daily_cap=None):
    """Serial single-slot replay of one day. eligible(c) -> (bool, tag)."""
    trades, skipped = [], collections.Counter()
    slot_until = -1
    stops = []  # (ct, pattern_base, direction, entry)
    day_pnl = 0.0
    halted = False
    for c in cands:
        ok, tag = eligible(c)
        if not ok:
            skipped[tag] += 1
            continue
        if c["levels"] is None or c["entry"] is None:
            skipped["no_levels"] += 1
            continue
        if halted:
            skipped["daily_loss_halt"] += 1
            continue
        ebar = floor5(c["ts"])
        i0 = idx_of.get(ebar)
        if i0 is None:
            skipped["no_bar"] += 1
            continue
        if i0 <= slot_until:
            skipped["slot"] += 1
            continue
        base = c["pattern"].replace("_LONG", "").replace("_SHORT", "")
        cd = [s for s in stops if s[1] == base and s[2] == c["direction"] and
              (c["ct"] - s[0]).total_seconds() <= COOLDOWN_MIN * 60 and abs(c["entry"] - s[3]) <= COOLDOWN_PTS]
        if cd:
            skipped["pattern_stop_cooldown"] += 1
            continue
        n_ctr = contracts_fn(c) if contracts_fn else 5
        has_t0 = True if not contracts_fn else bool(c.get("has_t0"))
        r = simulate(c, rth, idx_of, contracts=n_ctr, has_t0=has_t0, runner_struct=runner_struct)
        if r is None:
            skipped["no_bars_after"] += 1
            continue
        r.update({"cand": c, "tag": tag, "contracts": n_ctr})
        trades.append(r)
        slot_until = r["exit_i"]
        day_pnl += r["pnl"]
        if r["exit_reason"] == "STOP":
            stops.append((rth[r["exit_i"]]["ct"] + dt.timedelta(minutes=5), base, c["direction"], c["entry"]))
        if daily_cap is not None and day_pnl <= -daily_cap:
            halted = True
    return trades, skipped, halted


# ───────────────────────────── variants ─────────────────────────────
BASE_POLICY = ("live", "slot", "presend")
BASE_LIVE = ("live",)


def make_eligible(variant, gate_off=None, rel_cache=None, rth=None, idx_of=None, bars_by_ny=None,
                  base=BASE_POLICY):
    """variant in V0..V4; gate_off = single gate isolation on top of V0 (live release params)."""
    def elig(c):
        k = c["kind"]
        if k in base:
            return True, k
        if k != "blocked":
            return False, k
        g = c["blocked_by"]
        v1 = variant >= 1
        want = False
        rel_min_hl = 2
        if gate_off is not None:
            if g != gate_off:
                return False, "blocked"
            want = True
            rel_min_hl = 0 if gate_off == "awaiting_release" else 2
        else:
            if v1 and g == "awaiting_release":
                want, rel_min_hl = True, 0
            elif variant >= 2 and (c["date"], c["pattern"], c["direction"], c["entry"]) in ELQ3:
                want, rel_min_hl = True, 0
            elif variant >= 3 and g in V3_GATES:
                want, rel_min_hl = True, 0
        if not want:
            return False, "blocked"
        if c["levels"] is None:
            return False, "no_levels"
        # gates between g and the end of the chain that we can replay
        gpos = GATE_ORDER.index(g) if g in GATE_ORDER else 0
        if gpos <= REL_POS:
            key = (id(c), rel_min_hl)
            v = rel_cache.get(key)
            if v is None:
                v = release_verdict(c, bars_by_ny, rel_min_hl)
                rel_cache[key] = v
            if not v.released:
                return False, "release_hold"
        lg = late_gates(c, rth, idx_of, skip=gate_off)
        if lg:
            return False, "late:" + lg
        return True, "unblocked:" + g
    return elig


def stats(trades):
    n = len(trades)
    if n == 0:
        return {"n": 0}
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in trades if t["pnl"] < 0]
    return {"n": n, "win_pct": round(100 * len(wins) / n, 1), "avg_win": round(statistics.mean(wins), 1) if wins else 0,
            "avg_loss": round(statistics.mean(losses), 1) if losses else 0, "sum": round(sum(t["pnl"] for t in trades), 2),
            "max_loss_trade": round(min(t["pnl"] for t in trades), 2), "n_be": sum(1 for t in trades if t["pnl"] == 0)}


def max_streak(trades):
    best = cur = 0
    for t in trades:
        cur = cur + 1 if t["pnl"] < 0 else 0
        best = max(best, cur)
    return best


def main():
    conn = connect()
    bars = load_bars(conn)
    trades = load_trades(conn)
    cands, raw_n = load_candidates(trades)
    bars_by_ny = collections.defaultdict(list)
    for b in bars:
        bars_by_ny[b["ny"].date()].append(b)
    rth_by_date, idx_by_date = {}, {}
    for d in DATES:
        dd = dt.date.fromisoformat(d)
        rth = [b for b in bars if b["ct"].date() == dd and dt.time(8, 30) <= b["ct"].time() <= LAST_BAR_CT]
        rth_by_date[d] = rth
        idx_by_date[d] = {b["ts"]: i for i, b in enumerate(rth)}
    by_date = collections.defaultdict(list)
    for c in cands:
        by_date[c["date"]].append(c)

    report = {"raw_records": dict(raw_n), "n_dedup": len(cands),
              "kinds": dict(collections.Counter(c["kind"] for c in cands)),
              "blocked_by": dict(collections.Counter(c["blocked_by"] for c in cands if c["kind"] == "blocked")),
              "no_levels": dict(collections.Counter(f'{c["kind"]}/{c["blocked_by"]}' for c in cands if c["levels"] is None))}

    # broker per day (system, parents + scale-in children)
    broker_day, broker_parents = collections.Counter(), collections.Counter()
    for tid, pnl in BROKER_TRADE.items():
        tr = trades[tid]
        d = tr["entry_ct"].date().isoformat()
        broker_day[d] += pnl
        if tid not in SCALE_IN_CHILDREN:
            broker_parents[d] += pnl
    report["broker_day"] = {d: round(broker_day[d], 2) for d in DATES}
    report["broker_parents_day"] = {d: round(broker_parents[d], 2) for d in DATES}

    # ── release-gate replay fidelity (live params on closed bars vs the logged verdict)
    fid = collections.Counter()
    rel_cache = {}
    for c in cands:
        if c["kind"] == "blocked" and c["blocked_by"] == "awaiting_release":
            v = release_verdict(c, bars_by_ny, 2)
            rel_cache[(id(c), 2)] = v
            fid["agree_blocked" if not v.released else "replay_released_live_blocked"] += 1
    report["release_fidelity"] = dict(fid)

    # ── V0-strict calibration: live fires only, live contracts/ladder
    cal_rows, cal_day = [], collections.defaultdict(float)
    for d in DATES:
        rth, idx_of = rth_by_date[d], idx_by_date[d]
        live_c = [c for c in by_date[d] if c["kind"] == "live"]
        for c in live_c:
            if c["levels"] is None:
                continue
            r = simulate(c, rth, idx_of, contracts=c["contracts_live"] or 5, has_t0=bool(c["has_t0"]))
            if r is None:
                continue
            bp = BROKER_TRADE.get(c["trade_id"])
            cal_rows.append({"date": d, "id": c["trade_id"], "pattern": c["pattern"], "dir": c["direction"],
                             "ct": c["ct"].strftime("%H:%M"), "entry": c["entry"], "contracts": c["contracts_live"],
                             "sim": r["pnl"], "broker": bp, "exit": r["exit_reason"],
                             "fills": r["fills"]})
            cal_day[d] += r["pnl"]
    report["calibration"] = {"rows": cal_rows, "sim_day": {d: round(cal_day[d], 2) for d in DATES}}

    # ── variants (two bases: policy = live+slot+presend candidates; live = live fires only)
    variants = {}
    for base_name, base in (("policy", BASE_POLICY), ("live", BASE_LIVE)):
        for v in range(5):
            per_day, all_tr, skips, halts = {}, [], collections.Counter(), []
            for d in DATES:
                rth, idx_of = rth_by_date[d], idx_by_date[d]
                elig = make_eligible(v, rel_cache=rel_cache, rth=rth, idx_of=idx_of, bars_by_ny=bars_by_ny, base=base)
                tr, sk, _ = run_day(by_date[d], rth, idx_of, bars_by_ny, elig, runner_struct=(v == 4))
                per_day[d] = round(sum(t["pnl"] for t in tr), 2)
                all_tr += [dict(t, date=d) for t in tr]
                skips.update(sk)
                run = 0.0
                for t in tr:
                    run += t["pnl"]
                    if run <= -DAILY_CAP:
                        halts.append(d)
                        break
            cap_day = {}
            for d in DATES:
                rth, idx_of = rth_by_date[d], idx_by_date[d]
                elig = make_eligible(v, rel_cache=rel_cache, rth=rth, idx_of=idx_of, bars_by_ny=bars_by_ny, base=base)
                tr, _, _ = run_day(by_date[d], rth, idx_of, bars_by_ny, elig, runner_struct=(v == 4), daily_cap=DAILY_CAP)
                cap_day[d] = round(sum(t["pnl"] for t in tr), 2)
            st = stats(all_tr)
            st["max_day_loss"] = min(per_day.values())
            st["max_day_loss_date"] = min(per_day, key=per_day.get)
            st["days_halted"] = halts
            st["sum_with_cap"] = round(sum(cap_day.values()), 2)
            st["losing_streak"] = max_streak(all_tr)
            st["by_tag"] = dict(collections.Counter(t["tag"] for t in all_tr))
            st["exit_reasons"] = dict(collections.Counter(t["exit_reason"] for t in all_tr))
            st["sum_8d"] = round(sum(p for d, p in per_day.items() if d >= "2026-08-26"), 2)
            name = f"V{v}" if base_name == "policy" else f"V{v}-livebase"
            variants[name] = {"per_day": per_day, "cap_day": cap_day, "stats": st, "skips": dict(skips),
                              "trades": [{"date": t["date"], "ct": t["cand"]["ct"].strftime("%H:%M:%S"),
                                          "pattern": t["cand"]["pattern"], "dir": t["cand"]["direction"],
                                          "entry": t["cand"]["entry"], "levels": t["cand"]["levels"],
                                          "kind": t["cand"]["kind"], "blocked_by": t["cand"]["blocked_by"],
                                          "tag": t["tag"], "pnl": t["pnl"], "exit": t["exit_reason"],
                                          "fills": t["fills"], "trade_id": t["cand"].get("trade_id"),
                                          "exit_ct": rth_by_date[t["date"]][t["exit_i"]]["ct"].strftime("%H:%M")}
                                         for t in all_tr]}
    report["variants"] = variants

    # ── debug: every blocked candidate that any variant could unblock — verdicts
    dbg = []
    for c in cands:
        if c["kind"] != "blocked":
            continue
        g = c["blocked_by"]
        interesting = g == "awaiting_release" or g in V3_GATES or \
            (c["date"], c["pattern"], c["direction"], c["entry"]) in ELQ3
        if not interesting or c["levels"] is None:
            continue
        rth, idx_of = rth_by_date[c["date"]], idx_by_date[c["date"]]
        v2 = rel_cache.get((id(c), 2)) or release_verdict(c, bars_by_ny, 2)
        v0 = rel_cache.get((id(c), 0)) or release_verdict(c, bars_by_ny, 0)
        dbg.append({"date": c["date"], "ct": c["ct"].strftime("%H:%M:%S"), "pattern": c["pattern"], "dir": c["direction"],
                    "entry": c["entry"], "gate": g, "live_reason": c["reason"][:80],
                    "replay_min_hl2": (v2.released, v2.reason[:70]), "replay_min_hl0": (v0.released, v0.reason[:70]),
                    "late": late_gates(c, rth, idx_of)})
    report["debug_candidates"] = dbg
    report["release_min_hl0_reasons"] = dict(collections.Counter(
        f'{d["replay_min_hl0"][0]}|{d["replay_min_hl0"][1].split("(")[0].strip()}' for d in dbg if d["gate"] == "awaiting_release"))

    # ── per-gate isolation on top of V0 (live release params for gates before the release gate), both bases
    gates = sorted(report["blocked_by"], key=lambda g: -report["blocked_by"][g])
    report["gate_isolation"] = {}
    for base_name, base in (("policy", BASE_POLICY), ("live", BASE_LIVE)):
        v0_sum = sum(variants["V0" if base_name == "policy" else "V0-livebase"]["per_day"].values())
        iso = {}
        for g in gates:
            tot, n_added, added_pnl, tags, added = 0.0, 0, 0.0, collections.Counter(), []
            for d in DATES:
                rth, idx_of = rth_by_date[d], idx_by_date[d]
                elig = make_eligible(0, gate_off=g, rel_cache=rel_cache, rth=rth, idx_of=idx_of, bars_by_ny=bars_by_ny, base=base)
                tr, sk, _ = run_day(by_date[d], rth, idx_of, bars_by_ny, elig)
                tot += sum(t["pnl"] for t in tr)
                for t in tr:
                    if t["tag"].startswith("unblocked:"):
                        n_added += 1
                        added_pnl += t["pnl"]
                        added.append(f'{d[5:]} {t["cand"]["ct"].strftime("%H:%M")} {t["cand"]["pattern"]} {t["cand"]["direction"]} {t["pnl"]:+.2f} {t["exit_reason"]}')
                for k, v in sk.items():
                    if k.startswith("late:") or k in ("release_hold", "no_levels"):
                        tags[k] += v
            iso[g] = {"n_blocked": report["blocked_by"][g], "n_entered": n_added, "delta": round(tot - v0_sum, 2),
                      "added_pnl": round(added_pnl, 2), "filtered": dict(tags), "added": added}
        # awaiting_release with live params (min_hl=2 on closed bars) and ALL (no release check) for reference
        for label, min_hl in (("awaiting_release@min_hl=2(closed-bars)", 2), ("awaiting_release@ALL(no release check)", None)):
            tot, n_added, added_pnl, added = 0.0, 0, 0.0, []
            for d in DATES:
                rth, idx_of = rth_by_date[d], idx_by_date[d]

                def elig_x(c, rth=rth, idx_of=idx_of, min_hl=min_hl):
                    if c["kind"] in base:
                        return True, c["kind"]
                    if c["kind"] == "blocked" and c["blocked_by"] == "awaiting_release" and c["levels"]:
                        if min_hl is not None:
                            v = rel_cache.get((id(c), min_hl)) or release_verdict(c, bars_by_ny, min_hl)
                            if not v.released:
                                return False, "release_hold"
                        if late_gates(c, rth, idx_of):
                            return False, "late"
                        return True, "unblocked:" + label
                    return False, "blocked"
                tr, _, _ = run_day(by_date[d], rth, idx_of, bars_by_ny, elig_x)
                tot += sum(t["pnl"] for t in tr)
                for t in tr:
                    if t["tag"].startswith("unblocked:"):
                        n_added += 1
                        added_pnl += t["pnl"]
                        added.append(f'{d[5:]} {t["cand"]["ct"].strftime("%H:%M")} {t["cand"]["pattern"]} {t["cand"]["direction"]} {t["pnl"]:+.2f} {t["exit_reason"]}')
            iso[label] = {"n_blocked": report["blocked_by"]["awaiting_release"], "n_entered": n_added,
                          "delta": round(tot - v0_sum, 2), "added_pnl": round(added_pnl, 2), "added": added}
        report["gate_isolation"][base_name] = iso
        report[f"v0_sum_{base_name}"] = round(v0_sum, 2)
    iso = {f"{b}:{g}": r for b, d in report["gate_isolation"].items() for g, r in d.items()}

    with open(os.path.join(OUT, "gate_replay_result.json"), "w") as f:
        json.dump(report, f, indent=1, default=str, ensure_ascii=False)
    print(json.dumps({k: report[k] for k in ("raw_records", "n_dedup", "kinds", "blocked_by", "no_levels",
                                              "release_fidelity", "broker_day", "broker_parents_day")},
                     indent=1, default=str, ensure_ascii=False))
    print("calibration sim_day", report["calibration"]["sim_day"])
    for v, res in variants.items():
        print(v, res["per_day"], "Σ10", round(sum(res["per_day"].values()), 2), "Σ8", res["stats"].get("sum_8d"),
              {k: res["stats"][k] for k in ("n", "win_pct", "avg_win", "avg_loss", "max_loss_trade", "max_day_loss",
                                            "max_day_loss_date", "days_halted", "losing_streak", "by_tag", "exit_reasons")},
              "skips", res["skips"])
    for g, r in iso.items():
        print("GATE", g, r)
    print("release_min_hl0_reasons", report["release_min_hl0_reasons"])
    for d in dbg:
        print("DBG", d)


if __name__ == "__main__":
    main()
