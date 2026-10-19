#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Opening-type (S1) 30-day audit (2026-10-19): what the system LOCKED (mems26.v9_day_type_history.opening_type) vs a reference
reading of the first 30 minutes off the 5-minute bars (ref_opening from doctrine_audit.py = Dalton pp.63-74), per trading day.
READ-ONLY (SELECT only). Writes docs/reports/OPENING_TYPE_30D_<tag>.md (Hebrew) + docs/reports/opening_type_30d_<tag>.csv.

usage: python3 harness_out/t586/hist/opening_type_30d.py [--start=2026-09-08] [--end=2026-10-16] [--tag=2026-10-19] [--dry]

rth_bars / prev_session_profile / ref_opening / TICK / q / PSQL are COPIED from doctrine_audit.py (super-agent T1, 18.10); the only
change is that the DB is selected per date: live `mems26`, or `mems26_hist` when that holds MORE RTH bars for the date (the live DB
is missing the last 8 bars of 2026-09-10 and 2026-10-09). doctrine_audit.py itself is not modified."""
import sys, os, json, subprocess, collections, datetime as dt, csv, functools

PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
LIVE, HIST = "mems26", "mems26_hist"
TICK = 0.25
opt = {a.split("=")[0][2:]: (a.split("=", 1)[1] if "=" in a else "1") for a in sys.argv[1:] if a.startswith("--")}
START = opt.get("start", "2026-09-08"); END = opt.get("end", "2026-10-16"); TAG = opt.get("tag", "2026-10-19"); DRY = "dry" in opt
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OUT_MD = os.path.join(REPO, "docs", "reports", f"OPENING_TYPE_30D_{TAG}.md")
OUT_CSV = os.path.join(REPO, "docs", "reports", f"opening_type_30d_{TAG}.csv")


def q(sql, db):
    r = subprocess.run([PSQL, "-d", db, "-Atc", sql], capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"psql {db}: {r.stderr.strip()[:300]}")
    return r.stdout.strip().splitlines()


@functools.lru_cache(maxsize=None)
def coverage(s, db):
    """(n RTH bars, first ET time, last ET time) of date s in db."""
    r = q(f"select count(*), min((ts at time zone 'America/New_York')::time), max((ts at time zone 'America/New_York')::time) from v9_bars_5min_woodies "
          f"where symbol='MES' and (ts at time zone 'America/New_York')::date='{s}' and (ts at time zone 'America/New_York')::time between '09:30' and '15:55'", db)
    n, a, b = (r[0].split("|") + ["", ""])[:3]
    return int(n), a, b


def bar_jumps(bars):
    """max |open(i+1) - close(i)| over consecutive bars - a mis-stamped / echoed bar shows up as a jump."""
    return max((abs(b2[1] - b1[4]) for b1, b2 in zip(bars, bars[1:])), default=0.0)


def pick_db(s):
    """live `mems26` unless `mems26_hist` holds MORE RTH bars for the date; on an EQUAL count with DIFFERENT bars the series with the smaller
    bar-to-bar jump wins (2026-09-25: 11 bars 11:55-12:45 ET in `mems26` are echoes of the 12:55-13:45 bars, an hour mis-stamp)."""
    nl, nh = coverage(s, LIVE)[0], coverage(s, HIST)[0]
    if nl == 0 and nh == 0: return None
    if nh > nl: return HIST
    if nl > nh: return LIVE
    a, c = rth_bars_db(s, LIVE), rth_bars_db(s, HIST)
    return HIST if a != c and bar_jumps(c) < bar_jumps(a) else LIVE


@functools.lru_cache(maxsize=None)
def rth_bars_db(s, db):
    rows = q(f"select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close, volume from v9_bars_5min_woodies where symbol='MES' "
             f"and (ts at time zone 'America/New_York')::date='{s}' and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts", db)
    return [(r.split("|")[0], *map(float, r.split("|")[1:6])) for r in rows]


def rth_bars(s):
    db = pick_db(s)
    return rth_bars_db(s, db) if db else []


def prev_session_profile(s):
    """prior RTH session's TPO value area from its own 5-min bars (30-minute letters, 70% around the POC)."""
    cands = []
    for db in (LIVE, HIST):   # the last RTH-bar date < s in either DB (original: single DB)
        rows = q(f"select (ts at time zone 'America/New_York')::date from v9_bars_5min_woodies where symbol='MES' and (ts at time zone 'America/New_York')::date < '{s}' "
                 f"and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts desc limit 1", db)
        if rows: cands.append(rows[0])
    if not cands: return None
    pd_ = max(cands); bars = rth_bars(pd_)
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
    return dict(date=pd_, poc=poc, vah=hi, val=lo, high=max(b[2] for b in bars), low=min(b[3] for b in bars))


def ref_opening(bars, prev):
    """Dalton pp.63-74 on the first 30 minutes (6 bars). Returns (type, note)."""
    if len(bars) < 6: return "UNKNOWN", "fewer than 6 bars"
    o = bars[0][1]; b0h, b0l = bars[0][2], bars[0][3]
    highs = [b[2] for b in bars[:6]]; lows = [b[3] for b in bars[:6]]; closes = [b[4] for b in bars[:6]]
    up_drive = all(c > o for c in closes[1:]) and min(lows[1:]) >= o - 2 * TICK
    dn_drive = all(c < o for c in closes[1:]) and max(highs[1:]) <= o + 2 * TICK
    if up_drive or dn_drive: return "OPEN_DRIVE", "no re-trade of the open in bars 2-6"
    # test-drive: first 1-2 bars probe one side (beyond a prior reference), then the drive goes the other way and holds
    refs = [prev["high"], prev["low"], prev["vah"], prev["val"]] if prev else []
    probe_up = max(highs[:2]) > max([r for r in refs if r > o], default=1e9) if refs else False
    probe_dn = min(lows[:2]) < min([r for r in refs if r < o], default=-1e9) if refs else False
    if probe_up and all(c < o for c in closes[3:]) : return "OPEN_TEST_DRIVE", "probe above a prior reference, drive down"
    if probe_dn and all(c > o for c in closes[3:]) : return "OPEN_TEST_DRIVE", "probe below a prior reference, drive up"
    # rejection-reverse: a drive of >= 4 pts that comes back through the open within the 30 minutes
    if (max(highs[:3]) - o >= 4 and min(lows[3:]) < o) or (o - min(lows[:3]) >= 4 and max(highs[3:]) > o): return "OPEN_REJECTION_REVERSE", "drive then back through the open"
    if prev and prev["low"] <= o <= prev["high"]: return "OPEN_AUCTION_IN", "rotation around the open inside the prior range"
    return "OPEN_AUCTION_OUT", "rotation around the open outside the prior range" if prev else "no prior reference"


# ───────────────────────────── new code (not in doctrine_audit.py) ─────────────────────────────
WD_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WD_HE = ["ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "שבת", "א׳"]
DRIVE_REFS = ("OPEN_DRIVE", "OPEN_TEST_DRIVE", "OPEN_REJECTION_REVERSE")
TYPES = ["OPEN_DRIVE", "OPEN_TEST_DRIVE", "OPEN_REJECTION_REVERSE", "OPEN_AUCTION_IN", "OPEN_AUCTION_OUT"]
NO_DATA = "אין נתונים — המק ישן"


def retrade_bar(bars):
    """Bar number (2..6) at which a one-sided drive from the open is first definitively broken; None = never. Exactly the OPEN_DRIVE test of
    ref_opening: every close of bars 2-6 on one side of the open AND no wick through the open by more than 2 ticks."""
    o = bars[0][1]; highs = [b[2] for b in bars[:6]]; lows = [b[3] for b in bars[:6]]; closes = [b[4] for b in bars[:6]]
    up_fail = next((i + 1 for i in range(1, 6) if closes[i] <= o or lows[i] < o - 2 * TICK), None)
    dn_fail = next((i + 1 for i in range(1, 6) if closes[i] >= o or highs[i] > o + 2 * TICK), None)
    return None if up_fail is None or dn_fail is None else max(up_fail, dn_fail)


def ref_direction(bars, typ, note):
    """side the reference reading implies: DRIVE = the drive side; TEST_DRIVE = the drive after the failed probe; REJECTION_REVERSE = the REVERSAL side."""
    o = bars[0][1]; highs = [b[2] for b in bars[:6]]; lows = [b[3] for b in bars[:6]]; closes = [b[4] for b in bars[:6]]
    if typ == "OPEN_DRIVE": return "up" if all(c > o for c in closes[1:]) else "down"
    if typ == "OPEN_TEST_DRIVE": return "down" if note.endswith("drive down") else "up"
    if typ == "OPEN_REJECTION_REVERSE":
        a = max(highs[:3]) - o >= 4 and min(lows[3:]) < o      # up first, then back through the open  -> reversal = down
        b = o - min(lows[:3]) >= 4 and max(highs[3:]) > o      # down first, then back through the open -> reversal = up
        return "down" if a and not b else ("up" if b and not a else "both")
    return ""


def open_loc(o, prev):
    if not prev: return "NO_PRIOR"
    if prev["val"] <= o <= prev["vah"]: return "IN_VALUE"
    if prev["low"] <= o <= prev["high"]: return "IN_RANGE"
    return "ABOVE_RANGE" if o > prev["high"] else "BELOW_RANGE"


def xdb_diff(s):
    """cross-check of the two bar sources on the timestamps both hold: (common bars, max |OHLC diff|, bars that differ)."""
    a = {b[0]: b for b in rth_bars_db(s, LIVE)}; c = {b[0]: b for b in rth_bars_db(s, HIST)}
    common = set(a) & set(c)
    if not common: return 0, None, 0
    mx = 0.0; nd = 0
    for k in common:
        d = max(abs(x - y) for x, y in zip(a[k][1:5], c[k][1:5]))
        mx = max(mx, d); nd += d > 1e-9
    return len(common), round(mx, 4), nd


def echo_times(bars):
    """labels (Israel HH:MM) of bars whose (O,H,L,C,V) is an exact copy of the bar ONE HOUR later (12 bars on) = an hour mis-stamp / echoed bar."""
    return [bars[i][0] for i in range(len(bars) - 12) if bars[i][1:] == bars[i + 12][1:]]


def il2et(lbl, first):
    """Israel label -> ET label, given that the day's first bar (Israel label `first`) is the 09:30 ET open."""
    m = int(lbl[:2]) * 60 + int(lbl[3:]) - (int(first[:2]) * 60 + int(first[3:])) + 9 * 60 + 30
    return f"{m // 60:02d}:{m % 60:02d}"


def diff_labels(s):
    """Israel labels of the bars both sources hold whose OHLCV differ."""
    a = {b[0]: b for b in rth_bars_db(s, LIVE)}; c = {b[0]: b for b in rth_bars_db(s, HIST)}
    return sorted(k for k in set(a) & set(c) if a[k][1:] != c[k][1:])


def crossings(bars):
    """how many times the closes of bars 1-6 switch side of the opening print (raw fact; the system's AUCTION definition is >=2 crossings)."""
    o = bars[0][1]; last = 0; n = 0
    for b in bars[:6]:
        sg = 1 if b[4] > o else (-1 if b[4] < o else 0)
        if sg:
            n += bool(last and sg != last); last = sg
    return n


def key_metrics(bars, prev):
    o = bars[0][1]
    return dict(ref=ref_opening(bars, prev)[0], open=o, net_30m=bars[5][4] - o, ib_high=max(b[2] for b in bars[:12]), ib_low=min(b[3] for b in bars[:12]),
                rth_close=bars[-1][4], rth_high=max(b[2] for b in bars), rth_low=min(b[3] for b in bars))


def load_system_rows():
    lo = (dt.date.fromisoformat(START) - dt.timedelta(days=10)).isoformat()
    rows = q("select date, opening_type, day_type, status, coalesce(confidence::text,''), coalesce(ib_high::text,''), coalesce(ib_low::text,''), "
             "coalesce(to_char(locked_at at time zone 'Asia/Jerusalem','YYYY-MM-DD HH24:MI'),''), "
             "coalesce(to_char(created_at at time zone 'Asia/Jerusalem','YYYY-MM-DD HH24:MI'),''), "
             "coalesce(to_char(last_updated_at at time zone 'Asia/Jerusalem','YYYY-MM-DD HH24:MI'),'') "
             f"from v9_day_type_history where date between '{lo}' and '{END}' order by date", LIVE)
    out = collections.OrderedDict()
    for r in rows:
        f = r.split("|"); d = f[0]
        if d in out: raise RuntimeError(f"duplicate v9_day_type_history rows for {d}")
        out[d] = dict(opening_type=f[1], day_type=f[2], status=f[3], confidence=f[4], ib_high=f[5], ib_low=f[6], locked_at=f[7], created_at=f[8], updated_at=f[9])
    return out


def trading_dates():
    d = dt.date.fromisoformat(START); e = dt.date.fromisoformat(END)
    while d <= e:
        if d.weekday() < 5: yield d.isoformat()
        d += dt.timedelta(days=1)


def r2(x): return None if x is None else round(float(x), 2)


COLS = ["date", "weekday", "sys_opening_type", "sys_status", "sys_day_type", "sys_confidence", "sys_ib_high", "sys_ib_low", "sys_locked_at_il", "sys_row_created_il",
        "sys_row_updated_il", "ref_opening_type", "ref_note", "ref_direction", "match", "open", "prev_date", "prev_high", "prev_low", "prev_vah", "prev_val", "prev_poc",
        "prev_close", "prev_bars_n", "gap_open_vs_prev_close", "open_location", "high_30m", "low_30m", "net_30m", "retrade_open", "retrade_bar", "ib_high_bars",
        "ib_low_bars", "d_ib_high", "d_ib_low", "ib_same_as_prev_row", "rth_close", "rth_high", "rth_low", "close_minus_open", "day_range", "dir_30m",
        "closed_with_dir_30m", "closed_in_ref_dir", "bars_db", "bars_n", "bars_n_live", "bars_n_hist", "bars_first_et", "bars_last_et", "xdb_common_bars",
        "xdb_max_abs_diff", "xdb_bars_differing", "xdb_fields_differ", "echo_bars_live", "echo_bars_hist", "crossings_open_30m", "max_bar_jump", "dup_bars", "note"]

SYS = load_system_rows(); SYS_KEYS = list(SYS)


def build_row(s):
    d = dt.date.fromisoformat(s); sr = SYS.get(s); row = {c: "" for c in COLS}
    row.update(date=s, weekday=WD_EN[d.weekday()])
    if sr:
        row.update(sys_opening_type=sr["opening_type"], sys_status=sr["status"], sys_day_type=sr["day_type"], sys_confidence=sr["confidence"], sys_ib_high=sr["ib_high"],
                   sys_ib_low=sr["ib_low"], sys_locked_at_il=sr["locked_at"], sys_row_created_il=sr["created_at"], sys_row_updated_il=sr["updated_at"])
    db = pick_db(s); bars = rth_bars(s) if db else []
    cov = coverage(s, db) if db else (0, "", "")
    xc, xmax, xnd = xdb_diff(s)
    row.update(bars_db=db or "", bars_n=len(bars), bars_n_live=coverage(s, LIVE)[0], bars_n_hist=coverage(s, HIST)[0], bars_first_et=cov[1][:5], bars_last_et=cov[2][:5],
               xdb_common_bars=xc, xdb_max_abs_diff="" if xmax is None else xmax, xdb_bars_differing=xnd if xc else "")
    row.update(max_bar_jump=r2(bar_jumps(bars)) if bars else "", dup_bars=(len(bars) - len({b[1:] for b in bars})) if bars else "")   # repeated (O,H,L,C,V) = echoed bar
    row.update(echo_bars_live=len(echo_times(rth_bars_db(s, LIVE))), echo_bars_hist=len(echo_times(rth_bars_db(s, HIST))))
    have_open = len(bars) >= 6 and cov[1] == "09:30:00"
    row["_have_open"] = have_open
    if not have_open:
        row["match"] = "NA"
        row["note"] = NO_DATA + (f" (ב-mems26 רק {len(bars)} ברים חלקיים מ-{cov[1][:5]} ET — בלי פתיחה/IB)" if bars else "")
        return row
    prev = prev_session_profile(s); pbars = rth_bars(prev["date"]) if prev else []
    rt, rn = ref_opening(bars, prev)
    o = bars[0][1]; hi30 = max(b[2] for b in bars[:6]); lo30 = min(b[3] for b in bars[:6]); net30 = bars[5][4] - o
    rtb = retrade_bar(bars)
    ibh = max(b[2] for b in bars[:12]) if len(bars) >= 12 else None; ibl = min(b[3] for b in bars[:12]) if len(bars) >= 12 else None
    rth_hi = max(b[2] for b in bars); rth_lo = min(b[3] for b in bars); rth_close = bars[-1][4]; cod = rth_close - o
    pk = [k for k in SYS_KEYS if k < s]; pib = (SYS[pk[-1]]["ib_high"], SYS[pk[-1]]["ib_low"]) if pk else (None, None)
    st = row["sys_opening_type"]
    rd = ref_direction(bars, rt, rn)
    d30 = "up" if net30 > 0 else ("down" if net30 < 0 else "flat")
    ob = rth_bars_db(s, HIST if db == LIVE else LIVE)      # does the OTHER source change any reported number? (documents the DB choice)
    fd = ",".join(k for k, v in key_metrics(bars, prev).items() if v != key_metrics(ob, prev)[k]) if len(ob) >= 12 and ob[0][0] == bars[0][0] else ""
    row.update(xdb_fields_differ=fd, crossings_open_30m=crossings(bars))
    row.update(ref_opening_type=rt, ref_note=rn, ref_direction=rd, match="NA" if st in ("", "INDETERMINATE") else ("Y" if st == rt else "N"),
               open=r2(o), prev_date=prev["date"] if prev else "", prev_high=r2(prev["high"]) if prev else "", prev_low=r2(prev["low"]) if prev else "",
               prev_vah=r2(prev["vah"]) if prev else "", prev_val=r2(prev["val"]) if prev else "", prev_poc=r2(prev["poc"]) if prev else "",
               prev_close=r2(pbars[-1][4]) if pbars else "", prev_bars_n=len(pbars) if prev else "",
               gap_open_vs_prev_close=r2(o - pbars[-1][4]) if pbars else "", open_location=open_loc(o, prev),
               high_30m=r2(hi30), low_30m=r2(lo30), net_30m=r2(net30), retrade_open="N" if rtb is None else "Y", retrade_bar="" if rtb is None else rtb,
               ib_high_bars=r2(ibh), ib_low_bars=r2(ibl),
               d_ib_high=r2(float(sr["ib_high"]) - ibh) if sr and sr["ib_high"] and ibh is not None else "",
               d_ib_low=r2(float(sr["ib_low"]) - ibl) if sr and sr["ib_low"] and ibl is not None else "",
               ib_same_as_prev_row="" if not sr else ("Y" if (sr["ib_high"], sr["ib_low"]) == pib else "N"),
               rth_close=r2(rth_close), rth_high=r2(rth_hi), rth_low=r2(rth_lo), close_minus_open=r2(cod), day_range=r2(rth_hi - rth_lo), dir_30m=d30,
               closed_with_dir_30m="" if d30 == "flat" else ("Y" if (cod > 0) == (d30 == "up") and cod != 0 else "N"),
               closed_in_ref_dir="" if rd not in ("up", "down") else ("Y" if (cod > 0 and rd == "up") or (cod < 0 and rd == "down") else "N"))
    if len(bars) < 78: row["note"] = f"יום חלקי: {len(bars)} ברים עד {cov[2][:5]} ET"
    return row


rows = [build_row(s) for s in trading_dates()]

if DRY or opt.get("print"):
    for r in rows:
        print(" ".join(str(r[k]) for k in ("date", "weekday", "sys_opening_type", "ref_opening_type", "match", "open", "open_location", "net_30m", "retrade_bar", "d_ib_high", "d_ib_low",
                                         "close_minus_open", "day_range", "gap_open_vs_prev_close", "prev_bars_n", "bars_db", "bars_n", "xdb_common_bars", "xdb_max_abs_diff",
                                         "xdb_fields_differ", "crossings_open_30m", "max_bar_jump", "dup_bars")))


# ───────────────────────────────────── outputs ─────────────────────────────────────
HE_NOTE = {"no re-trade of the open in bars 2-6": "אין חזרה לפתיחה בברים 2–6",
           "probe above a prior reference, drive down": "בדיקה מעל רפרנס קודם ואז דרייב למטה",
           "probe below a prior reference, drive up": "בדיקה מתחת לרפרנס קודם ואז דרייב למעלה",
           "drive then back through the open": "דרייב ואז חזרה דרך הפתיחה",
           "rotation around the open inside the prior range": "סיבוב סביב הפתיחה, בתוך הטווח הקודם",
           "rotation around the open outside the prior range": "סיבוב סביב הפתיחה, מחוץ לטווח הקודם",
           "no prior reference": "אין רפרנס קודם", "fewer than 6 bars": "פחות מ-6 ברים"}
HE_LOC = {"IN_VALUE": "בתוך-ערך", "IN_RANGE": "בתוך-טווח", "ABOVE_RANGE": "מחוץ-לטווח מעל", "BELOW_RANGE": "מחוץ-לטווח מתחת", "NO_PRIOR": "אין יום קודם"}
ARROW = {"up": "↑", "down": "↓", "both": "↕", "": ""}
AUC = ("OPEN_AUCTION_IN", "OPEN_AUCTION_OUT")
HDR = ["תאריך", "יום", "מערכת: opening_type", "נוצרה (IL)*", "מערכת: day_type", "מערכת: IB H/L", "ייחוס: סוג", "ייחוס: הערה", "התאמה", "פתיחה", "יום קודם H/L",
       "יום קודם VAH/VAL/POC", "מיקום הפתיחה", "30 דק׳ H/L", "30 דק׳ נטו", "חזרה לפתיחה (בר 2–6)", "חציות הפתיחה", "IB ברים H/L", "Δ IB מערכת−ברים H/L",
       "סגירה−פתיחה", "טווח היום"]


def f(x, signed=False):
    if x in ("", None): return "—"
    v = round(float(x), 2); s = ("%.2f" % v).rstrip("0").rstrip(".")
    if s in ("-0", ""): s = "0"
    return "+" + s if signed and v > 0 else s


def fs(x): return "\u200e" + f(x, True)      # signed number behind an LRM, so the minus/plus stays left of the digits inside Hebrew (RTL) running text


def hhmm(ts, day): return "—" if not ts else (ts[11:16] if ts[:10] == day else ts[5:16])


def is_roll_day(s):
    """first session after the quarterly expiry (3rd Friday of Mar/Jun/Sep/Dec): the MES series switches contract (unadjusted)."""
    p = dt.date.fromisoformat(s) - dt.timedelta(days=1)
    while p.weekday() >= 5: p -= dt.timedelta(days=1)
    return p.month in (3, 6, 9, 12) and p.weekday() == 4 and 15 <= p.day <= 21


def marks(r):
    m = ""
    if r["bars_db"] == HIST: m += "†"
    if r["_have_open"] and r["prev_bars_n"] != "" and r["prev_bars_n"] < 78: m += "‡"
    if r["_have_open"] and is_roll_day(r["date"]): m += "◊"
    if not r["_have_open"] and r["bars_n"]: m += "§"
    return (" " + m) if m else ""


def md_row(r):
    d = r["date"]; wd = WD_HE[dt.date.fromisoformat(d).weekday()]
    if not r["_have_open"]: return [d + marks(r), wd, NO_DATA] + ["—"] * (len(HDR) - 3)
    note = HE_NOTE.get(r["ref_note"], r["ref_note"])
    if r["ref_opening_type"] == "OPEN_DRIVE": note += f" ({ARROW[r['ref_direction']]})"
    elif r["ref_opening_type"] == "OPEN_REJECTION_REVERSE": note += f" (היפוך {ARROW[r['ref_direction']]})"
    sib = f"{f(r['sys_ib_high'])}/{f(r['sys_ib_low'])}" if r["sys_ib_high"] != "" else "—"
    return [d + marks(r), wd, r["sys_opening_type"] or "—", hhmm(r["sys_row_created_il"], d), r["sys_day_type"] or "—", sib, r["ref_opening_type"], note,
            {"Y": "✓", "N": "✗", "NA": "—"}[r["match"]], f(r["open"]), f"{f(r['prev_high'])}/{f(r['prev_low'])}",
            f"{f(r['prev_vah'])}/{f(r['prev_val'])}/{f(r['prev_poc'])}", HE_LOC[r["open_location"]], f"{f(r['high_30m'])}/{f(r['low_30m'])}", f(r["net_30m"], True),
            "לא" if r["retrade_open"] == "N" else f"כן (בר {r['retrade_bar']})", str(r["crossings_open_30m"]), f"{f(r['ib_high_bars'])}/{f(r['ib_low_bars'])}",
            f"{f(r['d_ib_high'], True)}/{f(r['d_ib_low'], True)}", f(r["close_minus_open"], True), f(r["day_range"])]


def write_csv():
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore"); w.writeheader()
        for r in rows: w.writerow({c: r.get(c, "") for c in COLS})


def dl(rs): return ", ".join(r["date"][5:] for r in rs)
def pc(a, b): return f"{round(100 * a / b)}%" if b else "—"
def dv(rs): return ", ".join(f"{r['date'][5:]} {ARROW.get(r['ref_direction'], '')} ({fs(r['close_minus_open'])})" for r in rs)


def stats():
    have = [r for r in rows if r["_have_open"]]; both = [r for r in have if r["match"] in ("Y", "N")]
    return dict(have=have, both=both, nb=len(both), nm=sum(r["match"] == "Y" for r in both), nd=len(rows),
                sys_cnt=collections.Counter(r["sys_opening_type"] for r in rows if r["sys_opening_type"] not in ("", "INDETERMINATE")),
                ref_cnt=collections.Counter(r["ref_opening_type"] for r in have),
                conf=collections.Counter((r["sys_opening_type"], r["ref_opening_type"]) for r in both),
                no_data=[r for r in rows if not r["_have_open"]], no_sys=[r for r in rows if not r["sys_opening_type"]],
                indet=[r for r in rows if r["sys_opening_type"] == "INDETERMINATE"])


def md_head_and_table(S):
    n_all, n_lock = q("select count(*), count(locked_at) from v9_day_type_history", LIVE)[0].split("|")
    a_all, a_lock = q("select count(*), count(locked_at) from v9_day_type_archive", LIVE)[0].split("|")
    both, nb, nm = S["both"], S["nb"], S["nm"]
    matched = collections.Counter(r["sys_opening_type"] for r in both if r["match"] == "Y")
    sys_auc = [r for r in both if r["sys_opening_type"] in AUC]; ref_auc = [r for r in both if r["ref_opening_type"] in AUC]
    ai = [r for r in both if r["sys_opening_type"] == "OPEN_AUCTION_IN"]; ai_ref = collections.Counter(r["ref_opening_type"] for r in ai)
    L = []; A = L.append
    A("# קריאת סוג-הפתיחה (S1): מה שהמערכת ראתה מול מה שקרה בברים")
    A(f"**חלון:** {START} עד {END} · {S['nd']} ימי מסחר (ב׳–ו׳) · **נוצר:** {TAG} · **סקריפט:** `harness_out/t586/hist/opening_type_30d.py` · **CSV:** `docs/reports/opening_type_30d_{TAG}.csv`")
    A("")
    A("## תקציר")
    A(f"- **התאמה:** {nm} מתוך {nb} הימים שיש בהם גם שורת-מערכת וגם ברים ({pc(nm, nb)}): " + ", ".join(f"{t} ×{n}" for t, n in matched.most_common()) + ".")
    A(f"- **הפער המרכזי:** המערכת סימנה AUCTION (IN/OUT) ב-{len(sys_auc)} מתוך {nb} ימים; קריאת-הייחוס — ב-{len(ref_auc)}. ב-{len(ai)} ימי OPEN_AUCTION_IN של המערכת הברים הראו: "
      + ", ".join(f"{t} ב-{n}" for t, n in ai_ref.most_common()) + ".")
    drv_ai = [r for r in ai if r["ref_opening_type"] == "OPEN_DRIVE"]; dirs = [r for r in both if r["match"] == "N" and r["closed_in_ref_dir"] in ("Y", "N")]
    A(f"- **כיוון הסגירה:** מ-{len(drv_ai)} ימי „AUCTION_IN של המערכת / דרייב בברים“ היום נסגר בכיוון הדרייב ב-{sum(r['closed_in_ref_dir'] == 'Y' for r in drv_ai)}; "
      f"בכל {len(dirs)} ימי אי-ההתאמה שיש להם כיוון ברור — בכיוון הייחוס ב-{sum(r['closed_in_ref_dir'] == 'Y' for r in dirs)} ונגדו ב-{sum(r['closed_in_ref_dir'] == 'N' for r in dirs)} (מדגם קטן — לא מסקנה).")
    A(f"- **חסר:** {len(S['no_data'])} ימים ללא נתונים ({dl(S['no_data'])} — המק ישן). `locked_at` ריק ב-{int(n_all) - int(n_lock)} מתוך {n_all} שורות בטבלה — זמן הנעילה לא נשמר.")
    A("- **הסתייגות:** קריאת-הייחוס היא קריאה מבוססת-כללים של הסוכן-העל (18.10) לדלטון עמ׳ 63–74 על 30 הדקות הראשונות — לא תיוג של מייקל; לכן מצורפות העובדות הגולמיות לשיפוט עצמאי.")
    A("")
    A("## איך לקרוא את הטבלה")
    sts = collections.Counter(r["sys_status"] for r in rows if r["sys_status"])
    sts_txt = f"כל {sum(sts.values())} שורות החלון בסטטוס {next(iter(sts))}" if len(sts) == 1 else ", ".join(f"{k} ×{v}" for k, v in sts.items())
    A(f"- **מערכת** — שורת התאריך ב-`v9_day_type_history` (DB `mems26`): `opening_type`, `day_type` שפורסם, `ib_high/ib_low`. {sts_txt} — כלומר מצב סוף-יום, לא בהכרח הערך ברגע הנעילה הראשוני (יש ביטול/קריאה-מחדש). שורות סוף-שבוע הן ארטיפקט גלגול (נושאות את ה-IB הקודם) והוחרגו.")
    A(f"- **נוצרה (IL)\\*** — `created_at` של השורה בשעון ישראל, כי `locked_at` ריק בכל השורות ({n_lock} מתוך {n_all} מלאים בטבלה; {a_lock} מתוך {a_all} בארכיון).")
    A("- **ייחוס** — `ref_opening` מ-`harness_out/t586/hist/doctrine_audit.py` (דלטון עמ׳ 63–74) על 6 הברים הראשונים (09:30–10:00 ET = 16:30–17:00 ישראל), מול הפרופיל של הסשן הקודם (`prev_session_profile`: TPO של 30 דק׳, 70% סביב ה-POC).")
    A("- **פתיחה** — open של הבר הראשון ב-RTH. **יום קודם** — high/low והערך (VAH/VAL/POC) של הסשן הקודם. **מיקום הפתיחה** — בתוך-ערך (VAL≤פתיחה≤VAH) · בתוך-טווח (מחוץ לערך, בין L ל-H של היום הקודם) · מחוץ-לטווח מעל/מתחת.")
    A("- **30 דק׳** — high/low של הברים 1–6; נטו = סגירת בר 6 − פתיחה (נק׳). **חזרה לפתיחה** — „לא“ = בברים 2–6 כל הסגירות בצד אחד של הפתיחה ואין ויק שחוצה אותה ביותר מ-2 טיקים (בדיוק מבחן ה-DRIVE של הייחוס); „כן (בר N)“ = הבר שבו הדרייב החד-צדדי נשבר לראשונה.")
    A("- **חציות הפתיחה** — כמה פעמים סגירות ברים 1–6 עוברות מצד לצד של הפתיחה (ספירה פשוטה, בלי באפר; לשם השוואה — בתיעוד הגלאי `opening_detector_v2` ההגדרה של AUCTION היא ≥2 חציות של הפתיחה). **IB ברים** — 12 הברים הראשונים (09:30–10:30 ET); **Δ** = ib של המערכת פחות IB הברים.")
    A("- **סגירה−פתיחה** — סגירת בר 15:55 ET פחות הפתיחה; **טווח היום** — high−low של ה-RTH (נק׳). **התאמה** — ✓ סוג-המערכת = סוג-הייחוס · ✗ אחרת · — אין שורת-מערכת/INDETERMINATE/אין ברים.")
    A("")
    A("## הטבלה")
    A("")
    A("| " + " | ".join(HDR) + " |"); A("|" + "---|" * len(HDR))
    for r in rows: A("| " + " | ".join(md_row(r)) + " |")
    A("")
    foot = [f"\\* `locked_at` ריק ב-{int(n_all) - int(n_lock)} מתוך {n_all} שורות. `created_at` ≈17:00 = השורה נוצרה 30 דק׳ אחרי הפתיחה (16:30 ישראל); שעה אחרת לפני 16:30 (למשל ≈07:00) = השורה נוצרה בגלגול/הפעלה לפני הפתיחה — אינה מעידה על שעת הנעילה."]
    FIELD_HE = {"ref": "סוג-הייחוס", "open": "פתיחה", "net_30m": "נטו 30 דק׳", "ib_high": "IB high", "ib_low": "IB low", "rth_close": "סגירת ה-RTH", "rth_high": "high היום", "rth_low": "low היום"}
    rng = lambda a, b: a if a == b else f"{a}–{b}"
    for r in rows:
        if r["bars_db"] != HIST: continue
        s = r["date"]; first = rth_bars_db(s, HIST)[0][0]; parts = []
        if r["bars_n_live"] < r["bars_n_hist"]:
            parts.append(f"ב-`mems26` {r['bars_n_live']} ברים בלבד (עד {coverage(s, LIVE)[2][:5]} ET) מול {r['bars_n_hist']}")
        dls = diff_labels(s)
        if dls:
            last_live = rth_bars_db(s, LIVE)[-1][0]
            parts.append(("בר משותף אחד שונה" if len(dls) == 1 else f"{len(dls)} ברים משותפים שונים") + f" בין המקורות ({rng(il2et(dls[0], first), il2et(dls[-1], first))} ET; הפרש מקסימלי {r['xdb_max_abs_diff']} נק׳)"
                         + (" — זה הבר האחרון ב-`mems26`, כנראה חלקי" if len(dls) == 1 and dls[0] == last_live else ""))
        if r["echo_bars_live"]:
            el = echo_times(rth_bars_db(s, LIVE))
            parts.append(f"ב-`mems26` {len(el)} ברים ({rng(il2et(el[0], first), il2et(el[-1], first))} ET) הם עותק מדויק של הבר שעה אחריהם (הזזת שעה), ואילו ב-`mems26_hist` הרצף תקין")
        fd = [FIELD_HE.get(k, k) for k in r["xdb_fields_differ"].split(",") if k]
        foot.append(f"† {s[5:]}: ברי היום מ-`mems26_hist` — " + "; ".join(parts) + ". מספרי היום שמשתנים בין המקורות: " + (", ".join(fd) if fd else "אין (פתיחה, 30 דק׳, IB, סגירה וטווח זהים)") + ".")
    for r in rows:
        if r["_have_open"] and r["prev_bars_n"] != "" and r["prev_bars_n"] < 78:
            foot.append(f"‡ {r['date'][5:]}: היום הקודם הוא {r['prev_date']} — סשן חלקי של {r['prev_bars_n']} ברים (Labor Day); H/L/VAH/VAL/POC נגזרים ממנו.")
        if r["_have_open"] and is_roll_day(r["date"]):
            same = "סוג-הייחוס ביום זה נקבע במבחן ה-DRIVE, לפני כל השוואה לרפרנסי היום הקודם, ולכן אינו מושפע" if r["ref_opening_type"] == "OPEN_DRIVE" else "סוג-הייחוס ביום זה כן תלוי ברפרנסי היום הקודם ועלול להיות מוטה"
            foot.append(f"◊ {r['date'][5:]}: יום הגלגול (פקיעת Sep ב-{r['prev_date'][5:]}) — נראה שהסדרה `MES` אינה מתואמת-גלגול: פער הפתיחה מול סגירת היום הקודם הוא {fs(r['gap_open_vs_prev_close'])} נק׳ וכולל את בסיס Sep→Dec, "
                        f"כך ש„מיקום הפתיחה“ ו„יום קודם H/L/VAH/VAL/POC“ אינם באותו חוזה. {same}.")
        if not r["_have_open"] and r["bars_n"]:
            foot.append(f"§ {r['date'][5:]}: ב-`mems26` רק {r['bars_n']} ברים חלקיים ({r['bars_first_et']}–{r['bars_last_et']} ET) — בלי הפתיחה וה-IB; לא חושב.")
    for x in foot: A(x); A("")
    return L


def md_summary(S):
    both, nb, nm, conf = S["both"], S["nb"], S["nm"], S["conf"]
    L = []; A = L.append
    A("## סיכום"); A("")
    A("### 1. התפלגות סוגי-הפתיחה"); A("")
    A("| סוג | המערכת (ימים) | קריאת-הייחוס (ימים) |"); A("|---|---:|---:|")
    for t in TYPES: A(f"| {t} | {S['sys_cnt'].get(t, 0)} | {S['ref_cnt'].get(t, 0)} |")
    A(f"| INDETERMINATE (בימי מסחר) | {len(S['indet'])} | — |")
    A(f"| אין נתונים ({dl(S['no_data'])}) | {len(S['no_sys'])} | {len(S['no_data'])} |")
    A(f"| סה״כ ימי מסחר | {S['nd']} | {S['nd']} |"); A("")
    A("### 2. שיעור ההתאמה"); A("")
    A(f"- ימים עם שורת-מערכת (לא INDETERMINATE) **וגם** ברים: {nb}. התאמה מלאה (סוג-מערכת = סוג-ייחוס): **{nm} ({pc(nm, nb)})**; אי-התאמה: {nb - nm}.")
    A("- לפי מה שהמערכת אמרה: " + " · ".join(f"{t}: {sum(1 for r in both if r['sys_opening_type'] == t and r['match'] == 'Y')}/{sum(1 for r in both if r['sys_opening_type'] == t)}"
                                          for t in TYPES if any(r["sys_opening_type"] == t for r in both)) + ".")
    sa = [r for r in both if r["sys_opening_type"] in AUC]; ra = [r for r in both if r["ref_opening_type"] in AUC]; sra = [r for r in sa if r["ref_opening_type"] in AUC]
    A(f"- AUCTION (IN או OUT): המערכת סימנה {len(sa)} מתוך {nb} ימים, הייחוס {len(ra)} מתוך {nb}; ימי AUCTION משותפים: {len(sra)}. כיווני (DRIVE/TEST_DRIVE/ORR): המערכת {nb - len(sa)}, הייחוס {nb - len(ra)}.")
    A("")
    A("### 3. מטריצת בלבול (שורות = מה שהמערכת אמרה, עמודות = קריאת-הייחוס)"); A("")
    A("| מערכת ↓ / ייחוס → | " + " | ".join(TYPES) + " | סה״כ |"); A("|---|" + "---:|" * (len(TYPES) + 1))
    for t in TYPES:
        A(f"| **{t}** | " + " | ".join((f"**{conf[(t, c)]}**" if t == c and conf.get((t, c)) else str(conf.get((t, c), 0))) for c in TYPES) + f" | {sum(conf.get((t, c), 0) for c in TYPES)} |")
    A("| **סה״כ** | " + " | ".join(str(sum(conf.get((t, c), 0) for t in TYPES)) for c in TYPES) + f" | {nb} |"); A("")
    A("### 4. אי-התאמות שיטתיות"); A("")
    ai = [r for r in both if r["sys_opening_type"] == "OPEN_AUCTION_IN"]; ai_c = collections.Counter(r["ref_opening_type"] for r in ai)
    dr = [r for r in both if r["sys_opening_type"] == "OPEN_DRIVE"]; orr_s = [r for r in both if r["sys_opening_type"] == "OPEN_REJECTION_REVERSE"]; ao = [r for r in both if r["sys_opening_type"] == "OPEN_AUCTION_OUT"]
    ok_ = lambda rs: sum(r["match"] == "Y" for r in rs)
    A(f"**בקצרה:** המערכת קוראת OPEN_AUCTION_IN ב-{len(ai)} מתוך {nb} ימים ({pc(len(ai), nb)}); באותם ימים הברים הראו AUCTION ב-{sum(ai_c.get(t, 0) for t in AUC)}, דרייב ב-{ai_c.get('OPEN_DRIVE', 0)} "
      f"והיפוך-דחייה (ORR) ב-{ai_c.get('OPEN_REJECTION_REVERSE', 0)}. כשהמערכת קראה OPEN_DRIVE ({len(dr)} ימים) הייחוס הסכים ב-{ok_(dr)}, ובשאר ראה ORR (הפתיחה נסחרה שוב בברים 2–6). "
      f"OPEN_REJECTION_REVERSE: הסכמה {ok_(orr_s)} מתוך {len(orr_s)}. OPEN_AUCTION_OUT: {ok_(ao)} מתוך {len(ao)}. OPEN_TEST_DRIVE: "
      + ("אף צד לא קרא אותו בחלון." if not S["sys_cnt"].get("OPEN_TEST_DRIVE") and not S["ref_cnt"].get("OPEN_TEST_DRIVE") else f"המערכת {S['sys_cnt'].get('OPEN_TEST_DRIVE', 0)}, הייחוס {S['ref_cnt'].get('OPEN_TEST_DRIVE', 0)}."))
    A("")
    A("בסוגריים: סגירה−פתיחה של אותו יום (נק׳). החץ = כיוון קריאת-הייחוס (דרייב, או צד ההיפוך ב-ORR).")
    A("")
    for st in TYPES:
        D = [r for r in both if r["sys_opening_type"] == st]
        if not D: continue
        ok = [r for r in D if r["match"] == "Y"]; mis = [r for r in D if r["match"] == "N"]; by = collections.OrderedDict()
        for r in mis: by.setdefault(r["ref_opening_type"], []).append(r)
        s = f"- **המערכת אמרה {st} ב-{len(D)} ימים** ({pc(len(D), nb)} מהימים). הייחוס הסכים ב-{len(ok)}" + (f" ({dl(ok)})" if ok else "")
        if by: s += "; בשאר הברים הראו " + ", ".join(f"{t} ב-{len(v)} ({dl(v)})" for t, v in by.items())
        A(s + ".")
        for t, v in by.items():
            if t not in DRIVE_REFS: continue
            w = [r for r in v if r["closed_in_ref_dir"] == "Y"]; a = [r for r in v if r["closed_in_ref_dir"] == "N"]; u = [r for r in v if r["closed_in_ref_dir"] == ""]; parts = []
            if w: parts.append(f"נסגרו בכיוון הייחוס {len(w)} מתוך {len(v)}: {dv(w)}")
            if a: parts.append(f"נגד הכיוון {len(a)}: {dv(a)}")
            if u: parts.append(f"היפוך דו-צדדי (שני תנאי ה-ORR התקיימו, אין כיוון) {len(u)}: " + ", ".join(f"{r['date'][5:]} ({fs(r['close_minus_open'])})" for r in u))
            A(f"  - ייחוס {t}: " + "; ".join(parts) + ".")
    mis_all = [r for r in both if r["match"] == "N" and r["ref_opening_type"] in DRIVE_REFS]
    A(f"- **במצטבר:** מתוך {len(mis_all)} ימי אי-התאמה שבהם הברים הראו דרייב/היפוך, היום נסגר בכיוון הייחוס ב-{sum(r['closed_in_ref_dir'] == 'Y' for r in mis_all)}, "
      f"נגדו ב-{sum(r['closed_in_ref_dir'] == 'N' for r in mis_all)}, ולא מוגדר ב-{sum(r['closed_in_ref_dir'] == '' for r in mis_all)}.")
    t30 = [r for r in both if r["closed_with_dir_30m"] in ("Y", "N")]; w30 = [r for r in t30 if r["closed_with_dir_30m"] == "Y"]
    sa30 = [r for r in t30 if r["sys_opening_type"] in AUC]; sa30w = [r for r in sa30 if r["closed_with_dir_30m"] == "Y"]
    A(f"- **לקונטקסט (כל הימים):** ב-{len(w30)} מתוך {len(t30)} ימים היום נסגר בכיוון תנועת 30 הדקות הראשונות; בימי ה-AUCTION של המערכת — {len(sa30w)} מתוך {len(sa30)}.")
    clear = [r for r in both if r["sys_opening_type"] in AUC and r["ref_opening_type"] == "OPEN_DRIVE" and abs(float(r["net_30m"])) >= 15]
    if clear:
        A("- **המקרים שהעובדות הכי פחות משאירות מקום לפרשנות** (המערכת: AUCTION; בברים: הפתיחה לא נסחרה שוב בברים 2–6 ותנועה נטו ≥15 נק׳ ב-30 דק׳ — הסף הוא שלי, להמחשה בלבד): "
          + "; ".join(f"{r['date'][5:]} נטו {fs(r['net_30m'])}, סגירה−פתיחה {fs(r['close_minus_open'])}" for r in clear) + ".")
    contra = [r for r in both if r["sys_opening_type"] == "OPEN_DRIVE" and r["retrade_open"] == "Y"]
    if contra:
        A("- **הכרזות OPEN_DRIVE של המערכת שהעובדות סותרות** (הפתיחה נסחרה שוב בברים 2–6): " + "; ".join(f"{r['date'][5:]} בר {r['retrade_bar']}, נטו 30 דק׳ {fs(r['net_30m'])}" for r in contra) + ".")
    auc_days = [r for r in both if r["sys_opening_type"] in AUC and r["open_location"] != "NO_PRIOR"]
    inc = [r for r in auc_days if (r["sys_opening_type"] == "OPEN_AUCTION_IN") == (r["open_location"] in ("ABOVE_RANGE", "BELOW_RANGE"))]
    if auc_days:
        txt = (f"- **IN/OUT מול מיקום הפתיחה (בלי קשר לקריאת-הייחוס):** מתוך {len(auc_days)} ימי AUCTION של המערכת, ההבחנה IN/OUT עקבית עם מיקום הפתיחה מול טווח ה-RTH של היום הקודם ב-{len(auc_days) - len(inc)}")
        if inc: txt += (f"; לא עקבית ב-{len(inc)}: " + ", ".join(f"{r['date'][5:]} (המערכת {r['sys_opening_type'].replace('OPEN_AUCTION_', '')}, הפתיחה {HE_LOC[r['open_location']]})" for r in inc)
                        + " — אם המערכת מודדת טווח אחר (למשל כולל הלילה) ייתכן שאין סתירה")
        A(txt + ".")
    A("")
    A("### 5. ימים שבהם המערכת הייתה INDETERMINATE או חסרה"); A("")
    n_locked = sum(S["sys_cnt"].values())
    A(f"- INDETERMINATE בימי מסחר: " + (dl(S["indet"]) if S["indet"] else f"**אין** — כל {n_locked} הימים שיש להם שורה נעלו סוג."))
    maxh = q("select max(ts at time zone 'America/New_York') from v9_bars_5min_woodies where symbol='MES'", HIST)[0]
    A(f"- חסרים ({len(S['no_sys'])}): {dl(S['no_sys'])} — אין שורה ב-`v9_day_type_history`, ואין ברי RTH מלאים באף DB (המק ישן; ב-`mems26_hist` הברים נגמרים ב-{maxh[:16]} ET, לפני פתיחת ה-RTH של 12.10). "
      + " ".join(f"ב-{r['date'][5:]} קיימים ב-`mems26` רק {r['bars_n']} ברים חלקיים ({r['bars_first_et']}–{r['bars_last_et']} ET) — בלי פתיחה." for r in S["no_data"] if r["bars_n"]))
    wk = [d for d in SYS if START <= d <= END and dt.date.fromisoformat(d).weekday() >= 5]
    if wk: A(f"- שורות סוף-שבוע שהוחרגו (ארטיפקט גלגול, נושאות את ה-IB הקודם): " + ", ".join(f"{d[5:]} ({WD_HE[dt.date.fromisoformat(d).weekday()]}, {SYS[d]['opening_type']})" for d in wk) + ".")
    A("")
    A("### 6. הסתייגויות"); A("")
    zero_ib = sum(1 for r in both if r["d_ib_high"] == 0 and r["d_ib_low"] == 0)
    orr = S["ref_cnt"].get("OPEN_REJECTION_REVERSE", 0)
    A(f"- **שיטת הייחוס והשבוע החסר, במשפט אחד:** קריאת-הייחוס היא קריאה מבוססת-כללים של הסוכן-העל (18.10) לדלטון עמ׳ 63–74 על 30 הדקות הראשונות — לא תיוג של מייקל — ו-{dl(S['no_data'])} חסרים כי המק ישן והמערכת לא רצה.")
    A(f"- **הכלל של ORR בייחוס רחב:** `ref_opening` קורא ORR כשיש תנועה של ≥4 נק׳ בברים 1–3 וחזרה דרך הפתיחה בברים 4–6, ו-AUCTION נשאר שארית בלבד — ולכן סימן AUCTION ב-{len(ra)} מתוך {nb} ימים ו-ORR ב-{orr}. חלק מהפער הוא פער בהגדרות ולא בהכרח טעות של המערכת.")
    A("- **חלונות שונים:** לפי `backend/v9/systems/day_type/opening_lock.py` (T-314) סוגים שאינם AUCTION ננעלים אחרי 3 ברים סגורים (≈15 דק׳), AUCTION נשאר פתוח עד נעילת ה-IB (≈60 דק׳), ויש ביטול (negation) כשסגירה חורגת מהקצה שנדחה; הייחוס קורא 30 דק׳ שלמות. "
      "לא נבדק כאן איזה מסלול כתב את שורת ה-DB, ולא אם הדגל `OPENING_LOCK_PRIOR_REFS_V1` (T-594: רפרנסי היום-הקודם בנעילה, ברירת מחדל כבוי) היה דלוק בחלון.")
    A(f"- **יישור תאריכים והזנה:** ה-IB של המערכת זהה ל-IB מהברים ב-{zero_ib} מתוך {nb} הימים (Δ = 0/0) — תאריך השורה הוא תאריך הסשן, והברים הם אותה הזנה.")
    A(f"- **מדגם:** {nb} ימים בלבד; אין כאן מובהקות סטטיסטית, רק תמונת מצב.")
    dups = sum(int(r["dup_bars"]) for r in S["have"])
    A("- **מקור הברים:** ברירת-מחדל `mems26`; `mems26_hist` רק כשהוא מכיל יותר ברים לאותו יום, או — בשוויון — כשהסדרה שלו רציפה יותר (ראו † מעל). בדיקות שלמות על הסדרה שנבחרה: "
      + ("אין ברים כפולים" if dups == 0 else f"{dups} ברים כפולים") + f"; הקפיצה המקסימלית בין סגירת בר לפתיחת הבר הבא היא {max(float(r['max_bar_jump']) for r in S['have'])} נק׳ (בכל {len(S['have'])} הימים).")
    A("")
    return L


S = stats()
if not DRY:
    write_csv()
    with open(OUT_MD, "w", encoding="utf-8") as fh: fh.write("\n".join(md_head_and_table(S) + md_summary(S)) + "\n")
    print(f"wrote {OUT_CSV} ({len(rows)} rows) and {OUT_MD}")
    print("agreement", S["nm"], "/", S["nb"], "conf", dict(S["conf"]))
