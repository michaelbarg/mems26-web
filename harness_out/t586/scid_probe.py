#!/usr/bin/env python3
"""T-586 — probe Sierra .scid files: header, record count, first/last timestamps, bid/ask volume presence. Read-only."""
import struct, sys, os, datetime, glob
EPOCH = datetime.datetime(1899, 12, 30)
def rec(b):
    dt, o, h, l, c, nt, tv, bv, av = struct.unpack("<qffffIIII", b)
    return dt, o, h, l, c, nt, tv, bv, av
def ts(dt):
    # SCID v2: int64 microseconds since 1899-12-30 (SCDateTimeMS); older: double days
    return EPOCH + datetime.timedelta(microseconds=dt)
for p in sys.argv[1:]:
    sz = os.path.getsize(p)
    with open(p, "rb") as f:
        hdr = f.read(56)
        magic, hsz, rsz, ver = struct.unpack("<4sIIH", hdr[:14])
        n = (sz - hsz) // rsz
        f.seek(hsz); first = rec(f.read(rsz))
        f.seek(hsz + (n - 1) * rsz); last = rec(f.read(rsz))
        # sample a stretch of 2000 records in the middle for bid/ask presence and granularity
        f.seek(hsz + (n // 2) * rsz); mid = [rec(f.read(rsz)) for _ in range(2000)]
    ba = sum(1 for r in mid if r[7] or r[8]); 
    spans = [ts(mid[i + 1][0]) - ts(mid[i][0]) for i in range(len(mid) - 1)]
    med = sorted(spans)[len(spans) // 2]
    print(f"{os.path.basename(p):26s} magic={magic} hsz={hsz} rsz={rsz} ver={ver} n={n:,} first={ts(first[0])} last={ts(last[0])} "
          f"mid: bid/ask nonzero {ba}/2000 · median gap {med} · sample o/h/l/c {mid[0][1:5]} vol {mid[0][6]}")
