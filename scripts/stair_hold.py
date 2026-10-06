#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STAIR_HOLD — the DAY_LESSONS walk-forward with ONE change: the exit (Michael 06.10 13:07 IL).

Same 66 sessions, same bars, same candidate definition, same lesson tuples and the same
walk-forward entry selection as /tmp/day_lessons.py (DAY_LESSONS_2026-10-06.md) — the loader,
pivots(), features(), candidates() and the lesson loop are copied verbatim, and the original
exit is re-run as a self-check (must reproduce +7042.50 / +851.25).

Exit under test — "hold the stair":
  LONG (SHORT mirrored): entry = open of the bar after the signal bar; stop = the low that confirmed
  the stair (at entry: the last confirmed swing low below the entry, else the session low so far).
  Hold while every newly confirmed swing low is higher than the previous stair low AND the bar
  closes above the VAH as-of that bar (v9_tpo_history row with created_at <= bar close).
  Exit — whichever comes first, checked in this order on every bar after the fill:
    STOP        the bar trades through the stop (gap -> open)
    STAIR_BREAK the bar CLOSES below the previous stair low
    VALUE       the bar closes at/below the as-of VAH (short: at/above VAL)
    20:00       the 19:55 bar close
  A newly confirmed higher swing low raises the stair: stair_low = stop = that low.
Walk-forward only: day D uses lessons learned on days < D; the lesson learning (best causal
trade under the ORIGINAL exit) is unchanged, so the entries are exactly DAY_LESSONS' entries.
$ = points x 5, 1 contract, no fee, no slippage. Read-only: DB SELECT only; writes one report.

usage: python3 scripts/stair_hold.py            -> docs/reports/STAIR_HOLD_2026-10-06.md + stdout
"""
import os, sys, json, statistics, collections, datetime as dt
import psycopg2
from zoneinfo import ZoneInfo

IL = ZoneInfo("Asia/Jerusalem")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DSN = os.environ.get("STAIR_DSN", "postgresql://localhost/mems26")
K = 3            # fractal half-width (bars each side) for a swing
IB_BARS = 12     # 16:30-17:25 IL
LAST_ENTRY_T = dt.time(19, 50)   # signal bar ts <= 19:50 -> fill at 19:55 open
EXIT_T = dt.time(19, 55)         # close of the 19:55 bar == 20:00
PT = 5.0
REPORT = os.path.join(ROOT, "docs/reports/STAIR_HOLD_2026-10-06.md")

S = [l.strip() for l in open(os.path.join(ROOT, "harness_out/t529/sessions.txt")) if l.strip()]

con = psycopg2.connect(DSN); cur = con.cursor()
cur.execute("""select ts, open, high, low, close, volume from v9_bars_5min_woodies
 where symbol='MES' and ts >= '2026-06-14' and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:59'
 order by ts""")
by_day = collections.defaultdict(list)
for ts, o, h, l, c, v in cur.fetchall():
    t = ts.astimezone(IL)
    by_day[t.date().isoformat()].append(dict(ts=t, o=float(o), h=float(h), l=float(l), c=float(c), v=float(v or 0)))
cur.execute("select created_at, poc, vah, val from v9_tpo_history where created_at >= '2026-06-01' order by created_at")
TPO = [(r[0].astimezone(IL), float(r[1]), float(r[2]), float(r[3])) for r in cur.fetchall()]
con.close()


def va_asof(when):
    """last v9_tpo_history row created_at <= when (availability, not nominal ts)."""
    best = None
    for r in TPO:
        if r[0] <= when: best = r
        else: break
    return best


def harness_pnl(variant, d):
    p = os.path.join(ROOT, "harness_out/t466", f"{variant}_{d}.json")
    if not os.path.exists(p): return None, None
    j = json.load(open(p))
    tr = j.get("trades") or []
    return round(sum(float(t.get("pnl_usd") or 0) for t in tr), 2), len(tr)


def pivots(bars):
    """confirmed fractal pivots: (idx, 'H'|'L', price, confirm_idx)."""
    out = []
    n = len(bars)
    for p in range(K, n - K):
        hs = [bars[q]["h"] for q in range(p - K, p + K + 1)]
        ls = [bars[q]["l"] for q in range(p - K, p + K + 1)]
        if bars[p]["h"] == max(hs) and hs.count(bars[p]["h"]) == 1: out.append((p, "H", bars[p]["h"], p + K))
        if bars[p]["l"] == min(ls) and ls.count(bars[p]["l"]) == 1: out.append((p, "L", bars[p]["l"], p + K))
    return out


def initial_stop(bars, pv, i, side, entry):
    conf = [x for x in pv if x[3] <= i and x[1] == ("L" if side > 0 else "H")]
    for x in reversed(conf):
        if (side > 0 and x[2] < entry) or (side < 0 and x[2] > entry):
            return x[2]
    stop = min(b["l"] for b in bars[:i + 1]) if side > 0 else max(b["h"] for b in bars[:i + 1])
    if (side > 0 and stop >= entry) or (side < 0 and stop <= entry): return None
    return stop


def simulate(bars, pv, i, side):
    """ORIGINAL DAY_LESSONS exit (self-check only): stop, next opposite swing close, or 19:55 close."""
    n = len(bars)
    if i + 1 >= n: return None
    entry = bars[i + 1]["o"]
    stop = initial_stop(bars, pv, i, side, entry)
    if stop is None: return None
    opp = {x[3]: x for x in pv if x[0] > i and x[1] == ("H" if side > 0 else "L")}
    for j in range(i + 1, n):
        b = bars[j]
        if side > 0 and b["l"] <= stop: ex, why = min(b["o"], stop), "STOP"; break
        if side < 0 and b["h"] >= stop: ex, why = max(b["o"], stop), "STOP"; break
        if j in opp: ex, why = b["c"], "SWING"; break
        if b["ts"].time() >= EXIT_T: ex, why = b["c"], "20:00"; break
    else:
        return None
    pts = (ex - entry) * side
    return dict(i=i, side=side, entry=entry, stop=stop, exit=ex, exit_i=j, why=why, pts=round(pts, 2), usd=round(pts * PT, 2),
                risk=round(abs(entry - stop), 2))


def simulate_stair(bars, pv, i, side):
    """THE EXIT UNDER TEST. Same fill and same initial stop as simulate(); then hold the stair."""
    n = len(bars)
    if i + 1 >= n: return None
    entry = bars[i + 1]["o"]
    stop = initial_stop(bars, pv, i, side, entry)
    if stop is None: return None
    stair = stop                      # the low (long) / high (short) that confirmed the current stair
    steps = 0                         # confirmed higher lows (lower highs) after the fill
    same = {x[3]: x for x in pv if x[0] > i and x[1] == ("L" if side > 0 else "H")}   # confirm_idx -> swing on our side
    for j in range(i + 1, n):
        b = bars[j]
        # 1. the stop (intrabar, gap -> open) — checked first
        if side > 0 and b["l"] <= stop: ex, why = min(b["o"], stop), "STOP"; break
        if side < 0 and b["h"] >= stop: ex, why = max(b["o"], stop), "STOP"; break
        # 2. a close that breaks the previous stair low/high
        if side > 0 and b["c"] < stair: ex, why = b["c"], "STAIR_BREAK"; break
        if side < 0 and b["c"] > stair: ex, why = b["c"], "STAIR_BREAK"; break
        # 3. price must stay above the VAH (long) / below the VAL (short) as-of this bar
        r = va_asof(b["ts"] + dt.timedelta(minutes=5))
        if r is not None:
            _, _, vah, val = r
            if side > 0 and b["c"] <= vah: ex, why = b["c"], "VALUE"; break
            if side < 0 and b["c"] >= val: ex, why = b["c"], "VALUE"; break
        # 4. 20:00
        if b["ts"].time() >= EXIT_T: ex, why = b["c"], "20:00"; break
        # a new swing on our side confirmed by this bar: higher low raises the stair (and the stop)
        if j in same:
            p = same[j][2]
            if (side > 0 and p > stair) or (side < 0 and p < stair):
                stair = stop = p; steps += 1
            else:
                ex, why = b["c"], "LOWER_LOW"; break    # the new low is not higher than the previous one
    else:
        return None
    pts = (ex - entry) * side
    return dict(i=i, side=side, entry=entry, stop=stop, exit=ex, exit_i=j, why=why, pts=round(pts, 2), usd=round(pts * PT, 2),
                risk=round(abs(entry - initial_stop(bars, pv, i, side, entry)), 2), steps=steps)


def features(bars, i, ibh, ibl):
    b = bars[i]
    px = b["c"]
    if i < IB_BARS: loc_ib = "IB_FORMING"
    elif px > ibh: loc_ib = "ABOVE_IB"
    elif px < ibl: loc_ib = "BELOW_IB"
    else: loc_ib = "INSIDE_IB"
    r = va_asof(b["ts"] + dt.timedelta(minutes=5))
    if r is None: loc_va = "NO_VA"; vah = val = None
    else:
        _, poc, vah, val = r
        loc_va = "ABOVE_VAH" if px > vah else "BELOW_VAL" if px < val else "IN_VALUE"
    prior = [bars[q]["v"] for q in range(max(0, i - 5), i)]
    med = statistics.median(prior) if prior else 0
    ratio = (b["v"] / med) if med else None
    vol = "VOL_HI" if (ratio is not None and ratio >= 1.0) else "VOL_LO"
    return dict(loc_ib=loc_ib, loc_va=loc_va, vol=vol, vol_ratio=None if ratio is None else round(ratio, 2), vah=vah, val=val)


def candidates(bars):
    for i in range(1, len(bars)):
        if bars[i]["ts"].time() > LAST_ENTRY_T: break
        b, p = bars[i], bars[i - 1]
        if b["c"] > b["o"] and b["c"] > p["h"]: yield i, +1
        if b["c"] < b["o"] and b["c"] < p["l"]: yield i, -1


def ib_of(bars):
    ib = bars[:IB_BARS]
    return max(b["h"] for b in ib), min(b["l"] for b in ib)


def tstr(b): return b["ts"].strftime("%H:%M")


def main():
    lessons = collections.OrderedDict()          # tuple -> first day learned (ORIGINAL exit, as in DAY_LESSONS)
    sum_best_orig = sum_wf_orig = 0.0            # self-check against the locked numbers
    sum_best_stair = sum_took = sum_wf_stair = 0.0
    took_days = n_wf = 0; cum = 0.0
    wins = losses = flat = 0; peak = 0.0; maxdd = 0.0
    reasons = collections.Counter(); reason_usd = collections.Counter(); steps_hist = collections.Counter()
    lines = []
    lines.append("day        | entry (lesson)                               | stair exit                          | WF stair $ | WF orig $ | took $   | cum $")
    for d in S:
        bars = by_day.get(d)
        if not bars or len(bars) < 20:
            lines.append(f"{d} | missing bars"); continue
        pv = pivots(bars); ibh, ibl = ib_of(bars)
        # best causal under the ORIGINAL exit (this is what the lessons are learned from — unchanged)
        best = None; best_stair = None
        for i, side in candidates(bars):
            r = simulate(bars, pv, i, side)
            if r and (best is None or r["usd"] > best["usd"]): best = r
            rs = simulate_stair(bars, pv, i, side)
            if rs and (best_stair is None or rs["usd"] > best_stair["usd"]): best_stair = rs
        took, _ = harness_pnl("t543ref", d)
        key = None
        if best:
            f = features(bars, best["i"], ibh, ibl)
            key = ("LONG" if best["side"] > 0 else "SHORT", f["loc_ib"], f["loc_va"], f["vol"])
        prior = {k for k, v in lessons.items() if v < d}
        wf_o = wf_s = None; wf_key = None
        for i, side in candidates(bars):
            ff = features(bars, i, ibh, ibl)
            kk = ("LONG" if side > 0 else "SHORT", ff["loc_ib"], ff["loc_va"], ff["vol"])
            if kk in prior:
                r = simulate(bars, pv, i, side)
                if r:
                    wf_o = r; wf_key = kk; wf_s = simulate_stair(bars, pv, i, side); break
        if key and key not in lessons: lessons[key] = d
        sum_best_orig += best["usd"] if best else 0.0
        sum_best_stair += best_stair["usd"] if best_stair else 0.0
        if took is not None: sum_took += took; took_days += 1
        if wf_o: sum_wf_orig += wf_o["usd"]
        if wf_s:
            u = wf_s["usd"]; sum_wf_stair += u; n_wf += 1; cum += u
            wins += u > 0; losses += u < 0; flat += u == 0
            peak = max(peak, cum); maxdd = min(maxdd, cum - peak)
            reasons[wf_s["why"]] += 1; reason_usd[wf_s["why"]] += u; steps_hist[wf_s["steps"]] += 1
            sb = bars[wf_s["i"]]; eb = bars[wf_s["exit_i"]]
            lines.append(f"{d} | {('L' if wf_s['side']>0 else 'S')} {tstr(sb)}->{tstr(bars[wf_s['i']+1])} @{wf_s['entry']:.2f} {'/'.join(wf_key)[:28]:<28} | "
                         f"{tstr(eb)} @{wf_s['exit']:.2f} {wf_s['why']:<11} steps={wf_s['steps']} | {u:+9.2f} | {wf_o['usd']:+8.2f} | "
                         f"{('%+8.2f' % took) if took is not None else '   miss '} | {cum:+8.2f}")
        else:
            lines.append(f"{d} | no prior lesson matched ({len(prior)} known)                 | -                                   |      0.00 |     0.00 | "
                         f"{('%+8.2f' % took) if took is not None else '   miss '} | {cum:+8.2f}")
    return dict(lessons=lessons, lines=lines, sum_best_orig=sum_best_orig, sum_wf_orig=sum_wf_orig, sum_best_stair=sum_best_stair,
                sum_took=sum_took, took_days=took_days, sum_wf_stair=sum_wf_stair, n_wf=n_wf, wins=wins, losses=losses, flat=flat,
                maxdd=maxdd, reasons=reasons, reason_usd=reason_usd, steps_hist=steps_hist)


def render(R):
    out = []
    out.append("STAIR_HOLD walk-forward — %d sessions · $ = points x 5 · 1 contract · no fee · read-only" % len(S))
    out.append("self-check (ORIGINAL exit, must equal DAY_LESSONS): best-causal %+.2f · walk-forward %+.2f" % (R["sum_best_orig"], R["sum_wf_orig"]))
    out.append("")
    out.extend(R["lines"])
    out.append("")
    out.append("exit reasons (stair walk-forward): " + " · ".join("%s n=%d $%+.2f" % (k, R["reasons"][k], R["reason_usd"][k]) for k, _ in R["reasons"].most_common()))
    out.append("stairs climbed before exit: " + " · ".join("%d steps: %d trades" % (k, v) for k, v in sorted(R["steps_hist"].items())))
    out.append("walk-forward stair: %d trades · %dW / %dL / %d flat · max drawdown $%+.2f · lessons known at end: %d" % (
        R["n_wf"], R["wins"], R["losses"], R["flat"], R["maxdd"], len(R["lessons"])))
    out.append("best-causal ceiling under the stair exit (hindsight picks the bar; NOT a walk-forward number): $%+.2f" % R["sum_best_stair"])
    out.append("")
    out.append("THE THREE NUMBERS")
    out.append("  stair-hold walk-forward ........ $%+.2f  (%d trades)" % (R["sum_wf_stair"], R["n_wf"]))
    out.append("  the tree took (t543ref) ........ $%+.2f  (%d days)" % (R["sum_took"], R["took_days"]))
    out.append("  old lesson walk-forward ........ $%+.2f  (DAY_LESSONS, same entries, swing exit)" % R["sum_wf_orig"])
    verdict = "PASSES the tree" if R["sum_wf_stair"] > R["sum_took"] else "does not pass the tree (לא עוברת את העץ)"
    out.append("  verdict: stair-hold %s; vs the old lesson: %s" % (verdict, "better" if R["sum_wf_stair"] > R["sum_wf_orig"] else "worse"))
    return "\n".join(out)


if __name__ == "__main__":
    R = main()
    text = render(R)
    print(text)
    hdr = ("# STAIR_HOLD — walk-forward, exit = hold the stair · 2026-10-06\n\n"
           "Michael 06.10 13:07 IL. Same 66 sessions and the same entries as DAY_LESSONS_2026-10-06.md "
           "(first bar closing beyond the prior bar's high/low, fill at the next bar's open, first candidate whose lesson tuple "
           "was learned on an earlier day). Only the exit changed: hold while each newly confirmed swing low is higher than the "
           "previous stair low and the bar closes above the as-of VAH (`v9_tpo_history`, created_at <= bar close); exit on the "
           "first of: stop (= the low that confirmed the stair, raised with every higher low), a close below the previous stair low, "
           "a close at/below the as-of VAH, 20:00. Shorts mirrored (VAL). Walk-forward only: day D uses lessons from days < D; "
           "the lesson learning itself is unchanged (best causal trade under the original exit), so no day's best trade enters the sum.\n\n"
           "**$ = points x 5 · 1 contract · no fee · no slippage.** Read-only (SELECT); no YAML leaf, no .env, no restart.\n\n"
           "```\n$ python3 scripts/stair_hold.py\n" + text + "\n```\n")
    open(REPORT, "w", encoding="utf-8").write(hdr)
    print("report:", os.path.relpath(REPORT, ROOT))
