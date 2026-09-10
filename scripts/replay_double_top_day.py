import os, sys
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/mems26")
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
from backend.v9.db.read import read_all
from backend.v9.systems.five_min.patterns.double_bt import (
    detect_double_top_aa, _swing_highs, _peak_width_bars, PEAK_MAX_WIDTH_BARS, TICK_SIZE, SEARCH_WINDOW)

rows = read_all(
    "SELECT ts, open o, high h, low l, close c, volume v FROM v9_bars_5min_woodies "
    "WHERE ts >= '2026-09-10 13:30:00+00' AND ts < '2026-09-10 20:00:00+00' ORDER BY ts", {})
bars = [{"ts": r["ts"], "o": float(r["o"]), "h": float(r["h"]), "l": float(r["l"]), "c": float(r["c"]), "v": float(r["v"])} for r in rows]
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem")
def il(ts): return ts.astimezone(IL).strftime("%H:%M")
print("flag DOUBLE_TOP_ADAM_FIX_V1 =", os.environ.get("DOUBLE_TOP_ADAM_FIX_V1"), "S2_ATR_RELATIVE =", os.environ.get("S2_ATR_RELATIVE"), "SEARCH_WINDOW =", SEARCH_WINDOW)
atr = 10.0
fired = []
for i in range(12, len(bars)):
    buf = bars[:i+1]
    d, conf, info = detect_double_top_aa(buf, atr_5m=atr)
    window = buf[-min(len(buf), SEARCH_WINDOW):]
    highs = _swing_highs(window)
    # best candidate pair (last two swing highs) for display
    desc = ""
    if len(highs) >= 2:
        (p1i, p1), (p2i, p2) = highs[-2], highs[-1]
        w1 = _peak_width_bars(window, p1i, p1, atr); w2 = _peak_width_bars(window, p2i, p2, atr)
        nl = min(window[j]["l"] for j in range(p1i+1, p2i)) if p2i > p1i+1 else None
        desc = f"P1={p1}@{il(window[p1i]['ts'])} P2={p2}@{il(window[p2i]['ts'])} w=({w1},{w2}) neck={nl} close={buf[-1]['c']}"
    tag = f"FIRE {d} conf={conf:.2f} neck={info.get('neckline_price')}" if d else "-"
    print(f"{il(buf[-1]['ts'])} c={buf[-1]['c']:.2f} | {tag} | {desc}")
