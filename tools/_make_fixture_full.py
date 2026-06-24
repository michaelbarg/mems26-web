#!/usr/bin/env python3
"""_make_fixture_full.py — generate tools/_fixture_full.json.

╔══════════════════════════════════════════════════════════════════════════╗
║  SYNTHETIC. VERIFICATION ONLY. This file fabricates EVERY field the        ║
║  renderer can draw so we can prove — with no Mac DB — that every pane,      ║
║  overlay and marker renders. It is UNMISTAKABLY synthetic:                  ║
║     "synthetic": true  +  a loud on-screen banner  +  the _fixture_ name.   ║
║  It is SEPARATE from the real 06-09 demo. NEVER treat these numbers as      ║
║  market data. The moment a real Mac export lands, the same renderer         ║
║  produces the real file with the banner OFF.                               ║
╚══════════════════════════════════════════════════════════════════════════╝

Populates, for a fake session date:
  - bars: OHLC + volume + cci + trend_state (BLUE/RED segments) + zlr/hfe flags
  - levels: ALL FIVE (IBH, IBL, POC, VAH, VAL) — so every level line draws
  - cvd: per-bar cumulative_delta — so the CVD-present path is exercised
  - day_type: "Normal" → a FADE day-type, so the playbook zone-tint bands draw
  - trades: 2 (one LONG fade-from-VAL, one SHORT fade-from-VAH)

Run:  python3 tools/_make_fixture_full.py   →   tools/_fixture_full.json
Then: python3 tools/replay_brain_view.py --date FIXTURE \
          --data tools/_fixture_full.json --out tools/_fixture_full.html
"""

import json
import math
import os
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_fixture_full.json")

DATE = "2099-01-01"                 # obviously-fake far-future date
CT = timezone(timedelta(hours=-6))  # fixed offset; values are synthetic anyway


def ct_iso(hh, mm):
    return f"{DATE}T{hh:02d}:{mm:02d}:00"


def epoch_utc(hh, mm):
    dt = datetime(2099, 1, 1, hh, mm, 0, tzinfo=CT)
    return int(dt.astimezone(timezone.utc).timestamp())


def build():
    bars = []
    cvd = []
    # 06:00 (Globex) .. 15:55 CT, every 5 min. Synthetic sine+trend price path.
    base = 5000.0
    cum = 0.0
    t = datetime(2099, 1, 1, 6, 0, 0)
    end = datetime(2099, 1, 1, 16, 0, 0)
    i = 0
    while t < end:
        hh, mm = t.hour, t.minute
        # A wandering price: gentle uptrend with a sine wobble, dips midday.
        drift = 0.6 * i
        wob = 9.0 * math.sin(i / 6.0)
        o = base + drift + wob
        c = base + drift + 9.0 * math.sin((i + 1) / 6.0)
        h = max(o, c) + 2.25
        l = min(o, c) - 2.25
        vol = 800 + int(350 * abs(math.sin(i / 4.0))) + (i % 5) * 30
        # CCI-ish oscillator in [-220,220]
        cci = round(180.0 * math.sin(i / 5.0) - 20.0, 2)
        # trend_state colour from CCI sign (so the CCI line is segment-coloured)
        trend = "BLUE" if cci >= 0 else "RED"
        # ZLR every ~17 bars on an up-cross; HFE every ~23 bars on a down-extreme
        zlr = 1 if (i % 17 == 8) else 0
        hfe = 1 if (i % 23 == 11) else 0
        cum += round(120.0 * math.sin(i / 5.0) + (i % 7 - 3) * 18.0, 1)
        bars.append({
            "ts": ct_iso(hh, mm),
            "epoch": epoch_utc(hh, mm),
            "o": round(o, 2), "h": round(h, 2), "l": round(l, 2), "c": round(c, 2),
            "volume": vol,
            "cci": cci,
            "trend_state": trend,
            "zlr": zlr, "zlr_direction": ("LONG" if zlr else None),
            "hfe": hfe, "hfe_direction": ("SHORT" if hfe else None),
        })
        cvd.append({"ts": ct_iso(hh, mm), "epoch": epoch_utc(hh, mm),
                    "cumulative_delta": round(cum, 1)})
        t += timedelta(minutes=5)
        i += 1

    # ALL FIVE levels, placed inside the synthetic price band so the lines + the
    # fade zones land on-screen. (Normal = a fade day-type in the playbook.)
    px = [b["c"] for b in bars]
    lo, hi = min(px), max(px)
    mid = (lo + hi) / 2.0
    levels = {
        "ibh": round(mid + 0.30 * (hi - mid), 2),
        "ibl": round(mid - 0.30 * (mid - lo), 2),
        "poc": round(mid, 2),
        "vah": round(mid + 0.18 * (hi - mid), 2),
        "val": round(mid - 0.18 * (mid - lo), 2),
        # No ib_label here → drawn as plain IBH/IBL (these are synthetic-from-TPO,
        # not bar-derived; the real demo uses ib_label for its bar-derived IB).
    }

    # Two trades: LONG fade off VAL, SHORT fade off VAH (matches a Normal day).
    trades = [
        {
            "id": 9001, "mode": "shadow", "system": 2, "direction": "LONG",
            "state": "CLOSED",
            "entry_ts": ct_iso(9, 5), "entry_epoch": epoch_utc(9, 5),
            "entry_price": levels["val"],
            "stop": round(levels["val"] - 6, 2),
            "t1": levels["poc"], "t2": levels["vah"], "t3": levels["ibh"],
            "exit_ts": ct_iso(10, 30), "exit_epoch": epoch_utc(10, 30),
            "exit_price": levels["poc"], "exit_reason": "T1",
            "pnl_usd": 187.5, "pnl_r": 1.0, "outcome": "WIN",
            "pattern_id": "VEGAS", "day_type": "Normal",
        },
        {
            "id": 9002, "mode": "shadow", "system": 4, "direction": "SHORT",
            "state": "CLOSED",
            "entry_ts": ct_iso(12, 45), "entry_epoch": epoch_utc(12, 45),
            "entry_price": levels["vah"],
            "stop": round(levels["vah"] + 6, 2),
            "t1": levels["poc"], "t2": levels["val"], "t3": levels["ibl"],
            "exit_ts": ct_iso(13, 40), "exit_epoch": epoch_utc(13, 40),
            "exit_price": round(levels["vah"] + 6, 2), "exit_reason": "STOP",
            "pnl_usd": -150.0, "pnl_r": -1.0, "outcome": "LOSS",
            "pattern_id": "GHOST", "day_type": "Normal",
        },
    ]

    payload = {
        "date": DATE,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "_make_fixture_full.py — SYNTHETIC verification fixture (NOT real data)",
        "synthetic": True,
        "banner": "SYNTHETIC TEST FIXTURE — every field fabricated to verify the "
                  "renderer. NOT real market data. The real Mac export renders the "
                  "same panes with this banner OFF.",
        "day_type": "Normal",          # FADE day-type → zone tints draw
        "levels": levels,              # all 5 present
        "bars": bars,                  # OHLC + volume + cci + trend + zlr/hfe
        "cvd": cvd,                    # per-bar cumulative_delta present
        "trades": trades,
        "_notes": {
            "WARNING": "SYNTHETIC — verification only, separate from the real demo.",
            "purpose": "prove every pane/overlay draws before the real export lands",
        },
    }

    with open(OUT, "w") as fh:
        json.dump(payload, fh, indent=1)
    print(f"Wrote {OUT}")
    print(f"  bars={len(bars)} (with volume+cci+trend+zlr/hfe)  cvd_points={len(cvd)}")
    print(f"  levels: IBH={levels['ibh']} IBL={levels['ibl']} POC={levels['poc']} "
          f"VAH={levels['vah']} VAL={levels['val']}")
    print(f"  day_type=Normal (FADE → zone tints)  trades={len(trades)}")
    n_zlr = sum(b["zlr"] for b in bars)
    n_hfe = sum(b["hfe"] for b in bars)
    print(f"  zlr_flags={n_zlr}  hfe_flags={n_hfe}")


if __name__ == "__main__":
    build()
