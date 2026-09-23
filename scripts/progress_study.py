#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""progress_study.py — "האם יש שיפור מיום ליום?" (מייקל 23.09 11:42).

One number per branch per trading day, so the question "is it getting better?" has an
answer instead of an impression. Sources, all measured, nothing synthesized:

  review.json  (scripts/day_review.py)  — the day's real legs, which were taken/late/missed
  v9_trades    (Postgres)               — live + shadow outcomes, broker-first for live
  git log                               — what was actually built that day (commits + T-items)

Writes render_mobile_relay/static/docs/data/progress.json, rendered by gen_phone_pages.py
into progress.html. Read-only: no DB writes, no flags, no restarts.

  python3 scripts/progress_study.py [--since 2026-09-08]

Honesty rules (CLAUDE.md §Source-of-Truth Rule 1): a day with no broker number reports
books and says so — it never borrows the other source's label. N is printed next to every
rate; a rate over N<5 is a hint, not a verdict.
"""
import os, sys, json, re, argparse, subprocess, collections, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all

PT = 5.0  # MES $ per point per contract (backend/v9/services/active_trade_manager/monitor.py:22)

ap = argparse.ArgumentParser()
ap.add_argument("--since", default="2026-09-08")
ap.add_argument("--out", default=os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data", "progress.json"))
args = ap.parse_args()

RV = json.load(open(os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data", "review.json"), encoding="utf-8"))

# ── live + shadow, per day, broker-first for live ─────────────────────────────
live = {r["d"].isoformat(): r for r in read_all("""
  select (entry_ts at time zone 'Asia/Jerusalem')::date d, count(*) n,
    count(*) filter (where coalesce(pnl_sierra, pnl_usd, 0) > 0) w,
    count(*) filter (where pnl_sierra is not null) n_brok,
    round(sum(coalesce(pnl_usd,0))::numeric, 2) books,
    round(sum(pnl_sierra)::numeric, 2) brok,
    round(sum(greatest(coalesce(pnl_sierra, pnl_usd, 0), 0))::numeric, 2) won_usd,
    round(sum(least(coalesce(pnl_sierra, pnl_usd, 0), 0))::numeric, 2) lost_usd
  from v9_trades where mode='live' and entry_ts >= :s group by 1 order by 1""", {"s": args.since})}

shad = {r["d"].isoformat(): r for r in read_all("""
  select (entry_ts at time zone 'Asia/Jerusalem')::date d, count(*) n,
    count(*) filter (where coalesce(pnl_r,0) > 0) w, round(avg(coalesce(pnl_r,0))::numeric, 3) avg_r
  from v9_trades where mode='shadow' and state='CLOSED' and entry_ts >= :s group by 1 order by 1""",
  {"s": args.since})}

# ── what was built that day (git) ─────────────────────────────────────────────
log = subprocess.run(["git", "-C", ROOT, "log", f"--since={args.since}", "--date=short",
                      "--pretty=%ad\x1f%s"], capture_output=True, text=True).stdout
built = collections.defaultdict(lambda: {"commits": 0, "t": []})
for line in log.splitlines():
    if "\x1f" not in line: continue
    d, subj = line.split("\x1f", 1)
    built[d]["commits"] += 1
    for t in re.findall(r"\bT-\d{2,4}[a-z]?\b", subj):
        if t not in built[d]["t"]: built[d]["t"].append(t)

# ── per-day row ───────────────────────────────────────────────────────────────
days = []
for d in sorted(RV["days"]):
    R = RV["days"][d]
    v = collections.Counter(l["verdict"] for l in R["legs"])
    catch = R["n_legs"] - v["UNCATCHABLE"]
    lv, sh = live.get(d), shad.get(d)
    brok = float(lv["brok"]) if lv and lv["brok"] is not None else None
    books = float(lv["books"]) if lv else None
    # points actually banked, broker-first; None when the broker never recorded the day
    banked = (brok / PT) if brok is not None else None
    cand = [c for c in R.get("candidates", []) if c.get("kind") == "relax_gate"]
    days.append({
        "day": d, "day_type": R["day_type"], "opening": R["opening"], "range": R["range"],
        "legs": R["n_legs"], "catchable": catch, "took": v["TOOK"], "late": v["LATE"],
        "opposite": v["OPPOSITE"], "missed": v["MISSED"], "uncatchable": v["UNCATCHABLE"],
        "missed_pts": R["missed_pts"], "available_pts": R["available_pts"],
        "live_n": (lv["n"] if lv else 0), "live_w": (lv["w"] if lv else 0),
        "live_brok": brok, "live_books": books,
        "brok_n": (lv["n_brok"] if lv else 0),
        "banked_pts": (round(banked, 2) if banked is not None else None),
        # exits branch: when we were right, how many points did we actually take?
        "won_pts": (round(float(lv["won_usd"]) / PT, 2) if lv else None),
        "lost_pts": (round(float(lv["lost_usd"]) / PT, 2) if lv else None),
        "avg_win_pts": (round(float(lv["won_usd"]) / PT / lv["w"], 2) if lv and lv["w"] else None),
        "shadow_n": (sh["n"] if sh else 0), "shadow_w": (sh["w"] if sh else 0),
        "shadow_avg_r": (float(sh["avg_r"]) if sh and sh["avg_r"] is not None else None),
        "decisions": R["decisions"], "blocked": R["blocked"], "fired": R.get("fired", 0),
        "shadow_only": R.get("shadow_only", 0),
        "gate_cost_pts": round(sum(c.get("pts", 0) for c in cand), 1), "gate_cost_n": len(cand),
        "commits": built.get(d, {}).get("commits", 0), "t_items": built.get(d, {}).get("t", []),
    })

# ── halves: first vs last, the only "is it improving" comparison we can defend ─
def agg(rows):
    catch = sum(r["catchable"] for r in rows); took = sum(r["took"] for r in rows)
    late = sum(r["late"] for r in rows); ln = sum(r["live_n"] for r in rows)
    lw = sum(r["live_w"] for r in rows)
    bk = [r["banked_pts"] for r in rows if r["banked_pts"] is not None]
    av = sum(r["available_pts"] for r in rows if r["banked_pts"] is not None)
    rs = [r["shadow_avg_r"] for r in rows if r["shadow_avg_r"] is not None]
    brk = [r["live_brok"] for r in rows if r["live_brok"] is not None]
    wp = sum(r["won_pts"] for r in rows if r["won_pts"] is not None)
    lp = sum(r["lost_pts"] for r in rows if r["lost_pts"] is not None)
    avail_all = sum(r["available_pts"] for r in rows)
    return {
        "won_pts": round(wp, 1), "lost_pts": round(lp, 1),
        "avail_all_pts": round(avail_all, 1),
        "won_of_avail_pct": (round(100.0 * wp / avail_all, 1) if avail_all else None),
        "avg_win_pts": (round(wp / lw, 2) if lw else None),
        "avg_loss_pts": (round(lp / (ln - lw), 2) if (ln - lw) else None),
        "days": [r["day"] for r in rows], "n_days": len(rows),
        "catchable": catch, "took": took, "late": late,
        "in_time_pct": (round(100.0 * took / catch, 1) if catch else None),
        "any_pct": (round(100.0 * (took + late) / catch, 1) if catch else None),
        "live_n": ln, "live_w": lw, "live_win_pct": (round(100.0 * lw / ln, 1) if ln else None),
        "brok_sum": (round(sum(brk), 2) if brk else None), "brok_days": len(brk),
        "banked_pts": (round(sum(bk), 1) if bk else None), "available_pts": round(av, 1),
        "capture_pct": (round(100.0 * sum(bk) / av, 1) if bk and av else None),
        "shadow_avg_r": (round(sum(rs) / len(rs), 3) if rs else None),
        "blocked": sum(r["blocked"] for r in rows), "fired": sum(r["fired"] for r in rows),
        "gate_cost_pts": round(sum(r["gate_cost_pts"] for r in rows), 1),
        "commits": sum(r["commits"] for r in rows),
    }

half = len(days) // 2
halves = {"first": agg(days[:half]), "last": agg(days[half:])}

# ── by day type ───────────────────────────────────────────────────────────────
by_type = {}
for t in sorted({r["day_type"] for r in days}):
    by_type[t] = agg([r for r in days if r["day_type"] == t])

# ── today, so far (Michael asked "what did Claude on the computer do just now") ─
today = dt.date.today().isoformat()
t_log = subprocess.run(["git", "-C", ROOT, "log", f"--since={today} 00:00", "--date=format:%H:%M",
                        "--pretty=%ad\x1f%s"], capture_output=True, text=True).stdout
now_rows = []
for line in t_log.splitlines():
    if "\x1f" in line:
        hh, subj = line.split("\x1f", 1)
        now_rows.append({"t": hh, "s": subj[:150]})

out = {"days": days, "halves": halves, "by_type": by_type, "since": args.since,
       "today": {"day": today, "commits": now_rows},
       "generated": dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M%z")}
os.makedirs(os.path.dirname(args.out), exist_ok=True)
with open(args.out, "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)

print(f"progress.json: {len(days)} sessions {days[0]['day']}..{days[-1]['day']} → {args.out}")
for k, h in halves.items():
    print(f"  {k:5s} n={h['n_days']} in_time={h['in_time_pct']}% any={h['any_pct']}% "
          f"live={h['live_w']}/{h['live_n']} ({h['live_win_pct']}%) broker={h['brok_sum']} "
          f"won={h['won_pts']}pts/{h['avail_all_pts']} ({h['won_of_avail_pct']}%) "
          f"avgwin={h['avg_win_pts']} avgloss={h['avg_loss_pts']} shadowR={h['shadow_avg_r']}")
for t, h in by_type.items():
    print(f"  {t:16s} days={h['n_days']} in_time={h['in_time_pct']}% live={h['live_w']}/{h['live_n']} "
          f"broker={h['brok_sum']} capture={h['capture_pct']}%")
