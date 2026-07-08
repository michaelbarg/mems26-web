#!/usr/bin/env python3
"""בריפינג-בוקר — מה כל מערכת מחפשת היום + חשבון הסטופים (מייקל 2026-07-08).

שלב 2 בפרוטוקול LIVE_MORNING_PROTOCOL. מדפיס + כותב docs/reports/briefings/BRIEF_<date>.md.
הרצה: python3 scripts/morning_briefing.py
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scripts.flag_guard import parse_env  # noqa: E402
for _k, _v in parse_env(os.path.join(ROOT, ".env")).items():
    os.environ.setdefault(_k, _v)


def api(path, timeout=5):
    try:
        with urllib.request.urlopen(f"http://localhost:8000{path}", timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def main():
    today = date.today().isoformat()
    day = (api("/api/v9/day_type/state") or {}).get("state", {})
    bars = api("/api/v9/chart/bars5min?limit=15") or []
    rows = bars if isinstance(bars, list) else bars.get("bars", [])
    rngs = [float(b.get("high", b.get("h", 0))) - float(b.get("low", b.get("l", 0)))
            for b in rows if b.get("high", b.get("h")) is not None]
    atr = sum(rngs) / len(rngs) if rngs else 0.0
    g = api("/api/v9/gateway/status") or {}
    price = (api("/api/v9/live_price") or {}).get("price", "?")

    fg = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "flag_guard.py")],
                        capture_output=True, text=True)
    fg_line = (fg.stdout.strip().splitlines() or ["?"])[-1]

    def band(lo_mult, hi_mult):
        return f"{max(2.0, lo_mult*atr):.1f}–{hi_mult*atr:.1f} נק'"

    tol = 0.10 * atr
    L = []
    L.append(f"# בריפינג בוקר · {today}")
    L.append("")
    L.append(f"מחיר: **{price}** · ATR-14 (5-דק'): **{atr:.1f} נק'** · "
             f"‏flag-guard: **{'PASS' if fg.returncode == 0 else '🔴 NO-GO'}** ({fg_line})")
    L.append("")
    L.append("## מערכת 1 — סיווג היום (התורה: DALTON_DOCTRINE.md)")
    L.append(f"- מצב: **{day.get('day_type','?')}** · ביטחון {day.get('confidence','?')} · "
             f"‏opening={day.get('opening_type','?')} · IB={day.get('ib_width','?')} · שלב {day.get('stage','?')}")
    L.append("- מה יעביר סיווג: פריצת IB/טווח-אתמול עם קבלה (2 ברים + נפח) — לשני הכיוונים.")
    L.append("")
    L.append("## מערכת 2 — תבניות 5-דק'")
    L.append("- צדה: REACTIVE/INITIATIVE/FLAGS בהתאם ל-Auth Table על סוג-היום הנוכחי.")
    L.append(f"- בר-אישור: סגירה-נגד עד **{tol:.2f} נק'** (10%×ATR) = רעש, לא חסימה.")
    L.append("")
    L.append("## מערכת 4 — Woodies CCI")
    L.append("- צדה: ZLR/TLB/GB100 בהמשך-מגמה · FAMIR/VEGAS/GHOST בהיפוך; עץ A1–A7 → gateway.")
    L.append("")
    L.append("## הסטופים היום (רצועת הנר-הממוצע)")
    L.append(f"- ‏ZLR/TLB/TT: **{band(0.5, 1.0)}** · ‏GB100: **{band(0.5, 1.2)}** · "
             f"היפוכים: **{band(0.5, 1.5)}** (מבנה מנצח בתוך הרצועה; מינימום מוחלט 2 נק')")
    L.append(f"- אחרי T1 → ‏BE+טיק (טרייל-למבנה: משימת STOP-STRUCT) · יעד מעבר ל-IB-H רק ביום נייטרלי/מגמתי-מאושר (פסיקה 07-08).")
    L.append("")
    L.append("## מערכת 6 + מצב")
    L.append(f"- ‏slots: live={g.get('live_slot')} demo={g.get('demo_slot')} · ‏live_enabled={g.get('live_enabled_systems')}")
    eod = os.path.join(ROOT, "docs", "reports", "system6")
    prev = sorted(os.listdir(eod))[-1] if os.path.isdir(eod) and os.listdir(eod) else None
    L.append(f"- דוח S6 אחרון: {prev or '—'} — לקרוא את ההמלצות לפני GO.")
    L.append("")
    L.append("**GO/NO-GO: ‏fire_drill + flag_guard חייבים 🟢 + 6 השערים בפרוטוקול.**")

    outdir = os.path.join(ROOT, "docs", "reports", "briefings")
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"BRIEF_{today}.md")
    open(out, "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
