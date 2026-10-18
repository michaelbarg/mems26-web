#!/usr/bin/env python3
"""T-586 · full-history replay, step 2 — merge the per-contract 5-min bars into one MES series (front contract =
the contract with the most volume that ET day) and compute the Woodies study columns with the DLL-reference
formulas (backend/v9/systems/woodies/cci_calc.py), vectorised. Output: <out.csv> with the v9_bars_5min_woodies columns.
usage: merge_studies.py <out.csv> <contract.csv> [<contract.csv> ...]"""
import sys, numpy as np, pandas as pd
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
out = sys.argv[1]; files = sys.argv[2:]
frames = []
for f in files:
    d = pd.read_csv(f); d["contract"] = f.split("/")[-1].replace(".csv", ""); frames.append(d)
allb = pd.concat(frames, ignore_index=True)
t = pd.to_datetime(allb["ts"], unit="s", utc=True).dt.tz_convert(ET)
allb["etday"] = t.dt.date
tm = t.dt.hour * 60 + t.dt.minute
allb["rth"] = ((tm >= 570) & (tm < 960)).astype(int)
vol = allb.groupby(["etday", "contract"]).agg(v=("v", "sum"), rth=("rth", "sum")).reset_index()
# front contract per ET day: a MES contract with a full RTH (>= 70 bars) beats any ES file (same price, different volume
# scale); among equals the larger volume wins. ES fills only the days MES does not cover (2022–24 files).
vol["is_mes"] = vol["contract"].str.upper().str.startswith("MES").astype(int)
vol["full"] = (vol["rth"] >= 70).astype(int)
front = (vol.sort_values(["etday", "full", "is_mes", "v"], ascending=[True, False, False, False])
            .drop_duplicates("etday").set_index("etday")["contract"])
allb["front"] = allb["etday"].map(front)
m = allb[allb["contract"] == allb["front"]].drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
print(f"merged {len(m):,} bars from {len(files)} contracts · {t.min()} → {t.max()} · front switches: "
      + ", ".join(f"{d}:{c}" for d, c in front[front != front.shift()].items()))
h, l, c = m["h"].to_numpy(float), m["l"].to_numpy(float), m["c"].to_numpy(float)
tp = (h + l + c) / 3.0
def cci(period):
    s = pd.Series(tp); sma = s.rolling(period).mean()
    md = s.rolling(period).apply(lambda w: np.mean(np.abs(w - w.mean())), raw=True)
    v = (s - sma) / (0.015 * md)
    v[md < 0.0001] = 0.0
    return v.fillna(0.0).to_numpy()
cci14 = cci(14); cci6 = cci(6)
def ema_dll(period):      # calc_ema: seed = first close of the last period*3 bars, then standard EMA — a fixed FIR window
    k = 2.0 / (period + 1); w = period * 3
    wts = np.array([(1 - k) ** (w - 1)] + [k * (1 - k) ** (w - 1 - i) for i in range(1, w)])
    full = np.convolve(c, wts[::-1], mode="valid")           # value for bars with >= w history
    outv = np.empty_like(c); outv[:w - 1] = np.nan
    outv[w - 1:] = full
    for i in range(min(w - 1, len(c))):                       # short history: same recursion on what exists
        e = c[0]
        for j in range(1, i + 1): e = c[j] * k + e * (1 - k)
        outv[i] = e
    return outv
def ema_inf(series, period):   # the DLL's EMA-34 is a plain EMA on the TYPICAL price (validated 20.08: 97.1% exact vs 3.3% on close)
    k = 2.0 / (period + 1); e = np.empty(len(series)); v = series[0]
    for i in range(len(series)):
        v = series[i] * k + v * (1 - k); e[i] = v
    return e
ema34 = ema_inf(tp, 34)
def lsma_dll(period):     # endpoint of the least-squares line over the last `period` closes
    x = np.arange(period, dtype=float); sx, sx2 = x.sum(), (x * x).sum(); den = period * sx2 - sx * sx
    wb = (period * x - sx) / den; wa = (1.0 / period) - wb * sx / period      # a + b*(period-1) as a FIR
    wts = wa + wb * (period - 1)
    full = np.convolve(c, wts[::-1], mode="valid"); outv = np.empty_like(c); outv[:period - 1] = c[:period - 1]; outv[period - 1:] = full
    return outv
lsma25 = lsma_dll(25)
cci14_prev = np.concatenate([[0.0], cci14[:-1]]); cci14_3 = np.concatenate([[0.0] * 3, cci14[:-3]])
swi = cci14 - cci14_3
tr = np.maximum(h - l, np.maximum(np.abs(h - np.concatenate([[c[0]], c[:-1]])), np.abs(l - np.concatenate([[c[0]], c[:-1]]))))
atr = pd.Series(tr).rolling(14, min_periods=1).mean().to_numpy(); atr = np.where(atr < 0.01, 0.01, atr)
czi = np.round((c - ema34) * 3.9)   # DB czi ≈ 3.9×(close−EMA34), integer; only its sign is consumed (zlr.py)
# trend_state: the DLL's colouring is a hysteresis on CCI-14 — fitted on Sept–Oct 2026 live rows (93.7% agreement, the
# best of 576 enter/exit grids; the Python calc_trend_state gives 45%): BLUE entered at cci >= 50 and held while cci > 0,
# RED entered at cci <= -50 and held while cci < 0, GRAY otherwise.
trend = np.empty(len(c), dtype=object); st = "GRAY"
for i, v in enumerate(cci14):
    if st == "BLUE":
        if v <= 0: st = "RED" if v <= -50 else "GRAY"
    elif st == "RED":
        if v >= 0: st = "BLUE" if v >= 50 else "GRAY"
    else:
        if v >= 50: st = "BLUE"
        elif v <= -50: st = "RED"
    trend[i] = st
pred = cci14 + (cci14 - cci14_prev)
zlr = np.zeros(len(c), bool); zdir = np.array(["NONE"] * len(c), dtype=object)
for i in range(12, len(c)):
    lb = cci14[i - 11:i + 1]; cur, prev = lb[-1], lb[-2]
    if (lb[:-1] > 100).any() and prev > -50 and cur > prev and cur > 0: zlr[i] = True; zdir[i] = "UP"
    elif (lb[:-1] < -100).any() and prev < 50 and cur < prev and cur < 0: zlr[i] = True; zdir[i] = "DOWN"
res = pd.DataFrame({"ts": m["ts"], "open": m["o"], "high": h, "low": l, "close": c, "volume": m["v"], "bid_vol": m["bv"], "ask_vol": m["av"],
                    "cci_14": np.round(cci14, 2), "cci_6_tcci": np.round(cci6, 2), "lsma_value": np.round(lsma25, 2), "swi_value": np.round(swi, 2),
                    "czi_value": np.round(czi, 2), "ema_34": np.round(ema34, 2), "trend_state": trend, "predictor_next_cci": np.round(pred, 2),
                    "zlr_detected": zlr, "zlr_direction": zdir, "lsma_above_price": lsma25 > c, "contract": m["contract"]})
res.to_csv(out, index=False, float_format="%.2f")
print(f"→ {out}: {len(res):,} rows")
