#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""review_lib.py — shared hindsight primitives for the day-review tools
(scripts/missed_trades_study.py · scripts/day_review.py). Causal features only: everything
computed at bar i uses bars[:i+1]. Bars are dict rows {ts, d, t, o, h, l, c, v, delta}.
"""
import statistics
import oracle_engine as oe

ZONE_HEB = {"ABOVE_VA": "מעל הבטן", "BELOW_VA": "מתחת לבטן", "IN_VA": "בתוך הבטן", "AT_POC": "על ה-POC", "UNKNOWN": "?"}
FLAGS = ['with_day', 'with_ext', 'at_extreme', 'near_ib_edge', 'near_prev_edge', 'trigger_ok', 'structure_break', 'pullback_before']


def zigzag(bs, thr):
    """Pivots [(i, price, 'H'|'L'), …] of a threshold zigzag on highs/lows."""
    piv = []; mode = None; ext_i = 0; ext_p = bs[0]['c']
    for i, b in enumerate(bs):
        if mode is None:
            if b['h'] - ext_p >= thr: mode = 'up'; ext_i, ext_p = i, b['h']; piv.append((0, bs[0]['l'], 'L'))
            elif ext_p - b['l'] >= thr: mode = 'down'; ext_i, ext_p = i, b['l']; piv.append((0, bs[0]['h'], 'H'))
            continue
        if mode == 'up':
            if b['h'] > ext_p: ext_i, ext_p = i, b['h']
            elif ext_p - b['l'] >= thr: piv.append((ext_i, ext_p, 'H')); mode = 'down'; ext_i, ext_p = i, b['l']
        else:
            if b['l'] < ext_p: ext_i, ext_p = i, b['l']
            elif b['h'] - ext_p >= thr: piv.append((ext_i, ext_p, 'L')); mode = 'up'; ext_i, ext_p = i, b['h']
    piv.append((ext_i, ext_p, 'H' if mode == 'up' else 'L'))
    return piv


def legs_of(bs, atr0, min_pts=None, top=5):
    """Zigzag legs worth catching: ≥ max(12, 1.5×ATR) pts, ≥3 bars, not the first 2 bars."""
    piv = zigzag(bs, max(4.0, 1.0 * atr0))
    legs = []
    for (i0, p0, k0), (i1, p1, k1) in zip(piv, piv[1:]):
        if i1 > i0: legs.append(dict(i0=i0, i1=i1, pts=abs(p1 - p0), short=(p1 < p0), p0=p0, p1=p1))
    thr = min_pts if min_pts is not None else max(12.0, 1.5 * atr0)
    legs = [l for l in legs if l['pts'] >= thr and l['i0'] >= 2 and (l['i1'] - l['i0']) >= 3]
    legs = sorted(legs, key=lambda l: -l['pts'])[:top]; legs.sort(key=lambda l: l['i0'])
    return legs


def features(bs, i, short, prev_va=None):
    atr = oe.compute_atr(bs, i) or 0
    if atr <= 0: return None
    b = bs[i]
    deltas = [abs(float(x['delta'])) for x in bs[:i] if x.get('delta') is not None]
    med_d = statistics.median(deltas) if len(deltas) > 5 else None
    dr = (float(b['delta']) / med_d) if (b.get('delta') is not None and med_d) else None
    dev = oe.compute_developing_va(bs, i - 1) if i >= 4 else {}
    zone = oe.classify_zone_vs_developing_va(b['c'], dev) if dev else 'UNKNOWN'
    pv = prev_va or {}
    near_prev = bool(pv) and (abs(b['c'] - pv.get('val', 1e9)) <= 0.5 * atr or abs(b['c'] - pv.get('vah', 1e9)) <= 0.5 * atr)
    hi_i = max(range(i + 1), key=lambda k: bs[k]['h']); lo_i = min(range(i + 1), key=lambda k: bs[k]['l'])
    bsh, bsl = i - hi_i, i - lo_i; at_extreme = (bsl == 0) if short else (bsh == 0)
    mo = (b['c'] - bs[0]['o']) / atr; with_day = (mo <= -0.5) if short else (mo >= 0.5)
    ib_h = max(x['h'] for x in bs[:12]); ib_l = min(x['l'] for x in bs[:12])
    ext = 'up' if b['c'] > ib_h else 'down' if b['c'] < ib_l else 'none'; with_ext = (ext == 'down' and short) or (ext == 'up' and not short)
    near_ib_edge = abs(b['c'] - ib_l) <= 0.5 * atr or abs(b['c'] - ib_h) <= 0.5 * atr
    rng = b['h'] - b['l']; cp = ((b['c'] - b['l']) / rng) if rng > 0 else 0.5
    trigger_ok = (cp >= 0.7) if not short else (cp <= 0.3); body = abs(b['c'] - b['o']) / rng if rng > 0 else 0
    vols = [float(x['v'] or 0) for x in bs[max(0, i - 5):i]]; vmed = statistics.median(vols) if vols else 0
    vr = (float(b['v']) / vmed) if vmed > 0 else None
    seq = bs[max(0, i - 4):i]; pull = sum(1 for x in seq[-3:] if ((x['c'] < x['o']) if not short else (x['c'] > x['o'])))
    prev5 = bs[max(0, i - 5):i]
    brk = ((b['c'] < min(x['l'] for x in prev5)) if short else (b['c'] > max(x['h'] for x in prev5))) if prev5 else False
    return dict(atr=round(atr, 2), hour=str(b['t'])[:5], ph=('A' if i < 3 else 'B' if i < 12 else 'C' if i < 54 else 'D'), zone=zone,
                near_prev_edge=near_prev, near_ib_edge=near_ib_edge, at_extreme=at_extreme, bars_from_extreme=(bsl if short else bsh),
                with_day=with_day, with_ext=with_ext, ext=ext, move_from_open_atr=round(mo, 2), trigger_ok=trigger_ok, body_ge_50=body >= 0.5,
                range_atr=round(rng / atr, 2), range_ge_08atr=rng >= 0.8 * atr, vol_trig=(vr is not None and vr >= 1.3),
                vol_ratio=round(vr, 2) if vr else None, delta_with=(dr is not None and ((dr <= -1) if short else (dr >= 1))),
                delta_ratio=round(dr, 2) if dr is not None else None, pullback_before=pull >= 2, structure_break=brk,
                ib_h=ib_h, ib_l=ib_l, poc=dev.get('poc') if dev else None, vah=dev.get('vah') if dev else None, val=dev.get('val') if dev else None)


def describe(f, short):
    p = []
    p.append("בר-טריגר חזק (סגירה ב-30% הקיצוניים)" if f["trigger_ok"] else "בר-טריגר חלש")
    p.append(f"טווח {f['range_atr']}×ATR" + (" ✓" if f["range_ge_08atr"] else ""))
    if f["vol_ratio"] is not None: p.append(f"ווליום ×{f['vol_ratio']} מול 5 הברים הקודמים" + (" ✓" if f["vol_trig"] else ""))
    if f["delta_ratio"] is not None: p.append(f"דלתא ×{f['delta_ratio']} מהחציון" + (" עם-הכיוון ✓" if f["delta_with"] else ""))
    p.append("שבירת-מבנה (סגירה מעבר ל-5 הברים הקודמים)" if f["structure_break"] else ("אחרי פולבק" if f["pullback_before"] else "המשך"))
    loc = ZONE_HEB.get(f["zone"], f["zone"])
    if f["near_ib_edge"]: loc += ", ליד קצה-IB"
    if f["near_prev_edge"]: loc += ", ליד ערך-אתמול"
    p.append("מיקום: " + loc + (f", {f['bars_from_extreme']} ברים מהקיצון" if f["bars_from_extreme"] else ", על הקיצון"))
    p.append(("עם" if f["with_day"] else "נגד/בלי") + " כיוון-היום" + (", עם ההרחבה" if f["with_ext"] else ""))
    return " · ".join(p)


def ideal_entry(bs, leg, atr0, prev_va=None):
    """First bar in the leg's first half from which stop ≤1 ATR behind the bar holds until 1.5×ATR.
    Returns dict(i, ep, stop, captured, f) or None (the move gave no confirmable bar)."""
    short = leg['short']
    half = leg['i0'] + max(1, (leg['i1'] - leg['i0']) // 2)
    for i in range(leg['i0'], half + 1):
        atr = oe.compute_atr(bs, i) or atr0
        b = bs[i]; ep = b['c']
        stop = (min(b['h'] + 0.25, ep + 1.0 * atr) if short else max(b['l'] - 0.25, ep - 1.0 * atr))
        target = ep - 1.5 * atr if short else ep + 1.5 * atr
        ok = False
        for x in bs[i + 1:leg['i1'] + 1]:
            hit_s = (x['h'] >= stop) if short else (x['l'] <= stop)
            hit_t = (x['l'] <= target) if short else (x['h'] >= target)
            if hit_s: break
            if hit_t: ok = True; break
        if ok:
            f = features(bs, i, short, prev_va)
            if f:
                captured = (ep - bs[leg['i1']]['l']) if short else (bs[leg['i1']]['h'] - ep)
                return dict(i=i, ep=ep, stop=round(abs(stop - ep), 2), captured=round(captured, 2), atr=round(atr, 2), f=f)
            return None
    return None


def exit_models(bs, i, short, atr, until=None):
    """What each exit style captures from bar i (entry at close of i), first-touch on 5-min bars, to EOD or `until`.
    stop 1×ATR (min 5) · t1 = 1.5×ATR · trail = chandelier 1×ATR from the extreme, armed after +1×ATR ·
    max = best excursion. Points, one contract, no costs."""
    ep = bs[i]['c']; sgn = -1 if short else 1
    stop_d = max(5.0, 1.0 * atr); t1_d = 1.5 * atr
    end = until if until is not None else len(bs) - 1
    fixed = None; trail = None; mfe = 0.0; ext = ep; armed = False; trail_stop = None
    for x in bs[i + 1:end + 1]:
        fav = (ep - x['l']) if short else (x['h'] - ep); adv = (x['h'] - ep) if short else (ep - x['l'])
        mfe = max(mfe, fav)
        if fixed is None:
            if adv >= stop_d: fixed = -stop_d
            elif fav >= t1_d: fixed = t1_d
        if trail is None:
            if not armed:
                if adv >= stop_d: trail = -stop_d
                elif fav >= 1.0 * atr: armed = True; ext = x['l'] if short else x['h']
            if armed:
                ext = min(ext, x['l']) if short else max(ext, x['h'])
                trail_stop = ext + 1.0 * atr if short else ext - 1.0 * atr
                hit = (x['h'] >= trail_stop) if short else (x['l'] <= trail_stop)
                if hit: trail = (ep - trail_stop) if short else (trail_stop - ep)
        if fixed is not None and trail is not None: break
    last = bs[end]['c']; eod = (ep - last) if short else (last - ep)
    return dict(t1=round(fixed if fixed is not None else eod, 2), trail=round(trail if trail is not None else eod, 2), max=round(mfe, 2))
