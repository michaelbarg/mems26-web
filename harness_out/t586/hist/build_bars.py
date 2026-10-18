#!/usr/bin/env python3
"""T-586 · full-history replay, step 1 — Sierra .scid (tick records) → 5-min bars (UTC), chunked (RAM-light).
usage: build_bars.py <file.scid> <out.csv>     columns: ts (unix s, bar OPEN time, UTC), o,h,l,c,v,bv,av,nt
Price scale ×100 is detected (newer files store 7742.50 as 774250.0). Read-only on the .scid."""
import sys, os, datetime, numpy as np, pandas as pd
DT = np.dtype([("dt", "<i8"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"),
               ("nt", "<u4"), ("tv", "<u4"), ("bv", "<u4"), ("av", "<u4")])
EPOCH_US = int((datetime.datetime(1899, 12, 30) - datetime.datetime(1970, 1, 1)).total_seconds() * 1_000_000)
CHUNK = 4_000_000
src, out = sys.argv[1], sys.argv[2]
n_total = (os.path.getsize(src) - 56) // 40
scale = None; parts = []
with open(src, "rb") as f:
    f.seek(56)
    done = 0
    while done < n_total:
        a = np.fromfile(f, dtype=DT, count=min(CHUNK, n_total - done)); done += len(a)
        if not len(a):
            break
        # bar high/low = max/min of TRADE prices (c): the record's h/l fields carry bid/ask quotes one tick beyond the
        # trades and would make 30% of the highs/lows differ from Sierra's chart bars (validated 20.08 vs the live DB:
        # max(c)/min(c) exact 100%, max(h)/min(l) exact 78%/63%).
        c = a["c"].astype(np.float64); h = c.copy(); l = c.copy()
        if scale is None:
            med = np.median(c[c > 0][:200000]) if np.any(c > 0) else 0
            scale = 100.0 if med > 50000 else 1.0
        c /= scale; h /= scale; l /= scale
        ok = (c > 0) & (c < 100000) & (h > 0) & (l > 0) & (h >= l) & (h < 100000)
        us = a["dt"][ok] + EPOCH_US
        b = us // 300_000_000
        df = pd.DataFrame({"b": b, "h": h[ok], "l": l[ok], "c": c[ok], "v": a["tv"][ok].astype(np.int64),
                           "bv": a["bv"][ok].astype(np.int64), "av": a["av"][ok].astype(np.int64), "nt": a["nt"][ok].astype(np.int64)})
        g = df.groupby("b", sort=True)
        p = pd.DataFrame({"o": g["c"].first(), "h": g["h"].max(), "l": g["l"].min(), "c": g["c"].last(),
                          "v": g["v"].sum(), "bv": g["bv"].sum(), "av": g["av"].sum(), "nt": g["nt"].sum()})
        parts.append(p)
        print(f"  {os.path.basename(src)}: {done:,}/{n_total:,} records · {len(p)} bins (scale {scale})", flush=True)
allp = pd.concat(parts)
g = allp.groupby(level=0, sort=True)   # a bin split across chunks: open = first part's open, close = last part's close
bars = pd.DataFrame({"o": g["o"].first(), "h": g["h"].max(), "l": g["l"].min(), "c": g["c"].last(),
                     "v": g["v"].sum(), "bv": g["bv"].sum(), "av": g["av"].sum(), "nt": g["nt"].sum()})
bars.index = (bars.index * 300).astype(np.int64); bars.index.name = "ts"
bars.to_csv(out, float_format="%.2f")
print(f"{os.path.basename(src)} → {out}: {len(bars):,} bars · {datetime.datetime.utcfromtimestamp(bars.index[0])} → "
      f"{datetime.datetime.utcfromtimestamp(bars.index[-1])} UTC")
