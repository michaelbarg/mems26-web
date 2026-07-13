#!/usr/bin/env python3
"""weekly_report — IDEA-3: the Friday-evening weekly report (Michael 07-13).

One self-contained HTML: equity curve (SVG, no deps), headline stats, R-stats,
drawdown, pattern×day-type breakdown, and week-over-week comparison — from
closed REAL trades (live/demo/sim; never shadow) in local Postgres.

Honest by construction: only recorded fills; R computed only where
quality.initial_stop exists (others counted, marked no-R). No synthesis.

Usage:  python3 scripts/weekly_report.py [--end YYYY-MM-DD]   (end = Friday IL; default today)
Output: docs/reports/WEEKLY_REPORT_<end>.html
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
IL = ZoneInfo("Asia/Jerusalem")
PT_USD = 5.0


def _rows(sql, **p):
    from sqlalchemy import create_engine, text
    e = create_engine(os.getenv("DATABASE_URL", "postgresql://localhost/mems26"))
    with e.connect() as c:
        return [dict(r._mapping) for r in c.execute(text(sql), p)]


def load_week(d0: str, d1: str):
    return _rows("""
        SELECT id, mode, direction, entry_price, exit_price, pnl_usd, outcome,
               exit_reason, entry_ts, exit_ts,
               COALESCE(quality->>'pattern', quality->>'classification', '?') AS pattern,
               COALESCE(day_type_at_entry, '?') AS day_type,
               (quality->>'initial_stop')::float AS initial_stop,
               COALESCE((quality->>'contracts')::int, 2) AS contracts
        FROM v9_trades
        WHERE mode != 'shadow' AND state='CLOSED' AND pnl_usd IS NOT NULL
          AND (entry_ts AT TIME ZONE 'Asia/Jerusalem')::date BETWEEN :a AND :b
        ORDER BY entry_ts""", a=d0, b=d1)


def stats(trades):
    n = len(trades)
    if n == 0:
        return {"n": 0}
    pnls = [float(t["pnl_usd"]) for t in trades]
    wins = [p for p in pnls if p > 0]
    total = sum(pnls)
    # equity + max drawdown
    eq, peak, mdd = 0.0, 0.0, 0.0
    curve = []
    for p in pnls:
        eq += p
        peak = max(peak, eq)
        mdd = max(mdd, peak - eq)
        curve.append(eq)
    # R where honest
    rs = []
    for t in trades:
        if t["initial_stop"] and t["entry_price"]:
            risk_pts = abs(float(t["entry_price"]) - float(t["initial_stop"]))
            if risk_pts > 0:
                per_ct = float(t["pnl_usd"]) / PT_USD / max(1, t["contracts"])
                rs.append(per_ct / risk_pts)
    return {"n": n, "total": total, "wins": len(wins), "win_pct": 100.0 * len(wins) / n,
            "avg": total / n, "best": max(pnls), "worst": min(pnls), "mdd": mdd,
            "avg_r": (sum(rs) / len(rs)) if rs else None, "n_r": len(rs), "curve": curve}


def bucket(trades):
    b = {}
    for t in trades:
        k = (t["pattern"], t["day_type"])
        d = b.setdefault(k, {"n": 0, "pnl": 0.0, "w": 0})
        d["n"] += 1
        d["pnl"] += float(t["pnl_usd"])
        d["w"] += float(t["pnl_usd"]) > 0
    return sorted(b.items(), key=lambda kv: -kv[1]["pnl"])


def svg_curve(curve, w=640, h=180):
    if len(curve) < 2:
        return "<i>(פחות מ-2 עסקאות — אין עקומה)</i>"
    lo, hi = min(min(curve), 0), max(max(curve), 0)
    span = (hi - lo) or 1.0
    pts = []
    for i, v in enumerate(curve):
        x = 8 + i * (w - 16) / (len(curve) - 1)
        y = 8 + (hi - v) * (h - 16) / span
        pts.append(f"{x:.1f},{y:.1f}")
    zero_y = 8 + (hi - 0) * (h - 16) / span
    color = "#3fb950" if curve[-1] >= 0 else "#f85149"
    return (f'<svg width="{w}" height="{h}" style="background:#0d1117;border:1px solid #30363d;border-radius:6px">'
            f'<line x1="0" y1="{zero_y:.1f}" x2="{w}" y2="{zero_y:.1f}" stroke="#30363d" stroke-dasharray="4"/>'
            f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(pts)}"/></svg>')


def fmt_usd(v):
    return f"${v:,.2f}" if v >= 0 else f"-${abs(v):,.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", default=None)
    args = ap.parse_args()
    end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else datetime.now(IL).date()
    start = end - timedelta(days=end.weekday() + 1 if end.weekday() != 6 else 0)  # Sunday IL
    prev_end, prev_start = start - timedelta(days=2), start - timedelta(days=7)

    cur = load_week(start.isoformat(), end.isoformat())
    prv = load_week(prev_start.isoformat(), prev_end.isoformat())
    s, sp = stats(cur), stats(prv)

    rows = ""
    for (pat, dt), d in bucket(cur):
        rows += (f"<tr><td>{pat}</td><td>{dt}</td><td>{d['n']}</td>"
                 f"<td>{d['w']}/{d['n']}</td><td style='color:{'#3fb950' if d['pnl']>=0 else '#f85149'}'>{fmt_usd(d['pnl'])}</td></tr>")

    def line(label, v):
        return f"<tr><td>{label}</td><td>{v}</td></tr>"

    if s["n"]:
        wow = ""
        if sp.get("n"):
            diff = s["total"] - sp["total"]
            wow = f" (שבוע-קודם {fmt_usd(sp['total'])} · שינוי {fmt_usd(diff)})"
        summary = (line("עסקאות", s["n"]) + line("P&L", fmt_usd(s["total"]) + wow)
                   + line("אחוז-מנצחות", f"{s['win_pct']:.0f}% ({s['wins']}/{s['n']})")
                   + line("R ממוצע", f"{s['avg_r']:.2f} (על {s['n_r']} עם סטופ-מתועד)" if s["avg_r"] is not None else "אין נתוני-R")
                   + line("Drawdown מקסימלי", fmt_usd(-s["mdd"]))
                   + line("הטובה/הגרועה", f"{fmt_usd(s['best'])} / {fmt_usd(s['worst'])}"))
        curve_html = svg_curve(s["curve"])
    else:
        summary = line("עסקאות", "0 — שבוע ללא מסחר-אמת")
        curve_html = ""

    html = f"""<!DOCTYPE html><html dir="rtl" lang="he"><head><meta charset="utf-8">
<title>MEMS26 — דוח שבועי {start} → {end}</title>
<style>body{{font-family:-apple-system,sans-serif;background:#010409;color:#c9d1d9;max-width:760px;margin:24px auto;padding:0 16px}}
h1{{font-size:20px;color:#e6edf3}} h2{{font-size:15px;color:#8b949e;margin-top:24px}}
table{{border-collapse:collapse;width:100%;font-size:13px}} td,th{{border:1px solid #30363d;padding:6px 10px;text-align:right}}
th{{background:#161b22}}</style></head><body>
<h1>📊 MEMS26 — דוח שבועי · {start.strftime('%d/%m')}–{end.strftime('%d/%m/%Y')}</h1>
<p style="font-size:12px;color:#8b949e">עסקאות-אמת בלבד (live/demo/sim, ללא צל) · נוצר {datetime.now(IL).strftime('%Y-%m-%d %H:%M')} · לולאת-הלמידה</p>
<h2>עקומת-הון</h2>{curve_html}
<h2>סיכום</h2><table>{summary}</table>
<h2>פילוח תבנית × סוג-יום</h2>
<table><tr><th>תבנית</th><th>סוג-יום</th><th>N</th><th>מנצחות</th><th>P&L</th></tr>{rows or '<tr><td colspan=5>—</td></tr>'}</table>
</body></html>"""

    out = REPO / "docs/reports" / f"WEEKLY_REPORT_{end.isoformat()}.html"
    out.write_text(html, encoding="utf-8")
    print(f"[weekly_report] {s.get('n', 0)} trades {start}→{end} → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
