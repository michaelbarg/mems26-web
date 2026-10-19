#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daytype_intraday.py - Michael 19.10.2026: "run an agent that identifies the day type at every given moment of the trading day
per Dalton, and check whether there are gaps between how the system identifies and trades and what Dalton says."

For every trading day and every 5-minute step of RTH it computes
  REF  the day type per the super-agent's reading of Dalton (pp.19-29 day types, pp.63-74 opens; NOT Michael's labels) from the closed
       bars SEEN SO FAR only (no look-ahead): <6 bars -> early drive read / UNKNOWN, 6-11 bars -> PRE_IB:<opening type> with Dalton's
       expectation, >=12 bars -> the doctrine_audit.py EOD rules (IB = first 60 min, range extension with acceptance = >=2 consecutive
       closes beyond the IB edge +-2 ticks, rib, close position) applied to the partial day;
  SYS  what the system believed at that moment = v9_decision_vectors.vector.day_type, LAST 'DECISION' row of the bucket (forward-filled
       when the bucket has no row; NOT v9_day_type_history, which is an end-of-day rewrite and is reported separately);
and for every live trade: REF label at entry, SYS label at entry, and a doctrine verdict (WITH_DOCTRINE / AGAINST / UNCLEAR).
ALIGNMENT: bucket b = wall-clock [09:30+5b, 09:35+5b) ET. The system updates its label a few seconds after a bar closes, so the rows of
bucket b carry the information of closed bars 0..b-1, and REF at bucket b uses bars[:b] - same information set, no look-ahead.
SELECT-only (psql COPY .. TO STDOUT). usage (from the repo root):
  python3 harness_out/t586/hist/daytype_intraday.py [--from=2026-09-17] [--to=2026-10-16] [--db=mems26] [--out=docs/reports]
         [--tag=2026-10-19] [--summary=<json path>]
"""
import sys, os, io, re, csv, json, ast, subprocess, collections, statistics, random, datetime as dt

PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
opt = {a.split("=")[0][2:]: (a.split("=", 1)[1] if "=" in a else "1") for a in sys.argv[1:] if a.startswith("--")}
DB = opt.get("db", "mems26"); D0 = opt.get("from", "2026-09-17"); D1 = opt.get("to", "2026-10-16")
OUT = opt.get("out", "docs/reports"); TAG = opt.get("tag", "2026-10-19"); SUMMARY = opt.get("summary")
HERE = os.path.dirname(os.path.abspath(__file__))
TICK = 0.25; EDGE = 0.25; NB = 78            # NB = RTH 5-minute bars 09:30..15:55 ET
ROLL_DAYS = {"2026-09-21"}                   # contract-roll day: the prior session sits on the other contract (+48.25 gap) -> prior-day references invalid
ASLEEP = "המערכת ישנה"
SEGS = ["PRE_IB", "FIRST_HOUR_AFTER_IB", "MIDDAY", "AFTERNOON"]
def seg_of(b): return "PRE_IB" if b < 12 else "FIRST_HOUR_AFTER_IB" if b < 24 else "MIDDAY" if b < 54 else "AFTERNOON"


def q(sql):
    r = subprocess.run([PSQL, "-d", DB, "-X", "-q", "-c", f"COPY ({sql}) TO STDOUT WITH (FORMAT csv)"], capture_output=True, text=True)
    if r.returncode: raise SystemExit("psql failed: " + r.stderr[:600])
    return list(csv.reader(io.StringIO(r.stdout)))
def shift(d, k): return (dt.date.fromisoformat(d) + dt.timedelta(days=k)).isoformat()
def bucket_of(hms):
    h, m, s = (int(x) for x in hms[:8].split(":")); secs = h * 3600 + m * 60 + s - (9 * 3600 + 30 * 60)
    return secs // 300 if 0 <= secs < NB * 300 else None
def fnum(x, default=None):
    try: return float(x)
    except (TypeError, ValueError): return default


# ------------------------------------------------------------------------------------------------ data (SELECT-only)
BARS = collections.defaultdict(list)          # ET date -> [(il_hhmm, o, h, l, c, v, et_hhmm)] (same tuple layout as doctrine_audit.rth_bars + et)
for d, et, il, o, h, l, c, v in q(
        f"select to_char(ts at time zone 'America/New_York','YYYY-MM-DD'), to_char(ts at time zone 'America/New_York','HH24:MI'), "
        f"to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close, coalesce(volume,0) from v9_bars_5min_woodies "
        f"where symbol='MES' and (ts at time zone 'America/New_York')::date between '{shift(D0, -21)}' and '{D1}' "
        f"and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts"):
    BARS[d].append((il, float(o), float(h), float(l), float(c), float(v), et))
DAYS = [d for d in sorted(BARS) if D0 <= d <= D1]
for d in DAYS:
    if len(BARS[d]) != NB: print(f"WARN {d}: {len(BARS[d])} RTH bars (expected {NB}) - day dropped")
DAYS = [d for d in DAYS if len(BARS[d]) == NB]
PRIOR = {d: next((p for p in sorted(BARS, reverse=True) if p < d and len(BARS[p]) >= 30), None) for d in DAYS}

VEC = collections.defaultdict(list)           # ET date -> DECISION rows inside RTH, time-ordered
for d, hms, dtp, cf, ph, ot, ex, ep, px, cl, di, bl, sy in q(
        "select to_char(ts at time zone 'America/New_York','YYYY-MM-DD'), to_char(ts at time zone 'America/New_York','HH24:MI:SS'), "
        "coalesce(vector->>'day_type',''), coalesce(vector->>'day_type_conf',''), coalesce(vector->>'phase',''), "
        "coalesce(vector->>'opening_type',''), coalesce(vector->>'extension',''), coalesce(vector->>'extension_pts',''), "
        "coalesce(vector->>'price',''), coalesce(classification,''), coalesce(direction,''), coalesce(blocked_by,''), coalesce(system::text,'') "
        "from v9_decision_vectors where kind='DECISION' "
        f"and (ts at time zone 'America/New_York')::date between '{D0}' and '{D1}' "
        "and (ts at time zone 'America/New_York')::time between '09:30' and '15:59:59' order by ts"):
    b = bucket_of(hms)
    if b is not None: VEC[d].append(dict(b=b, hms=hms, raw=dtp, conf=cf, phase=ph, ot=ot, ext=ex, ext_pts=ep, px=px, cls=cl, dir=di, blocked=bl, system=sy))

TRADES = []
for r in q("select id, coalesce(firing_system::text,''), direction, to_char(coalesce(entry_ts,created_at) at time zone 'America/New_York','YYYY-MM-DD'), "
           "to_char(coalesce(entry_ts,created_at) at time zone 'America/New_York','HH24:MI:SS'), "
           "to_char(coalesce(entry_ts,created_at) at time zone 'Asia/Jerusalem','HH24:MI:SS'), "
           "coalesce(coalesce(pattern_id_at_entry, quality->>'pattern_name'),''), coalesce(day_type_at_entry,''), coalesce(exit_reason,''), "
           "coalesce(pnl_sierra, pnl_usd, 0), (pnl_sierra is not null), coalesce((quality->>'contracts')::int, 0), coalesce(entry_price, 0), "
           "(entry_ts is null), coalesce(pnl_usd, 0), coalesce(stop, 0), coalesce(t1, 0) "
           "from v9_trades where mode='live' and state='CLOSED' "
           f"and (coalesce(entry_ts,created_at) at time zone 'America/New_York')::date between '{D0}' and '{D1}' order by coalesce(entry_ts,created_at)"):
    TRADES.append(dict(id=r[0], fs=r[1], dir=r[2], date=r[3], et=r[4], il=r[5], pattern=r[6], dte=r[7], exit=r[8], pnl=float(r[9]), ver=(r[10] == "t"),
                       k=int(r[11]), px=float(r[12]), no_ts=(r[13] == "t"), pnl_books=float(r[14]), stop=float(r[15]), t1=float(r[16])))

HIST = {r[0]: dict(day_type=r[1], opening_type=r[2], ibh=fnum(r[3]), ibl=fnum(r[4])) for r in q(
    f"select date::text, day_type, coalesce(opening_type,''), ib_high, ib_low from v9_day_type_history where date between '{D0}' and '{D1}'")}


# ------------------------------------------------------------------------------------------------ reference rules
# ref_opening / prev_profile_from are the doctrine_audit.py logic verbatim (parity-checked below when that file is present).
def prev_profile_from(bars):
    """prior RTH session's TPO value area from its own 5-min bars (30-minute letters, 70% around the POC)."""
    if len(bars) < 30: return None
    prof = collections.defaultdict(set)
    for i, b in enumerate(bars):
        letter = i // 6; p = b[3]
        while p <= b[2] + 1e-9:
            prof[round(p / TICK) * TICK].add(letter); p += TICK
    counts = {p: len(v) for p, v in prof.items()}; total = sum(counts.values()); poc = max(counts, key=lambda p: (counts[p], -abs(p - (max(counts) + min(counts)) / 2)))
    lo = hi = poc; acc = counts[poc]
    while acc < 0.7 * total:
        up, dn = counts.get(round((hi + TICK) / TICK) * TICK, 0), counts.get(round((lo - TICK) / TICK) * TICK, 0)
        if up >= dn and up > 0: hi = round((hi + TICK) / TICK) * TICK; acc += up
        elif dn > 0: lo = round((lo - TICK) / TICK) * TICK; acc += dn
        else: break
    return dict(date=None, poc=poc, vah=hi, val=lo, high=max(b[2] for b in bars), low=min(b[3] for b in bars))
def ref_opening(bars, prev):
    """Dalton pp.63-74 on the first 30 minutes (6 bars). Returns (type, note)."""
    if len(bars) < 6: return "UNKNOWN", "fewer than 6 bars"
    o = bars[0][1]; b0h, b0l = bars[0][2], bars[0][3]
    highs = [b[2] for b in bars[:6]]; lows = [b[3] for b in bars[:6]]; closes = [b[4] for b in bars[:6]]
    up_drive = all(c > o for c in closes[1:]) and min(lows[1:]) >= o - 2 * TICK
    dn_drive = all(c < o for c in closes[1:]) and max(highs[1:]) <= o + 2 * TICK
    if up_drive or dn_drive: return "OPEN_DRIVE", "no re-trade of the open in bars 2-6"
    refs = [prev["high"], prev["low"], prev["vah"], prev["val"]] if prev else []
    probe_up = max(highs[:2]) > max([r for r in refs if r > o], default=1e9) if refs else False
    probe_dn = min(lows[:2]) < min([r for r in refs if r < o], default=-1e9) if refs else False
    if probe_up and all(c < o for c in closes[3:]): return "OPEN_TEST_DRIVE", "probe above a prior reference, drive down"
    if probe_dn and all(c > o for c in closes[3:]): return "OPEN_TEST_DRIVE", "probe below a prior reference, drive up"
    if (max(highs[:3]) - o >= 4 and min(lows[3:]) < o) or (o - min(lows[:3]) >= 4 and max(highs[3:]) > o): return "OPEN_REJECTION_REVERSE", "drive then back through the open"
    if prev and prev["low"] <= o <= prev["high"]: return "OPEN_AUCTION_IN", "rotation around the open inside the prior range"
    return "OPEN_AUCTION_OUT", "rotation around the open outside the prior range" if prev else "no prior reference"
def early_drive(bars):
    """EXTENSION (not in doctrine_audit): the same Open-Drive test as ref_opening, run on the 3-5 bars seen so far (Dalton p.63: conviction is
    readable in the first few minutes; the system's phase A is the first 3 bars). Returns +1 / -1 for an up / down drive so far, else 0."""
    o = bars[0][1]; cl = [b[4] for b in bars]; hs = [b[2] for b in bars]; ls = [b[3] for b in bars]
    if all(c > o for c in cl[1:]) and min(ls[1:]) >= o - 2 * TICK: return 1
    if all(c < o for c in cl[1:]) and max(hs[1:]) <= o + 2 * TICK: return -1
    return 0
def ref_daytype_core(bars):
    """doctrine_audit.ref_daytype verbatim in logic (Dalton pp.19-29), minimum lowered from 24 to 12 bars so it can run on a partial day;
    also returns the features the verdict needs."""
    ibh, ibl = max(b[2] for b in bars[:12]), min(b[3] for b in bars[:12]); ib = max(ibh - ibl, TICK)
    def accepted(side):
        run = 0
        for b in bars[12:]:
            beyond = b[4] > ibh + 2 * TICK if side == "up" else b[4] < ibl - 2 * TICK
            run = run + 1 if beyond else 0
            if run >= 2: return True
        return False
    acc_up, acc_dn = accepted("up"), accepted("dn"); sides = int(acc_up) + int(acc_dn)
    hi, lo = max(b[2] for b in bars), min(b[3] for b in bars)
    rng = hi - lo; rib = rng / ib; close_pos = (bars[-1][4] - lo) / rng if rng else 0.5
    if sides == 0: lab = "Nontrend" if rib <= 1.15 else "Normal"
    elif sides == 2: lab = "Neutral_Extreme" if (close_pos >= 0.85 or close_pos <= 0.15) else "Neutral_Center"
    elif rib >= 2.0 and (close_pos >= 0.85 or close_pos <= 0.15): lab = "Trend_Normal"
    else: lab = "Normal_Variation"
    return lab, dict(ibh=ibh, ibl=ibl, ib=ib, hi=hi, lo=lo, rib=rib, sides=sides, acc_up=acc_up, acc_dn=acc_dn, close_pos=close_pos,
                     ext_dir=(1 if acc_up and not acc_dn else -1 if acc_dn and not acc_up else 0), last=bars[-1][4])
def ot_dir_of(ot, bars):
    k = min(len(bars), 6); o = bars[0][1]; c = bars[k - 1][4]
    return (1 if c > o else -1) if ot in ("OPEN_DRIVE", "OPEN_TEST_DRIVE") else 0
def ref_state(bars, prev, ot30, narrow=None):
    """Reference state from the closed bars seen so far (bars = bars[:b]).
    label   = the verbatim doctrine_audit rules (REF-A, primary).
    label_b = SENSITIVITY (REF-B): identical except that 'Nontrend' additionally requires a NARROW initial balance
              (IB <= 0.7 x the median IB of the previous 10 sessions - Dalton p.19/p.27: Nontrend = narrow base and no range extension;
              a wide IB that is never upset is a Normal day, p.20). Verbatim rule: sides==0 and rib<=1.15 is Nontrend whatever the IB width."""
    n = len(bars)
    st = dict(n=n, label="PRE_IB:UNKNOWN", label_b="PRE_IB:UNKNOWN", ot="UNKNOWN", ot_basis="", ot_dir=0, ibh=None, ibl=None, hi=None, lo=None, last=None, sides=None,
              acc_up=None, acc_dn=None, rib=None, close_pos=None, ext_dir=0, note="")
    if n: st.update(hi=max(b[2] for b in bars), lo=min(b[3] for b in bars), last=bars[-1][4])
    if n >= 6: st.update(ot=ot30, ot_basis="30m", ot_dir=ot_dir_of(ot30, bars))
    elif n >= 3:
        e = early_drive(bars)
        if e: st.update(ot="OPEN_DRIVE", ot_basis="early", ot_dir=e)
    if n < 12:
        st["label"] = st["label_b"] = "PRE_IB:" + st["ot"]; return st
    lab, f = ref_daytype_core(bars)
    lab_b = lab if (narrow is None or lab not in ("Nontrend", "Normal")) else ("Nontrend" if (lab == "Nontrend" and narrow) else "Normal")
    st.update(label=lab, label_b=lab_b, ibh=f["ibh"], ibl=f["ibl"], sides=f["sides"], acc_up=f["acc_up"], acc_dn=f["acc_dn"], rib=f["rib"], close_pos=f["close_pos"], ext_dir=f["ext_dir"])
    if lab == "Trend_Normal" and f["ext_dir"] != 0 and ((f["close_pos"] >= 0.5) != (f["ext_dir"] > 0)): st["note"] = "TN_close_at_opposite_extreme_to_accepted_side"
    return st

# Dalton's expectation per opening type (DALTON_DOCTRINE.md section 3.1, pp.63-74), in the system's label vocabulary
EXPECT = {"OPEN_DRIVE": ("Trend_Normal", "Normal_Variation"), "OPEN_TEST_DRIVE": ("Normal_Variation", "Trend_Normal"),
          "OPEN_REJECTION_REVERSE": ("Normal", "Normal_Variation"), "OPEN_AUCTION_IN": ("Nontrend", "Normal", "Neutral_Center", "Neutral_Extreme"),
          "OPEN_AUCTION_OUT": ("Trend_Normal", "Normal_Variation")}      # out of range = potential Double-Distribution Trend -> trend family
FAMILY = {"Nontrend": "BALANCE", "Normal": "BALANCE", "Normal_Variation": "DIRECTIONAL", "Trend_Normal": "DIRECTIONAL",
          "Neutral_Center": "TWO_SIDED", "Neutral_Extreme": "TWO_SIDED"}
DIRSET = {"Normal_Variation", "Trend_Normal"}
SYSN = {"": "NONE", "Variation": "Normal_Variation", "Trend": "Trend_Normal", "Trend_DD": "Trend_Normal"}   # the system's raw -> reference vocabulary
def sysn(x): return SYSN.get(x, x)
def fam(x): return FAMILY.get(x, "NONE" if x in ("NONE", "") else "PRE_IB" if str(x).startswith("PRE_IB") else x)
LABELS = ["Nontrend", "Normal", "Normal_Variation", "Trend_Normal", "Neutral_Center", "Neutral_Extreme"]

# entry_kind per pattern: copy of config/dalton_playbook.yaml entry_kind_map @ 19.10.2026 (default BREAK) - descriptive, used only to read intent
EK = {"OPENING_DRIVE": "WITH_DRIVE", "OPENING_TEST_DRIVE": "WITH_DRIVE", "OPENING_ORR": "REVERSAL", "EXTREME_REJECT": "REVERSAL", "DALTON_EDGE": "REVERSAL",
      "DALTON_EDGE_LONG": "REVERSAL", "DALTON_EDGE_SHORT": "REVERSAL", "CEILING_FLIP": "REVERSAL", "CEILING_FLIP_TOUCH2": "EDGE_FADE",
      "CEILING_FLIP_LONG": "REVERSAL", "CEILING_FLIP_SHORT": "REVERSAL", "OPENING_EXTREME_REJECT": "REVERSAL", "FAILED_BREAK_SHORT": "EDGE_FADE",
      "FAILED_BREAK_LONG": "EDGE_FADE", "FAILED_RE_IB": "EDGE_FADE", "REACTIVE_LONG": "EDGE_FADE", "REACTIVE_SHORT": "EDGE_FADE", "VA_FADE_LONG": "EDGE_FADE",
      "VA_FADE_SHORT": "EDGE_FADE", "EDGE_FADE": "EDGE_FADE", "PULLBACK_CONT": "PULLBACK", "OPENING_PULLBACK_CONT": "PULLBACK", "TREND_STEP": "PULLBACK",
      "VAR_CONT": "PULLBACK", "INITIATIVE_LONG": "BREAK", "INITIATIVE_SHORT": "BREAK", "GB100": "BREAK", "TLB": "BREAK", "DOUBLE_BOTTOM": "BREAK",
      "DOUBLE_TOP": "BREAK", "DOUBLE_TOP_AA": "BREAK", "DOUBLE_BOTTOM_AA": "BREAK", "GHOST": "BREAK", "VEGAS": "BREAK", "FAMIR": "BREAK",
      "S2_DELTA_DBL": "BREAK", "RE_ACCEPTANCE": "VALUE_RETURN", "ZLR": "BREAK"}
def entry_kind(cls): return EK.get(cls, EK.get(cls.upper(), "BREAK"))


def doctrine_verdict(st, D, P, variant="A"):
    """(verdict, reason). D = +1 LONG / -1 SHORT, P = entry price, st = reference state at the moment (closed bars only).
    variant 'A' = verbatim reference label, 'B' = the narrow-IB Nontrend sensitivity (st['label_b']).
    Geometry first: direction vs the accepted side, location in the developing range (q: 0 = day low .. 1 = day high; edge zone = outer 25%).
      Trend_Normal / Normal_Variation : WITH iff trading the accepted extension, AGAINST iff fading it
      Normal / Neutral_*              : WITH iff a responsive fade at the edge of the range, AGAINST iff chasing the edge, mid-range UNCLEAR
      Nontrend                        : AGAINST (stand aside)
      PRE_IB                          : Open-Drive / Test-Drive -> WITH iff with the drive; Auction-in / ORR -> the balanced rule; else UNCLEAR"""
    lab = st["label"] if variant == "A" else st["label_b"]; hi, lo = st["hi"], st["lo"]
    qq = None if hi is None or lo is None or hi <= lo else (P - lo) / (hi - lo)
    side = lambda x: "LONG" if x > 0 else "SHORT"
    def balanced(tag):
        if qq is None: return "UNCLEAR", f"{tag}: no range yet"
        if (D > 0 and qq <= EDGE) or (D < 0 and qq >= 1 - EDGE): return "WITH_DOCTRINE", f"{tag}: responsive fade at the {'low' if D > 0 else 'high'} edge (q={qq:.2f})"
        if (D > 0 and qq >= 1 - EDGE) or (D < 0 and qq <= EDGE): return "AGAINST", f"{tag}: chasing the {'high' if D > 0 else 'low'} edge (q={qq:.2f})"
        return "UNCLEAR", f"{tag}: mid-range (q={qq:.2f})"
    if lab.startswith("PRE_IB:"):
        ot = lab[7:]
        if ot in ("OPEN_DRIVE", "OPEN_TEST_DRIVE") and st["ot_dir"]:
            return ("WITH_DOCTRINE" if D == st["ot_dir"] else "AGAINST"), f"{ot}({st['ot_basis']}): expects Trend/NV, drive {side(st['ot_dir'])}"
        if ot in ("OPEN_AUCTION_IN", "OPEN_REJECTION_REVERSE"): return balanced(ot)
        return "UNCLEAR", f"{ot}: no directional read yet"
    if lab in ("Trend_Normal", "Normal_Variation"):
        e = st["ext_dir"]
        if e == 0 or st["note"]: return "UNCLEAR", f"{lab}: direction ambiguous ({st['note'] or 'two sides'})"
        if D == e: return "WITH_DOCTRINE", f"{lab}: accepted extension {side(e)}, trade {side(D)}"
        arguable = lab == "Normal_Variation" and qq is not None and ((D > 0 and qq <= EDGE) or (D < 0 and qq >= 1 - EDGE))
        return "AGAINST", f"{lab}: accepted extension {side(e)}, trade {side(D)}" + ("; ARGUABLE: responsive fade at the far edge of the new range (NV playbook: 'fade new edges' once value re-balances)" if arguable else "")
    if lab == "Nontrend": return "AGAINST", "Nontrend: stand aside"
    if lab in ("Normal", "Neutral_Center", "Neutral_Extreme"): return balanced(lab)
    return "UNCLEAR", f"{lab}: no rule"


# ------------------------------------------------------------------------------------------------ parity with the verbatim original
def parity():
    path = os.path.join(HERE, "doctrine_audit.py")
    if not os.path.exists(path): return "parity skipped: doctrine_audit.py not found next to this script"
    tree = ast.parse(open(path, encoding="utf-8").read()); ns = dict(TICK=TICK, collections=collections)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ("ref_opening", "ref_daytype", "prev_session_profile"):
            exec(compile(ast.Module([node], []), path, "exec"), ns)
    ns["rth_bars"] = lambda s: BARS.get(s, [])
    ns["q"] = lambda sql: [PRIOR[re.search(r"::date < '([0-9-]+)'", sql).group(1)]]
    strip = lambda p: None if p is None else {k: v for k, v in p.items() if k != "date"}
    bad = []; n = 0
    for d in DAYS:
        pv_o = ns["prev_session_profile"](d); pv_m = None if PRIOR[d] is None else prev_profile_from(BARS[PRIOR[d]])
        if strip(pv_o) != strip(pv_m): bad.append((d, "prev_profile"))
        if ns["ref_opening"](BARS[d], pv_o) != ref_opening(BARS[d], pv_m): bad.append((d, "ref_opening"))
        lo_, _ = ns["ref_daytype"](BARS[d]); lm_, _ = ref_daytype_core(BARS[d])
        if lo_ != lm_: bad.append((d, f"ref_daytype {lo_} vs {lm_}"))
        n += 1
    return f"parity vs doctrine_audit.py on {n} days: " + ("OK (prior-session profile, opening read, EOD label identical)" if not bad else f"MISMATCH {bad}")
PARITY = parity(); print(PARITY)

# ------------------------------------------------------------------------------------------------ per day x bucket
def lag_cat(rb, sb, alive_end):
    if alive_end < 0: return "ASLEEP", None
    if rb is None and sb is None: return "BOTH_NEVER", None
    if rb is None: return "SYS_ONLY", None
    if sb is None: return ("SYS_ASLEEP_BEFORE" if alive_end < rb else "SYS_NEVER"), None
    return ("SYS_EARLIER" if sb < rb else "SAME" if sb == rb else "SYS_LATER"), (sb - rb) * 5
def n_flips(seq): return sum(1 for a, c in zip(seq, seq[1:]) if a != c)
def path_str(labels, times, skip=("NONE", ASLEEP)):
    out = []; last = None
    for l, t in zip(labels, times):
        if l in skip or l == last: continue
        out.append(f"{t} {l}"); last = l
    return " . ".join(out)

IBW = {d: max(b[2] for b in BARS[d][:12]) - min(b[3] for b in BARS[d][:12]) for d in BARS if len(BARS[d]) == NB}     # initial-balance width per session
def narrow_of(d):
    prior = [IBW[p] for p in sorted(IBW) if p < d][-10:]
    return ((IBW[d] <= 0.7 * statistics.median(prior)), statistics.median(prior)) if len(prior) >= 5 else (None, None)

REF, SYSB, DAYINFO, CSV_ROWS, PREV = {}, {}, {}, [], {}
for d in DAYS:
    bars = BARS[d]; prev = None if (d in ROLL_DAYS or PRIOR[d] is None) else prev_profile_from(BARS[PRIOR[d]]); PREV[d] = prev
    ot30, _w = ref_opening(bars[:6], prev)
    if prev is None and ot30 == "OPEN_AUCTION_OUT": ot30 = "OPEN_AUCTION_UNREF"          # no prior-session reference (roll day) -> in/out of range unknowable
    narrow, ib_med = narrow_of(d)
    REF[d] = [ref_state(bars[:b], prev, ot30, narrow) for b in range(NB)]
    ref_eod, f_eod = ref_daytype_core(bars); ref_eod_b = ref_state(bars, prev, ot30, narrow)["label_b"]
    rows = VEC.get(d, []); lastrow = {}; cnt = collections.Counter()
    for r in rows: lastrow[r["b"]] = r; cnt[r["b"]] += 1
    last_b = max(cnt) if cnt else -1
    alive_end = -1 if not rows else (last_b if last_b < 54 else NB - 1)             # a day whose rows stop before 14:00 ET = the system went to sleep
    cur = None; sysb = []
    for b in range(NB):
        if b > alive_end: sysb.append(dict(state="ASLEEP", src="", n=0, row=None, label=ASLEEP)); continue
        if b in lastrow: cur = lastrow[b]; src = "row"
        elif cur is not None: src = "ffill"
        else: src = "none"
        sysb.append(dict(state="LIVE", src=src, n=cnt.get(b, 0), row=cur, label=sysn(cur["raw"]) if cur is not None else "NONE"))
    SYSB[d] = sysb
    hist = HIST.get(d); eod_rewrite = sysn(hist["day_type"]) if hist else ""
    for b in range(NB):
        st = REF[d][b]; sb = sysb[b]; row = sb["row"]; sl = sb["label"]
        if sb["state"] == "ASLEEP": a_ex = a_co = a_exp = a_exb = ""
        elif b >= 12:
            a_ex = int(sl == st["label"]); a_co = int(sl != "NONE" and fam(sl) == fam(st["label"])); a_exp = ""; a_exb = int(sl == st["label_b"])
        else:
            ex = EXPECT.get(st["ot"]); a_ex = a_co = a_exb = ""
            a_exp = "" if (ex is None or sl == "NONE") else int(sl in ex)
        CSV_ROWS.append(dict(
            date=d, dow=dt.date.fromisoformat(d).strftime("%a"), bucket=b, et_time=bars[b][6], il_time=bars[b][0], bars_seen=b, segment=seg_of(b),
            sys_state=("LIVE" if sb["state"] == "LIVE" else ASLEEP), sys_src=sb["src"], sys_rows_in_bucket=sb["n"],
            sys_label_raw=(row["raw"] if row else ""), sys_label=sl, sys_conf=(row["conf"] if row else ""), sys_phase=(row["phase"] if row else ""),
            sys_opening_type=(row["ot"] if row else ""), sys_extension=(row["ext"] if row else ""), sys_extension_pts=(row["ext_pts"] if row else ""),
            ref_label=st["label"], ref_family=fam(st["label"]), ref_opening_type=st["ot"], ref_ot_basis=st["ot_basis"],
            ref_expect="/".join(EXPECT.get(st["ot"], ())) if b < 12 else "", ref_ib_high=st["ibh"] if st["ibh"] is not None else "", ref_ib_low=st["ibl"] if st["ibl"] is not None else "",
            ref_hi=st["hi"] if st["hi"] is not None else "", ref_lo=st["lo"] if st["lo"] is not None else "", ref_last_close=st["last"] if st["last"] is not None else "",
            ref_sides=st["sides"] if st["sides"] is not None else "", ref_rib=("" if st["rib"] is None else round(st["rib"], 3)),
            ref_close_pos=("" if st["close_pos"] is None else round(st["close_pos"], 3)), ref_note=st["note"],
            agree_exact=a_ex, agree_coarse=a_co, agree_vs_opening_expectation=a_exp, ref_eod=ref_eod, sys_eod_rewrite=(eod_rewrite or "n/a"),
            ref_label_ibw=st["label_b"], agree_exact_ibw=a_exb, ref_eod_ibw=ref_eod_b))
    # ---- day level
    il = [bars[b][0] for b in range(NB)]
    sys_seq = [(b, sb["label"]) for b, sb in enumerate(sysb) if sb["state"] == "LIVE" and sb["label"] != "NONE"]
    ref_seq = [(b, REF[d][b]["label"]) for b in range(12, NB)]
    rb_dir = next((b for b in range(NB) if REF[d][b]["label"] in DIRSET), None); sb_dir = next((b for b, l in sys_seq if l in DIRSET), None)
    rb_tn = next((b for b in range(NB) if REF[d][b]["label"] == "Trend_Normal"), None); sb_tn = next((b for b, l in sys_seq if l == "Trend_Normal"), None)
    cat_d, lag_d = lag_cat(rb_dir, sb_dir, alive_end); cat_t, lag_t = lag_cat(rb_tn, sb_tn, alive_end)
    sb_dir_post = next((b for b, l in sys_seq if b >= 12 and l in DIRSET), None); cat_dp, lag_dp = lag_cat(rb_dir, sb_dir_post, alive_end)   # from the IB lock on
    DAYINFO[d] = dict(
        ib_width=IBW[d], ib_med10=ib_med, ib_narrow=narrow, ref_eod_ibw=ref_eod_b, sb_dir_post=sb_dir_post, lag_dirpost_cat=cat_dp, lag_dirpost_min=lag_dp,
        sys_first_b=(sys_seq[0][0] if sys_seq else None), sys_first_label=(sys_seq[0][1] if sys_seq else ""),
        sys_early_tn=any(l == "Trend_Normal" and b < 12 for b, l in sys_seq), sys_early_dir=any(l in DIRSET and b < 12 for b, l in sys_seq),
        sys_label_b12=(sysb[12]["label"] if sysb[12]["state"] == "LIVE" else ""), sys_label_b24=(sysb[24]["label"] if sysb[24]["state"] == "LIVE" else ""),
        date=d, dow=dt.date.fromisoformat(d).strftime("%a"), system=("ASLEEP" if alive_end < 0 else "TRUNCATED" if alive_end < NB - 1 else "LIVE"), alive_end=alive_end,
        sys_rows=len(rows), roll_day=(d in ROLL_DAYS), ibh=f_eod["ibh"], ibl=f_eod["ibl"], rng=f_eod["hi"] - f_eod["lo"], rib=f_eod["rib"], close_pos=f_eod["close_pos"],
        ref_eod=ref_eod, sides_eod=f_eod["sides"], ext_dir_eod=f_eod["ext_dir"], ref_ot30=ot30, eod_rewrite=eod_rewrite, eod_rewrite_ot=(hist["opening_type"] if hist else ""),
        sys_final=(sys_seq[-1][1] if sys_seq else ""), sys_first=(f"{il[sys_seq[0][0]]} {sys_seq[0][1]}" if sys_seq else ""),
        sys_ot_b6=(sysb[6]["row"]["ot"] if sysb[6]["row"] else ""), sys_ot_final=(next((sb["row"]["ot"] for sb in reversed(sysb) if sb["row"]), "")),
        sys_ot_flips=n_flips([sb["row"]["ot"] for sb in sysb if sb["row"] and sb["row"]["ot"]]),
        sys_flips=n_flips([l for _, l in sys_seq]), sys_flips_post=n_flips([l for b, l in sys_seq if b >= 12]),
        sys_fam_flips=n_flips([fam(l) for b, l in sys_seq if b >= 12]),
        ref_flips=n_flips([l for _, l in ref_seq]), ref_fam_flips=n_flips([fam(l) for _, l in ref_seq]),
        rb_dir=rb_dir, sb_dir=sb_dir, lag_dir_cat=cat_d, lag_dir_min=lag_d, rb_tn=rb_tn, sb_tn=sb_tn, lag_tn_cat=cat_t, lag_tn_min=lag_t,
        ref_dir_il=(il[rb_dir] if rb_dir is not None else ""), sys_dir_il=(il[sb_dir] if sb_dir is not None else ""),
        ref_tn_il=(il[rb_tn] if rb_tn is not None else ""), sys_tn_il=(il[sb_tn] if sb_tn is not None else ""),
        sys_path=path_str([sb["label"] for sb in sysb], il), ref_path=path_str([REF[d][b]["label"] for b in range(NB)], il, skip=("NONE", ASLEEP)),
        tn_conflicts=sum(1 for b in range(NB) if REF[d][b]["note"]))
    di_ = DAYINFO[d]; nz = lambda x: "" if x is None else x
    for row in CSV_ROWS[-NB:]:      # day-level columns repeated on the 78 rows of the day (lag sign: + = the system is later than the reference)
        row.update(day_system_state=di_["system"], day_ref_first_dir_il=di_["ref_dir_il"], day_sys_first_dir_il=di_["sys_dir_il"], day_lag_dir_cat=di_["lag_dir_cat"], day_lag_dir_min=nz(di_["lag_dir_min"]),
                   day_lag_dir_from_lock_cat=di_["lag_dirpost_cat"], day_lag_dir_from_lock_min=nz(di_["lag_dirpost_min"]), day_ref_first_tn_il=di_["ref_tn_il"], day_sys_first_tn_il=di_["sys_tn_il"],
                   day_lag_tn_cat=di_["lag_tn_cat"], day_lag_tn_min=nz(di_["lag_tn_min"]), day_sys_flips_post_ib=di_["sys_flips_post"], day_ref_flips_post_ib=di_["ref_flips"],
                   day_sys_family_flips=di_["sys_fam_flips"], day_ref_family_flips=di_["ref_fam_flips"])

os.makedirs(OUT, exist_ok=True)
P_INTRA = os.path.join(OUT, f"daytype_intraday_{TAG}.csv"); P_TRADES = os.path.join(OUT, f"daytype_trades_{TAG}.csv")
with open(P_INTRA, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(CSV_ROWS[0].keys())); w.writeheader(); w.writerows(CSV_ROWS)
print(f"wrote {P_INTRA}: {len(CSV_ROWS)} rows ({len(DAYS)} days x {NB} buckets)")


# ------------------------------------------------------------------------------------------------ live trades (task C)
TR = []
for t in TRADES:
    d = t["date"]; b = bucket_of(t["et"])
    if d not in REF or b is None: print(f"WARN trade {t['id']} on {d} {t['et']} ET is outside the audited days/RTH - skipped"); continue
    st = REF[d][b]; sb = SYSB[d][b]; D = 1 if t["dir"].upper() == "LONG" else -1; P = t["px"]
    verdict, why = doctrine_verdict(st, D, P); verdict_b, why_b = doctrine_verdict(st, D, P, "B")
    fut = REF[d][min(b + 3, NB - 1)]      # HINDSIGHT diagnostic only (15 minutes later), never used for the verdict: did the reference later accept the side the trade was on?
    fut_side = "up" if fut["ext_dir"] > 0 else "down" if fut["ext_dir"] < 0 else ("both" if fut["sides"] == 2 else "none" if fut["sides"] == 0 else "")
    qq = (P - st["lo"]) / (st["hi"] - st["lo"]) if st["hi"] is not None and st["hi"] > st["lo"] else None
    pib = (P - st["ibl"]) / (st["ibh"] - st["ibl"]) if st["ibh"] is not None and st["ibh"] > st["ibl"] else None
    pv = PREV[d]
    ir = "N/A" if pv is None else ("RESPONSIVE" if ((D > 0 and P < pv["val"]) or (D < 0 and P > pv["vah"])) else "INITIATIVE")
    sl = sb["label"]
    if b >= 12: sv = "MATCH" if sl == st["label"] else "MISMATCH"
    else:
        ex = EXPECT.get(st["ot"]); sv = "PRE_IB_n/a" if (ex is None or sl == "NONE") else ("EXPECTED" if sl in ex else "NOT_EXPECTED")
    TR.append(dict(
        trade_id=t["id"], date=d, dow=dt.date.fromisoformat(d).strftime("%a"), et_time=t["et"], il_time=t["il"], bucket=b, system=t["fs"], direction=t["dir"], pattern=t["pattern"],
        entry_kind=entry_kind(t["pattern"]), entry_price=P, ref_label=st["label"], ref_family=fam(st["label"]), ref_opening_type=st["ot"], ref_ot_basis=st["ot_basis"],
        ref_ib_high=("" if st["ibh"] is None else st["ibh"]), ref_ib_low=("" if st["ibl"] is None else st["ibl"]), ref_hi=("" if st["hi"] is None else st["hi"]),
        ref_lo=("" if st["lo"] is None else st["lo"]), q_in_range=("" if qq is None else round(qq, 3)), pos_in_ib=("" if pib is None else round(pib, 3)),
        ref_accepted_side=("up" if st["ext_dir"] > 0 else "down" if st["ext_dir"] < 0 else ("both" if st["sides"] == 2 else "none" if st["sides"] == 0 else "")),
        init_vs_resp_prior_value=ir, sys_label_vector=sl, sys_day_type_at_entry=(sysn(t["dte"]) if t["dte"] else "NONE"), sys_vs_ref=sv,
        doctrine_verdict=verdict, verdict_reason=why, verdict_arguable=int("ARGUABLE" in why), ref_label_ibw=st["label_b"], doctrine_verdict_ibw=verdict_b,
        verdict_reason_ibw=why_b, hindsight_ref_label_plus15m=fut["label"], hindsight_ref_accepted_side_plus15m=fut_side,
        hindsight_ref_confirms_trade_side_15m=int(fut["ext_dir"] == D), ref_eod=DAYINFO[d]["ref_eod"], exit_reason=t["exit"], contracts=t["k"], pnl=t["pnl"], broker_verified=int(t["ver"]),
        pnl_books_pnl_usd=t["pnl_books"], entry_ts_missing=int(t["no_ts"])))
with open(P_TRADES, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(TR[0].keys())); w.writeheader(); w.writerows(TR)
print(f"wrote {P_TRADES}: {len(TR)} live closed trades")

def agg(rows, key):
    out = collections.OrderedDict()
    for r in rows:
        a = out.setdefault(key(r), dict(n=0, n_ver=0, pnl_ver=0.0, wins_ver=0, n_unv=0, pnl_unv_books=0.0))
        a["n"] += 1
        if r["broker_verified"]: a["n_ver"] += 1; a["pnl_ver"] += r["pnl"]; a["wins_ver"] += int(r["pnl"] > 0)
        else: a["n_unv"] += 1; a["pnl_unv_books"] += r["pnl"]
    return out

# ------------------------------------------------------------------------------------------------ candidate gate audit (complement)
CAND = collections.OrderedDict()
for d in DAYS:
    for r in VEC.get(d, []):
        if not r["cls"] or r["dir"].upper() not in ("LONG", "SHORT") or SYSB[d][r["b"]]["state"] != "LIVE": continue
        P = fnum(r["px"])
        if P is None: continue
        CAND.setdefault((d, r["b"], r["system"], r["cls"], r["dir"].upper()), []).append((r["blocked"], P))
cand_rows = []
for (d, b, sy, cl, di), lst in CAND.items():
    st = REF[d][b]; verdict, _ = doctrine_verdict(st, 1 if di == "LONG" else -1, lst[0][1]); verdict_b, _ = doctrine_verdict(st, 1 if di == "LONG" else -1, lst[0][1], "B")
    passed = any(not x[0] for x in lst); gate = "PASS" if passed else (lst[-1][0] or "PASS")
    cand_rows.append(dict(date=d, b=b, system=sy, cls=cl, dir=di, verdict=verdict, verdict_b=verdict_b, gate=gate, ref=st["label"], ref_b=st["label_b"], seg=seg_of(b), ek=entry_kind(cl)))

# ------------------------------------------------------------------------------------------------ summaries (task D)
LIVE_DAYS = [d for d in DAYS if DAYINFO[d]["system"] != "ASLEEP"]
segs = {s: dict(n=0, fresh=0, none=0, n_post=0, n_post_fresh=0, ex=0, co=0, ex_fresh=0, co_fresh=0, exb=0, exp_n=0, exp_ok=0) for s in SEGS}
conf, conf_co, conf_b = collections.Counter(), collections.Counter(), collections.Counter(); day_post = {d: [0, 0] for d in LIVE_DAYS}
EXT = collections.Counter(); EXTD = {d: [0, 0] for d in LIVE_DAYS}      # system 'extension' field vs the plain geometry (any trade beyond an IB edge), post-IB live buckets
for d in LIVE_DAYS:
    for b in range(NB):
        sb = SYSB[d][b]
        if sb["state"] != "LIVE": continue
        s = segs[seg_of(b)]; st = REF[d][b]; sl = sb["label"]; s["n"] += 1; fresh = sb["src"] == "row"; s["fresh"] += int(fresh); s["none"] += int(sl == "NONE")
        if b >= 12:
            ok = sl == st["label"]; okc = sl != "NONE" and fam(sl) == fam(st["label"])
            s["n_post"] += 1; s["ex"] += int(ok); s["co"] += int(okc); day_post[d][0] += int(ok); day_post[d][1] += 1; s["exb"] += int(sl == st["label_b"])
            if fresh: s["n_post_fresh"] += 1; s["ex_fresh"] += int(ok); s["co_fresh"] += int(okc)
            if sb["row"] is not None and st["ibh"] is not None:
                geo = "both" if (st["hi"] > st["ibh"] and st["lo"] < st["ibl"]) else "up" if st["hi"] > st["ibh"] else "down" if st["lo"] < st["ibl"] else "none"
                se = sb["row"]["ext"] or "none"; EXT[(se, geo)] += 1; EXTD[d][int(se == geo)] += 1
            conf[(sl, st["label"])] += 1; conf_co[("NONE" if sl == "NONE" else fam(sl), fam(st["label"]))] += 1; conf_b[(sl, st["label_b"])] += 1
        else:
            ex = EXPECT.get(st["ot"])
            if ex is not None and sl != "NONE": s["exp_n"] += 1; s["exp_ok"] += int(sl in ex)
for d in LIVE_DAYS: DAYINFO[d]["agree_post"] = (day_post[d][0] / day_post[d][1]) if day_post[d][1] else None

def lag_sum(cat_key, min_key):
    cats = collections.Counter(DAYINFO[d][cat_key] for d in DAYS); mins = [DAYINFO[d][min_key] for d in DAYS if DAYINFO[d][min_key] is not None]
    return dict(cats=dict(cats), n=len(mins), median=(statistics.median(mins) if mins else None), mean=(statistics.mean(mins) if mins else None),
                min=(min(mins) if mins else None), max=(max(mins) if mins else None), values={d: DAYINFO[d][min_key] for d in DAYS if DAYINFO[d][min_key] is not None})
LAG_DIR, LAG_TN = lag_sum("lag_dir_cat", "lag_dir_min"), lag_sum("lag_tn_cat", "lag_tn_min"); LAG_DIRPOST = lag_sum("lag_dirpost_cat", "lag_dirpost_min")
# the provisional 30-minute label: what the system said before the IB lock, and what became of it
EARLY = []
for d in LIVE_DAYS:
    i = DAYINFO[d]; pre = [(b, SYSB[d][b]["label"]) for b in range(12) if SYSB[d][b]["state"] == "LIVE" and SYSB[d][b]["label"] != "NONE"]
    EARLY.append(dict(date=d, first=(f"{BARS[d][pre[0][0]][0]} {pre[0][1]}" if pre else ""), pre_labels=sorted({l for _, l in pre}), early_tn=i["sys_early_tn"], early_dir=i["sys_early_dir"],
                      at_lock=i["sys_label_b12"], at_1130=i["sys_label_b24"], final=i["sys_final"], ref_eod=i["ref_eod"], rewrite=i["eod_rewrite"], ot30=i["ref_ot30"], sys_ot6=i["sys_ot_b6"]))
OTM = dict(n=len(LIVE_DAYS), at6=sum(1 for d in LIVE_DAYS if DAYINFO[d]["sys_ot_b6"] == DAYINFO[d]["ref_ot30"]), final=sum(1 for d in LIVE_DAYS if DAYINFO[d]["sys_ot_final"] == DAYINFO[d]["ref_ot30"]),
           hist=sum(1 for d in LIVE_DAYS if DAYINFO[d]["eod_rewrite_ot"] == DAYINFO[d]["ref_ot30"]), sys_counts=dict(collections.Counter(DAYINFO[d]["sys_ot_final"] for d in LIVE_DAYS)),
           ref_counts=dict(collections.Counter(DAYINFO[d]["ref_ot30"] for d in DAYS)))
# alignment QA: when the system's label changes between two consecutive DECISION rows of a day, how many seconds into the 5-minute bucket is the first row with the new label?
QA = []
for d in LIVE_DAYS:
    prev_lab = None
    for r in VEC.get(d, []):
        lab = sysn(r["raw"])
        if prev_lab is not None and lab != prev_lab and lab != "NONE" and prev_lab != "NONE":
            h, m, s_ = (int(x) for x in r["hms"][:8].split(":")); QA.append(((h * 3600 + m * 60 + s_ - (9 * 3600 + 30 * 60)) % 300, r["b"]))
        prev_lab = lab
ALIGN = dict(n=len(QA), within15=sum(1 for s_, _ in QA if s_ <= 15), within60=sum(1 for s_, _ in QA if s_ <= 60), secs=sorted(s_ for s_, _ in QA))
FL = dict(sys_post=[DAYINFO[d]["sys_flips_post"] for d in LIVE_DAYS], ref_post=[DAYINFO[d]["ref_flips"] for d in LIVE_DAYS],
          sys_fam=[DAYINFO[d]["sys_fam_flips"] for d in LIVE_DAYS], ref_fam=[DAYINFO[d]["ref_fam_flips"] for d in LIVE_DAYS], sys_all=[DAYINFO[d]["sys_flips"] for d in LIVE_DAYS],
          ref_all_days=[DAYINFO[d]["ref_flips"] for d in DAYS], sys_ot=[DAYINFO[d]["sys_ot_flips"] for d in LIVE_DAYS])
EOD = dict(
    rewrite_vs_ref=[(d, DAYINFO[d]["eod_rewrite"], DAYINFO[d]["ref_eod"]) for d in DAYS if DAYINFO[d]["eod_rewrite"]],
    live_final_vs_rewrite=[(d, DAYINFO[d]["sys_final"], DAYINFO[d]["eod_rewrite"]) for d in LIVE_DAYS if DAYINFO[d]["eod_rewrite"] and DAYINFO[d]["system"] == "LIVE"],
    live_final_vs_ref=[(d, DAYINFO[d]["sys_final"], DAYINFO[d]["ref_eod"]) for d in LIVE_DAYS if DAYINFO[d]["system"] == "LIVE"])
CPS = collections.OrderedDict([("10:30", 12), ("11:00", 18), ("11:30", 24), ("12:00", 30), ("13:00", 42), ("14:00", 54), ("15:00", 66)])   # ET; IL = +7h
CP = collections.OrderedDict()
for name, b in CPS.items():
    c = dict(n_sys=0, sys_ok=0, sys_ok_co=0, n_ref=0, ref_ok=0, ref_ok_co=0, same_sys_ref=0)
    for d in DAYS:
        eod = DAYINFO[d]["ref_eod"]; rl = REF[d][b]["label"]; c["n_ref"] += 1; c["ref_ok"] += int(rl == eod); c["ref_ok_co"] += int(fam(rl) == fam(eod))
        sb = SYSB[d][b]
        if sb["state"] != "LIVE": continue
        sl = sb["label"]; c["n_sys"] += 1; c["sys_ok"] += int(sl == eod); c["sys_ok_co"] += int(sl != "NONE" and fam(sl) == fam(eod))
    CP[name] = c
rows_fresh = sum(1 for d in LIVE_DAYS for b in range(NB) if SYSB[d][b]["state"] == "LIVE" and SYSB[d][b]["src"] == "row"); rows_live = sum(1 for d in LIVE_DAYS for b in range(NB) if SYSB[d][b]["state"] == "LIVE")
by_verdict = agg(TR, lambda r: r["doctrine_verdict"]); by_ref = agg(TR, lambda r: r["ref_label"]); by_sysref = agg(TR, lambda r: r["sys_vs_ref"])
by_verdict_b = agg(TR, lambda r: r["doctrine_verdict_ibw"]); by_ref_b = agg(TR, lambda r: r["ref_label_ibw"]); by_arg = agg(TR, lambda r: (r["doctrine_verdict"], "arguable_NV_fade" if r["verdict_arguable"] else "firm"))
by_agree_b = agg(TR, lambda r: (r["doctrine_verdict_ibw"], "sys=ref" if r["sys_vs_ref"] == "MATCH" else "sys!=ref" if r["sys_vs_ref"] == "MISMATCH" else "pre-IB"))
by_ir = agg(TR, lambda r: r["init_vs_resp_prior_value"]); by_ek = agg(TR, lambda r: (r["entry_kind"], r["doctrine_verdict"]))
by_dte = agg(TR, lambda r: r["sys_day_type_at_entry"]); by_sys = agg(TR, lambda r: (r["sys_label_vector"], r["ref_label"]))
CANDT = collections.Counter((c["verdict"], c["gate"]) for c in cand_rows); CANDP = collections.Counter((c["ref"], c["verdict"]) for c in cand_rows if c["gate"] == "PASS")
CANDS = collections.Counter((c["seg"], c["verdict"], c["gate"] == "PASS") for c in cand_rows)


# ------------------------------------------------------------------------------------------------ print + JSON
def pct(a, b): return "n/a" if not b else f"{100.0 * a / b:.1f}%"
def med(x): return "n/a" if not x else f"{statistics.median(x):g}"
def mean(x): return "n/a" if not x else f"{statistics.mean(x):.2f}"
print("\n== COVERAGE ==")
print(f"days audited {len(DAYS)}: {DAYS[0]} .. {DAYS[-1]} | system LIVE {sum(DAYINFO[d]['system'] == 'LIVE' for d in DAYS)} · TRUNCATED {[d for d in DAYS if DAYINFO[d]['system'] == 'TRUNCATED']} · ASLEEP {[d for d in DAYS if DAYINFO[d]['system'] == 'ASLEEP']}")
SKIPPED = {d: len(v) for d, v in VEC.items() if d not in set(DAYS)}
print(f"vector days with no bars (weekend tests, skipped): {SKIPPED}")
print(f"live buckets {rows_live} · buckets with a fresh DECISION row {rows_fresh} ({pct(rows_fresh, rows_live)}) · rest forward-filled")
print(f"roll days (prior-session refs neutralised): {sorted(ROLL_DAYS)} · TN-close-opposite notes: {sum(DAYINFO[d]['tn_conflicts'] for d in DAYS)} buckets")
print("\n== AGREEMENT BY SEGMENT (live buckets) ==")
for s in SEGS:
    a = segs[s]
    if s == "PRE_IB": print(f"{s:22s} buckets {a['n']:4d} · sys label NONE {a['none']:4d} ({pct(a['none'], a['n'])}) · consistent with opening expectation {a['exp_ok']}/{a['exp_n']} ({pct(a['exp_ok'], a['exp_n'])})")
    else: print(f"{s:22s} buckets {a['n']:4d} · exact {a['ex']}/{a['n_post']} ({pct(a['ex'], a['n_post'])}) · coarse {a['co']}/{a['n_post']} ({pct(a['co'], a['n_post'])}) · fresh-row-only exact {a['ex_fresh']}/{a['n_post_fresh']} ({pct(a['ex_fresh'], a['n_post_fresh'])}) · sys NONE {a['none']}")
tn = sum(segs[s]["n_post"] for s in SEGS[1:]); print(f"{'ALL post-IB':22s} exact {sum(segs[s]['ex'] for s in SEGS[1:])}/{tn} ({pct(sum(segs[s]['ex'] for s in SEGS[1:]), tn)}) · coarse {sum(segs[s]['co'] for s in SEGS[1:])}/{tn} ({pct(sum(segs[s]['co'] for s in SEGS[1:]), tn)})")
print("\n== CONFUSION (rows = system, cols = reference; post-IB live buckets) ==")
SL = ["NONE"] + LABELS
print("sys \\ ref".ljust(18) + "".join(x[:10].rjust(11) for x in LABELS) + "  total")
for a in SL:
    print(a.ljust(18) + "".join(str(conf.get((a, c), 0)).rjust(11) for c in LABELS) + str(sum(conf.get((a, c), 0) for c in LABELS)).rjust(7))
print("coarse (BALANCE / DIRECTIONAL / TWO_SIDED):")
for a in ["NONE", "BALANCE", "DIRECTIONAL", "TWO_SIDED"]: print(a.ljust(14) + "".join(str(conf_co.get((a, c), 0)).rjust(13) for c in ["BALANCE", "DIRECTIONAL", "TWO_SIDED"]))
colsA = {c: sum(conf.get((a, c), 0) for a in SL) for c in LABELS}; colsB = {c: sum(conf_b.get((a, c), 0) for a in SL) for c in LABELS}
print(f"BASE RATE - reference label share of the {tn} post-IB live buckets (a constant guess scores exactly this):")
print("   REF-A:", {c: f"{v} ({pct(v, tn)})" for c, v in colsA.items()}); print("   REF-B:", {c: f"{v} ({pct(v, tn)})" for c, v in colsB.items()})
print(f"system label share: {dict((a, f'{sum(conf.get((a, c), 0) for c in LABELS)} ({pct(sum(conf.get((a, c), 0) for c in LABELS), tn)})') for a in SL)}")
print("\n== LAG to first directional label (Normal_Variation/Trend_Normal), minutes, + = system later ==")
for d in DAYS:
    i = DAYINFO[d]; print(f"{d} {i['dow']} {i['system']:9s} ref@{i['ref_dir_il'] or '-':5s} sys@{i['sys_dir_il'] or '-':5s} {i['lag_dir_cat']:18s} lag {i['lag_dir_min']} | TN ref@{i['ref_tn_il'] or '-':5s} sys@{i['sys_tn_il'] or '-':5s} {i['lag_tn_cat']:18s} lag {i['lag_tn_min']}")
print(f"directional: {LAG_DIR['cats']} median {LAG_DIR['median']} mean {LAG_DIR['mean']} n={LAG_DIR['n']} range {LAG_DIR['min']}..{LAG_DIR['max']}")
print(f"trend_normal: {LAG_TN['cats']} median {LAG_TN['median']} mean {LAG_TN['mean']} n={LAG_TN['n']} range {LAG_TN['min']}..{LAG_TN['max']}")
print("\n== FLIPS per live day (post-IB exact | coarse | pre+post all), system vs reference ==")
print(f"system post-IB flips: sum {sum(FL['sys_post'])} mean {mean(FL['sys_post'])} median {med(FL['sys_post'])} · reference (same days): sum {sum(FL['ref_post'])} mean {mean(FL['ref_post'])} median {med(FL['ref_post'])}")
print(f"coarse family flips: system sum {sum(FL['sys_fam'])} mean {mean(FL['sys_fam'])} · reference sum {sum(FL['ref_fam'])} mean {mean(FL['ref_fam'])} · system incl. provisional {sum(FL['sys_all'])} · system opening-type flips sum {sum(FL['sys_ot'])} mean {mean(FL['sys_ot'])}")
print("\n== EOD ==")
for k, v in EOD.items(): print(f"{k}: agree {sum(1 for _, a, c in v if a == c)}/{len(v)} ({pct(sum(1 for _, a, c in v if a == c), len(v))}) · coarse {sum(1 for _, a, c in v if fam(a) == fam(c))}/{len(v)}")
print("\n== CHECKPOINTS: label at time T (ET) equals the day's EOD reference label ==")
for name, c in CP.items():
    print(f"{name} ET ({int(name[:2]) + 7}:{name[3:]} IL) system exact {c['sys_ok']}/{c['n_sys']} ({pct(c['sys_ok'], c['n_sys'])}) coarse {pct(c['sys_ok_co'], c['n_sys'])} | reference exact {c['ref_ok']}/{c['n_ref']} ({pct(c['ref_ok'], c['n_ref'])}) coarse {pct(c['ref_ok_co'], c['n_ref'])}")
print("\n== DAY TABLE ==")
trades_by_day = agg_day = collections.defaultdict(lambda: [0, 0.0, 0, 0.0])
for r in TR:
    a = agg_day[r["date"]]; a[0] += 1
    if r["broker_verified"]: a[1] += r["pnl"]; a[2] += 1
    else: a[3] += r["pnl"]
for d in DAYS:
    i = DAYINFO[d]; a = agg_day.get(d, [0, 0.0, 0, 0.0]); ap = i.get("agree_post"); aps = "n/a" if ap is None else "%.0f%%" % (100 * ap)
    print(f"{d} {i['dow']} {i['system'][:5]:5s} IB {i['ibl']}-{i['ibh']} rng {i['rng']:.1f} rib {i['rib']:.2f} cp {i['close_pos']:.2f} | REF_EOD {i['ref_eod']:16s} rewrite {i['eod_rewrite'] or 'n/a':16s} sysFinal {i['sys_final'] or '-':16s} | agree_post {aps:>4s} flips sys {i['sys_flips_post']} ref {i['ref_flips']} | ot30 {i['ref_ot30'][5:]:18s} sys_ot@6 {i['sys_ot_b6'][5:]:18s} sys_ot_final {i['sys_ot_final'][5:]:18s} | trades {a[0]} broker {a[1]:+.2f} ({a[2]}) books {a[3]:+.2f}")
print("\n== PATHS (IL time, label changes) ==")
for d in DAYS:
    i = DAYINFO[d]; print(f"{d}\n   SYS: {i['sys_path']}\n   REF: {i['ref_path']}")
print("\n== TRADES: doctrine verdict ==")
def show(title, ag):
    print(title)
    for k, a in ag.items(): print(f"   {str(k):52s} n {a['n']:3d} | broker n {a['n_ver']:3d} sum {a['pnl_ver']:+9.2f} win {a['wins_ver']} | unverified n {a['n_unv']} books {a['pnl_unv_books']:+.2f}")
show("by verdict", by_verdict); show("by reference label at entry", by_ref); show("system vs reference at entry", by_sysref)
show("initiative / responsive vs prior value", by_ir); show("by system day_type_at_entry", by_dte); show("entry_kind x verdict", by_ek)
print("\n== TRADE LIST ==")
for r in TR: print(f"#{r['trade_id']} {r['date']} {r['il_time'][:5]}IL S{r['system']} {r['direction']:5s} {r['pattern']:24s} px {r['entry_price']:.2f} q {r['q_in_range']} | REF {r['ref_label']:28s} SYS {r['sys_label_vector']:16s} dte {r['sys_day_type_at_entry']:16s} {r['sys_vs_ref']:12s} | {r['doctrine_verdict']:13s} | {r['exit_reason']:20s} pnl {r['pnl']:+8.2f} {'broker' if r['broker_verified'] else 'BOOKS '} | {r['verdict_reason']}")
print("\n== CANDIDATES (distinct day x bucket x system x pattern x direction) ==")
gates = sorted({g for _, g in CANDT}); print("verdict".ljust(15) + "".join(g[:22].rjust(24) for g in gates))
for v in ["WITH_DOCTRINE", "AGAINST", "UNCLEAR"]: print(v.ljust(15) + "".join(str(CANDT.get((v, g), 0)).rjust(24) for g in gates))
print("PASS candidates by reference label x verdict:")
for k, v in sorted(CANDP.items()): print(f"   {k}: {v}")
print("candidates by segment x verdict x passed:")
for k, v in sorted(CANDS.items()): print(f"   {k}: {v}")
print("\n== VARIANT REF-B (Nontrend only when IB <= 0.7 x median IB of the previous 10 sessions, otherwise Normal) ==")
for s in SEGS[1:]:
    a = segs[s]; print(f"{s:22s} exact(B) {a['exb']}/{a['n_post']} ({pct(a['exb'], a['n_post'])}) vs exact(A) {a['ex']}/{a['n_post']} ({pct(a['ex'], a['n_post'])})")
print(f"{'ALL post-IB':22s} exact(B) {sum(segs[s]['exb'] for s in SEGS[1:])}/{tn} ({pct(sum(segs[s]['exb'] for s in SEGS[1:]), tn)})")
print("confusion B (rows = system, cols = reference B):")
print("sys \\ ref".ljust(18) + "".join(x[:10].rjust(11) for x in LABELS) + "  total")
for a in SL:
    print(a.ljust(18) + "".join(str(conf_b.get((a, c), 0)).rjust(11) for c in LABELS) + str(sum(conf_b.get((a, c), 0) for c in LABELS)).rjust(7))
print("days whose reference EOD differs between A and B:", {d: (DAYINFO[d]["ref_eod"], DAYINFO[d]["ref_eod_ibw"]) for d in DAYS if DAYINFO[d]["ref_eod_ibw"] != DAYINFO[d]["ref_eod"]})
print("IB width / median of previous 10 sessions:", {d: (round(DAYINFO[d]["ib_width"], 2), None if DAYINFO[d]["ib_med10"] is None else round(DAYINFO[d]["ib_med10"], 2), DAYINFO[d]["ib_narrow"]) for d in DAYS})
HOURLY = collections.OrderedDict()
for d in LIVE_DAYS:
    for b in range(12, NB):
        sb = SYSB[d][b]
        if sb["state"] != "LIVE": continue
        a = HOURLY.setdefault(b // 12, [0, 0, 0, 0, 0]); sl = sb["label"]; st = REF[d][b]
        a[0] += 1; a[1] += int(sl == st["label"]); a[2] += int(sl != "NONE" and fam(sl) == fam(st["label"])); a[3] += int(sl == st["label_b"]); a[4] += int(sl == "NONE")
print("\n== SYSTEM 'extension' FIELD vs PLAIN GEOMETRY (price traded beyond an IB edge at all; post-IB live buckets; reference hi/lo of the closed bars) ==")
EC = ["none", "up", "down", "both"]; print("sys \\ geo".ljust(10) + "".join(c.rjust(8) for c in EC) + "   total")
for se in EC: print(se.ljust(10) + "".join(str(EXT.get((se, c), 0)).rjust(8) for c in EC) + str(sum(EXT.get((se, c), 0) for c in EC)).rjust(8))
n_ext = sum(EXT.values()); ok_ext = sum(v for (a, c), v in EXT.items() if a == c)
print(f"exact agreement {ok_ext}/{n_ext} ({pct(ok_ext, n_ext)}) | mismatching buckets per day: {[(d, v[0]) for d, v in EXTD.items() if v[0]]}")
print("\n== AGREEMENT BY HOUR AFTER THE OPEN (ET hour h => bucket 12h..12h+11; IL = ET + 7) ==")
for h, a in HOURLY.items(): print(f"h{h} ET {9 + (30 + 60 * h) // 60:02d}:{(30 + 60 * h) % 60:02d}+ : buckets {a[0]:4d} exact(A) {pct(a[1], a[0]):>6s} coarse {pct(a[2], a[0]):>6s} exact(B) {pct(a[3], a[0]):>6s} sysNONE {a[4]}")
def ilt(d, b): return "-" if b is None else BARS[d][b][0]
print("\n== LAG from the IB lock on (system evaluated from bucket 12 only, so the provisional 30-minute label is excluded) ==")
for d in DAYS:
    i = DAYINFO[d]; print(f"{d} {i['dow']} {i['system']:9s} ref_dir@{i['ref_dir_il'] or '-':5s} sys_dir_from_lock@{ilt(d, i['sb_dir_post']):5s} {i['lag_dirpost_cat']:18s} lag {i['lag_dirpost_min']}")
print(f"directional (from the lock): {LAG_DIRPOST['cats']} median {LAG_DIRPOST['median']} mean {LAG_DIRPOST['mean']} n={LAG_DIRPOST['n']} range {LAG_DIRPOST['min']}..{LAG_DIRPOST['max']}")
print("\n== PROVISIONAL SYSTEM LABEL BEFORE THE IB LOCK AND ITS FATE ==")
for e in EARLY:
    print(f"{e['date']} first {e['first']:26s} pre-lock labels {','.join(e['pre_labels']) or '-':36s} earlyTN {int(bool(e['early_tn']))} earlyDIR {int(bool(e['early_dir']))} | @lock {e['at_lock'] or '-':16s} @11:30ET {e['at_1130'] or '-':16s} final {e['final'] or '-':16s} | REF_EOD {e['ref_eod']:16s} rewrite {e['rewrite'] or '-':16s} | ot30 {e['ot30'][5:]:18s} sys_ot@6 {e['sys_ot6'][5:]}")
etn = [e for e in EARLY if e["early_tn"]]; edr = [e for e in EARLY if e["early_dir"]]
print(f"days with a provisional Trend_Normal before the lock: {len(etn)}/{len(EARLY)} | reference EOD of those {dict(collections.Counter(e['ref_eod'] for e in etn))} | system final {dict(collections.Counter(e['final'] for e in etn))} | rewrite {dict(collections.Counter((e['rewrite'] or 'n/a') for e in etn))}")
print(f"days with any directional label (Variation/Trend) before the lock: {len(edr)}/{len(EARLY)} | reference EOD of those {dict(collections.Counter(e['ref_eod'] for e in edr))}")
print("\n== OPENING TYPE (reference on the first 30 minutes vs the system) ==")
print(f"system ot at bucket 6 == reference ot30: {OTM['at6']}/{OTM['n']} ({pct(OTM['at6'], OTM['n'])}) | system final ot == reference ot30: {OTM['final']}/{OTM['n']} ({pct(OTM['final'], OTM['n'])}) | EOD-rewrite ot == reference ot30: {OTM['hist']}/{OTM['n']} ({pct(OTM['hist'], OTM['n'])})")
print(f"system final ot counts {OTM['sys_counts']} | reference ot30 counts over {len(DAYS)} days {OTM['ref_counts']}")
print("\n== ALIGNMENT QA: seconds past the 5-minute boundary at which a changed system label first shows up ==")
print(f"label changes between consecutive DECISION rows {ALIGN['n']} | within 15 s of a boundary {ALIGN['within15']} ({pct(ALIGN['within15'], ALIGN['n'])}) | within 60 s {ALIGN['within60']} ({pct(ALIGN['within60'], ALIGN['n'])}) | median {med(ALIGN['secs'])} s | max {max(ALIGN['secs']) if ALIGN['secs'] else 'n/a'} s")
print("\n== TRADES: variant B, arguable split, system agreement, segment ==")
show("by verdict (variant B reference)", by_verdict_b); show("by reference label (variant B)", by_ref_b); show("verdict A x arguable (Normal_Variation fade at the far edge)", by_arg)
show("verdict B x (system label equals the reference label?)", by_agree_b)
by_seg = agg(TR, lambda r: (seg_of(r["bucket"]), r["doctrine_verdict"])); show("entry segment x verdict A", by_seg)
by_hind = agg(TR, lambda r: (r["doctrine_verdict"], "ref_accepts_trade_side_within_15m" if r["hindsight_ref_confirms_trade_side_15m"] else "no")); show("HINDSIGHT (not used in any verdict): verdict A x did the reference accept the trade's side within 15 minutes?", by_hind)
print("AGAINST(A) trades the reference later confirmed:", [(r["trade_id"], r["date"], r["il_time"][:5], r["ref_label"], r["hindsight_ref_label_plus15m"], r["pnl"]) for r in TR if r["doctrine_verdict"] == "AGAINST" and r["hindsight_ref_confirms_trade_side_15m"]])
print("\n== P&L CUTS used in the report (broker-verified = pnl_sierra; books-only trades are shown separately and never added) ==")
def cut(title, rs):
    v = [r for r in rs if r["broker_verified"]]; u = [r for r in rs if not r["broker_verified"]]
    print(f"   {title:60s} n {len(rs):2d} | broker n {len(v):2d} sum {sum(r['pnl'] for r in v):+9.2f} wins {sum(1 for r in v if r['pnl'] > 0):2d} avg {(sum(r['pnl'] for r in v) / len(v)) if v else 0:+7.2f} | books-only n {len(u)} sum {sum(r['pnl'] for r in u):+7.2f}")
cut("ALL live closed trades", TR)
for sg, cond in (("PRE_IB", lambda r: r["bucket"] < 12), ("POST_IB", lambda r: r["bucket"] >= 12)):
    rs_ = [r for r in TR if cond(r)]; cut(sg, rs_)
    for v_ in ("WITH_DOCTRINE", "AGAINST", "UNCLEAR"):
        cut(f"  {sg} verdict A {v_}", [r for r in rs_ if r["doctrine_verdict"] == v_]); cut(f"  {sg} verdict B {v_}", [r for r in rs_ if r["doctrine_verdict_ibw"] == v_])
for ek_ in sorted({r["entry_kind"] for r in TR}): cut(f"entry_kind {ek_}", [r for r in TR if r["entry_kind"] == ek_])
cut("REVERSAL x POST_IB x AGAINST (A)", [r for r in TR if r["entry_kind"] == "REVERSAL" and r["bucket"] >= 12 and r["doctrine_verdict"] == "AGAINST"])
cut("REVERSAL x POST_IB (any verdict)", [r for r in TR if r["entry_kind"] == "REVERSAL" and r["bucket"] >= 12])
cut("REVERSAL x PRE_IB", [r for r in TR if r["entry_kind"] == "REVERSAL" and r["bucket"] < 12])
for dn_ in ("LONG", "SHORT"): cut(f"direction {dn_}", [r for r in TR if r["direction"].upper() == dn_])
for ir_ in ("RESPONSIVE", "INITIATIVE", "N/A"):
    cut(f"vs prior value: {ir_}", [r for r in TR if r["init_vs_resp_prior_value"] == ir_]); cut(f"  vs prior value: {ir_} x PRE_IB", [r for r in TR if r["init_vs_resp_prior_value"] == ir_ and r["bucket"] < 12]); cut(f"  vs prior value: {ir_} x POST_IB", [r for r in TR if r["init_vs_resp_prior_value"] == ir_ and r["bucket"] >= 12])
cut("system had NO day_type label at entry (day_type_at_entry NONE)", [r for r in TR if r["sys_day_type_at_entry"] == "NONE"])
cut("system label at entry Trend_Normal", [r for r in TR if r["sys_day_type_at_entry"] == "Trend_Normal"])
cut("system label at entry Trend_Normal, without #1806", [r for r in TR if r["sys_day_type_at_entry"] == "Trend_Normal" and str(r["trade_id"]) != "1806"])
cut("post-IB, system label == reference label (MATCH)", [r for r in TR if r["bucket"] >= 12 and r["sys_vs_ref"] == "MATCH"]); cut("post-IB, system label != reference label (MISMATCH)", [r for r in TR if r["bucket"] >= 12 and r["sys_vs_ref"] == "MISMATCH"])
def perm_p(w_, a_, n_=20000, seed=7):
    if not w_ or not a_: return None
    rnd = random.Random(seed); obs = statistics.mean(w_) - statistics.mean(a_); pool = list(w_) + list(a_); hit = 0
    for _ in range(n_):
        rnd.shuffle(pool); hit += (statistics.mean(pool[:len(w_)]) - statistics.mean(pool[len(w_):])) >= obs
    return obs, hit / n_
for scope, cond in (("post-IB", lambda r: r["bucket"] >= 12), ("all", lambda r: True)):
    for vk, col in (("A", "doctrine_verdict"), ("B", "doctrine_verdict_ibw")):
        w_ = [r["pnl"] for r in TR if r["broker_verified"] and cond(r) and r[col] == "WITH_DOCTRINE"]; a_ = [r["pnl"] for r in TR if r["broker_verified"] and cond(r) and r[col] == "AGAINST"]
        pr = perm_p(w_, a_); print(f"   permutation test (20000 shuffles, seed 7), {scope}, verdict {vk}: WITH n={len(w_)} mean {statistics.mean(w_):+.2f} vs AGAINST n={len(a_)} mean {statistics.mean(a_):+.2f} -> diff {pr[0]:+.2f}, one-sided p = {pr[1]:.3f}")
CANDT_B = collections.Counter((c["verdict_b"], c["gate"]) for c in cand_rows)
print("candidates verdict(B) x gate:"); gates_b = sorted({g for _, g in CANDT_B}); print("verdict".ljust(15) + "".join(g[:22].rjust(24) for g in gates_b))
for v in ["WITH_DOCTRINE", "AGAINST", "UNCLEAR"]: print(v.ljust(15) + "".join(str(CANDT_B.get((v, g), 0)).rjust(24) for g in gates_b))
if SUMMARY:
    js = dict(parity=PARITY, days=DAYS, dayinfo=DAYINFO, segs=segs,
              conf_b={f"{a}|{c}": v for (a, c), v in conf_b.items()}, hourly={str(h): a for h, a in HOURLY.items()}, lag_dirpost=LAG_DIRPOST, early=EARLY, otm=OTM, align=ALIGN,
              by_verdict_b=by_verdict_b, by_ref_b={str(k): v for k, v in by_ref_b.items()}, by_arg={"|".join(k): v for k, v in by_arg.items()}, by_agree_b={"|".join(k): v for k, v in by_agree_b.items()},
              by_seg={"|".join(k): v for k, v in by_seg.items()}, cand_verdictb_gate={f"{v}|{g}": n for (v, g), n in CANDT_B.items()},
              base_rate=dict(a=colsA, b=colsB, post_ib_buckets=tn), ext_vs_geometry={f"{a}|{c}": v for (a, c), v in EXT.items()}, ext_days={d: v for d, v in EXTD.items()}, by_hind={"|".join(k): v for k, v in by_hind.items()}, conf={f"{a}|{c}": v for (a, c), v in conf.items()}, conf_co={f"{a}|{c}": v for (a, c), v in conf_co.items()},
              lag_dir=LAG_DIR, lag_tn=LAG_TN, flips=FL, eod={k: v for k, v in EOD.items()}, checkpoints=CP, rows_fresh=rows_fresh, rows_live=rows_live,
              by_verdict=by_verdict, by_ref={str(k): v for k, v in by_ref.items()}, by_sysref=by_sysref, by_ir=by_ir, by_dte=by_dte, by_ek={"|".join(k): v for k, v in by_ek.items()},
              cand_verdict_gate={f"{v}|{g}": n for (v, g), n in CANDT.items()}, cand_pass_ref_verdict={f"{a}|{b}": n for (a, b), n in CANDP.items()},
              cand_seg={f"{a}|{b}|{c}": n for (a, b, c), n in CANDS.items()}, trades=TR)
    json.dump(js, open(SUMMARY, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str); print(f"summary json -> {SUMMARY}")
