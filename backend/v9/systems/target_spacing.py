"""target_spacing — TARGET_MIN_SPACING_V1: a ladder leg must be a leg.

Michael's ruling 2026-08-21 ~11:30 IL: "לבנות ולהפעיל בשדואו ולבדוק איך זה פותר".

THE EVIDENCE (live #756, 2026-08-20 11:55 ET)
---------------------------------------------
SHORT entry 7696.75, stop 7700.25 (risk 3.5pt), ladder 7691.50 / 7691.00 /
7690.50 — three exits 0.5pt apart. The raw log shows this was NOT "structure
clustered near the session low"; it is one real level plus two invented ones::

    18:55:05 [structural_targets] c3=7697.00 on wrong side of SHORT entry → R-fallback
    18:55:05 [Gateway] #68 structural targets: SHORT Variation → C1=7686.25 C2=7682.75 C3=7679.00
    18:55:05 [TargetClamp] TP-1 applied (SHORT Variation): t1 7689.25 → IB-edge 7691.5;
                            t2 7682.75 → IB-edge 7691.5; t3 7679.0 → IB-edge 7691.5
    18:55:05 [Gateway] ladder-dedup: t2=7691.50 collapsed to t1=7691.50 → nudged to 7691.00
    18:55:05 [Gateway] ladder-dedup: t3=7691.50 collapsed → nudged to 7690.50

Structure produced a healthy ladder (3.50 / 3.75pt steps). TP-1's IB clamp then
collapsed all three onto the SAME price, and the gateway's ladder-dedup
manufactured a "ladder" out of it by nudging 2 ticks at a time. So:

  * ``_target_degeneracy_guard`` (trading_gateway.py:3703) never sees a tie —
    ladder-dedup already un-equalised the legs upstream, and the guard only
    drops EXACT ties (``abs(diff) < 1e-9``).
  * the surviving 0.5pt "steps" are exactly the anti-pattern CLAUDE.md Rule 1
    forbids: prices that are not levels.

WHAT THIS MODULE DOES
---------------------
One rule, expressed RELATIVELY (Michael's standing principle — no fixed
points): consecutive ladder legs must be at least

    min_gap = max(k × ATR14, m × risk)

apart, measured as distance-from-entry so an inverted ladder violates too.
``k``/``m`` live in ``config/targets.yaml`` (``target_spacing:``), never
hardcoded here.

When a leg violates the gap:
  (a) PUSH  — move it out to the nearest REAL level that satisfies the gap;
  (b) DROP  — if no such level exists, the leg becomes absent (0.0) and its
      contract rides on to the next valid target / the runner.

A pushed leg may only land on a level that already exists: a TPO structural
level (IB edges, POC, VAH/VAL, PDH/PDL), a level a target producer already
computed for this fire, or a clean R multiple. It may never exceed the reach
the existing pipeline already granted the ladder (``max_reach``) — the rule
redistributes legs inside the ruled envelope, it never extends it. There is no
branch that invents a price.

FLAG (``TARGET_MIN_SPACING_V1``, default OFF in code)
-----------------------------------------------------
  unset / "0"           → OFF, byte-identical behaviour
  "shadow" / "1" / etc. → SHADOW: compute + log + record, change NOTHING
  "apply"               → live-apply (a separate ruling; not enabled 2026-08-21)

"1" deliberately means SHADOW, not apply: a careless ``=1`` must not be able to
move a live order. Only the literal "apply" does that.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

TICK = 0.25
EPS = 1e-9

MODE_OFF = "off"
MODE_SHADOW = "shadow"
MODE_APPLY = "apply"

_cfg_cache: Optional[Dict] = None

# The values below are only used when config/targets.yaml is unreachable; the
# YAML is the source of truth (see `target_spacing:` there for the derivation).
_CFG_FALLBACK = {
    "k_atr": 0.25,
    "m_risk": 0.33,
    "r_multiples": [1.0, 1.5, 2.0, 2.5, 3.0, 4.0],
    "atr_bars": 14,
}


def flag_mode() -> str:
    """Resolve TARGET_MIN_SPACING_V1 into off / shadow / apply."""
    raw = (os.getenv("TARGET_MIN_SPACING_V1", "0") or "0").strip().lower()
    if raw in ("", "0", "off", "false", "no"):
        return MODE_OFF
    if raw == "apply":
        return MODE_APPLY
    # everything else that is "on-ish" — including a bare 1 — is observe-only
    return MODE_SHADOW


def load_cfg() -> Dict:
    """k/m and the R-multiple menu from config/targets.yaml (`target_spacing:`)."""
    global _cfg_cache
    if _cfg_cache is not None:
        return _cfg_cache
    cfg = dict(_CFG_FALLBACK)
    try:
        import yaml
        with open("config/targets.yaml", "r") as f:
            doc = yaml.safe_load(f) or {}
        block = doc.get("target_spacing") or {}
        for key in _CFG_FALLBACK:
            if block.get(key) is not None:
                cfg[key] = block[key]
    except Exception as err:
        logger.warning("[TargetSpacing] targets.yaml unreadable (%s) — built-in k/m", err)
    _cfg_cache = cfg
    return cfg


def reset_cfg_cache() -> None:
    global _cfg_cache
    _cfg_cache = None


def snap(price: float) -> float:
    """Snap to the MES 0.25 grid (same helper shape as structural_targets)."""
    return round(round(float(price) / TICK) * TICK, 2)


def min_gap(atr14: Optional[float], risk: Optional[float],
            cfg: Optional[Dict] = None) -> Tuple[Optional[float], str]:
    """min_gap = max(k×ATR14, m×risk) — whichever inputs are actually alive.

    Honest None (Rule 1) when NEITHER input is usable: with no ATR and no risk
    there is no relative yardstick, and inventing a fixed-point one is exactly
    what Michael's principle forbids. Caller then leaves the ladder untouched.
    """
    cfg = cfg or load_cfg()
    parts: List[Tuple[str, float]] = []
    if atr14 is not None and float(atr14) > 0:
        parts.append(("k*ATR14", float(cfg["k_atr"]) * float(atr14)))
    if risk is not None and float(risk) > 0:
        parts.append(("m*risk", float(cfg["m_risk"]) * float(risk)))
    if not parts:
        return None, "no_basis(atr<=0 and risk<=0)"
    parts.sort(key=lambda p: p[1])
    name, val = parts[-1]
    if len(parts) == 1:
        # dead-ATR floor: risk alone still yields a relative gap; say so loudly
        # in the reason string so a report can never mistake it for a full basis.
        return round(val, 4), f"{name}(sole basis)"
    return round(val, 4), name


def build_candidates(
    *,
    entry: float,
    risk: Optional[float],
    tpo_ctx: Optional[Dict] = None,
    producer_levels: Optional[Sequence[Tuple[str, Optional[float]]]] = None,
    cfg: Optional[Dict] = None,
) -> List[Tuple[str, float]]:
    """Every REAL price a pushed leg is allowed to land on.

    Three families, no fourth:
      * TPO structure — IB edges, IB centre, POC, VAH/VAL, PDH/PDL;
      * levels a target producer already computed for THIS fire (the pre-clamp
        structural c1/c2/c3, a native leg ladder, …) — passed in by the caller;
      * clean R multiples off the real stop distance.
    """
    cfg = cfg or load_cfg()
    out: List[Tuple[str, float]] = []

    tpo = tpo_ctx or {}
    ibh, ibl = tpo.get("ib_high"), tpo.get("ib_low")
    for name, val in (("IBH", ibh), ("IBL", ibl), ("POC", tpo.get("poc")),
                      ("VAH", tpo.get("vah")), ("VAL", tpo.get("val")),
                      ("PDH", tpo.get("pd_high")), ("PDL", tpo.get("pd_low"))):
        if val is not None:
            try:
                out.append((name, float(val)))
            except (TypeError, ValueError):
                continue
    if ibh is not None and ibl is not None:
        try:
            out.append(("IB_CENTER", (float(ibh) + float(ibl)) / 2.0))
        except (TypeError, ValueError):
            pass

    for name, val in (producer_levels or []):
        if val is None:
            continue
        try:
            fv = float(val)
        except (TypeError, ValueError):
            continue
        if fv != 0.0:
            out.append((str(name), fv))

    if risk is not None and float(risk) > 0:
        for r in cfg["r_multiples"]:
            r = float(r)
            out.append((f"R{r:g}+", snap(entry + r * float(risk))))
            out.append((f"R{r:g}-", snap(entry - r * float(risk))))

    return out


def enforce_spacing(
    *,
    direction: str,
    entry: float,
    t1: Optional[float],
    t2: Optional[float],
    t3: Optional[float],
    risk: Optional[float],
    atr14: Optional[float],
    candidates: Optional[Sequence[Tuple[str, float]]] = None,
    cfg: Optional[Dict] = None,
) -> Dict:
    """Apply the minimum-spacing rule to (t1, t2, t3).

    Pure function — no I/O, no env reads, no logging side effects on the ladder.
    Returns a record: the corrected legs, per-leg branch (KEEP / PUSH / DROP)
    with the numbers, the min_gap and its basis, and `changed`.

    T1 is the anchor and is never moved: it is the leg the R:R gate, the realism
    ceiling and T1_BANK_R all already ruled on.
    """
    cfg = cfg or load_cfg()
    d = str(direction or "").upper()
    sign = 1.0 if d == "LONG" else -1.0

    def dist(p: Optional[float]) -> Optional[float]:
        if p is None or float(p) == 0.0:
            return None
        return sign * (float(p) - float(entry))

    legs = [("t1", t1), ("t2", t2), ("t3", t3)]
    gap, basis = min_gap(atr14, risk, cfg)

    rec: Dict = {
        "min_gap": gap,
        "basis": basis,
        "k_atr": float(cfg["k_atr"]),
        "m_risk": float(cfg["m_risk"]),
        "atr14": (round(float(atr14), 4) if atr14 else None),
        "risk": (round(float(risk), 4) if risk else None),
        "direction": d,
        "entry": float(entry),
        "before": {n: (float(v) if v else None) for n, v in legs},
        "after": {n: (float(v) if v else None) for n, v in legs},
        "branches": [],
        "changed": False,
    }
    if gap is None:
        rec["branches"].append({"leg": "-", "branch": "SKIP", "why": basis})
        return rec

    present = [(n, dist(v)) for n, v in legs]
    live_dists = [dv for _n, dv in present if dv is not None and dv > 0]
    if not live_dists:
        rec["branches"].append({"leg": "-", "branch": "SKIP", "why": "no live legs"})
        return rec
    # The rule never extends reach: a pushed leg may not go beyond the farthest
    # objective the existing (already-ruled) pipeline granted this ladder.
    max_reach = max(live_dists)
    rec["max_reach"] = round(max_reach, 4)

    cand: List[Tuple[str, float, float]] = []
    for name, price in (candidates or []):
        try:
            p = float(price)
        except (TypeError, ValueError):
            continue
        dv = sign * (p - float(entry))
        if dv > 0:
            cand.append((name, snap(p), round(dv, 6)))
    cand.sort(key=lambda c: c[2])

    out: Dict[str, Optional[float]] = {}
    prev_dist: Optional[float] = None
    for name, price in legs:
        dv = dist(price)
        if dv is None:
            out[name] = None
            rec["branches"].append({"leg": name, "branch": "ABSENT"})
            continue
        if prev_dist is None:
            # anchor leg — untouched by construction
            out[name] = float(price)
            prev_dist = dv
            rec["branches"].append(
                {"leg": name, "branch": "ANCHOR", "price": float(price),
                 "dist": round(dv, 4)})
            continue

        need = prev_dist + gap
        if dv >= need - EPS:
            out[name] = float(price)
            prev_dist = dv
            rec["branches"].append(
                {"leg": name, "branch": "KEEP", "price": float(price),
                 "dist": round(dv, 4), "need": round(need, 4)})
            continue

        # (a) PUSH to the nearest real level that satisfies the gap, inside reach
        pick = None
        for cname, cprice, cdist in cand:
            if cdist >= need - EPS and cdist <= max_reach + EPS:
                pick = (cname, cprice, cdist)
                break
        if pick is not None:
            out[name] = pick[1]
            prev_dist = pick[2]
            rec["changed"] = True
            rec["branches"].append(
                {"leg": name, "branch": "PUSH", "was": float(price),
                 "price": pick[1], "level": pick[0],
                 "dist_was": round(dv, 4), "dist": round(pick[2], 4),
                 "need": round(need, 4)})
            continue

        # (b) DROP — no real level satisfies the gap; the contract rides on
        out[name] = None
        rec["changed"] = True
        rec["branches"].append(
            {"leg": name, "branch": "DROP", "was": float(price),
             "dist_was": round(dv, 4), "need": round(need, 4),
             "why": "no real level at/beyond the gap within reach "
                    f"{round(max_reach, 4)}"})

    rec["after"] = out
    return rec


def format_shadow(rec: Dict) -> str:
    """The one-line evidence string: `t1..t3 = ... (reason)`."""
    a = rec.get("after") or {}
    def s(v):
        return f"{v:.2f}" if isinstance(v, (int, float)) and v else "—"
    reasons = []
    for b in rec.get("branches", []):
        br = b.get("branch")
        if br == "PUSH":
            reasons.append(f"{b['leg']} {b['was']:.2f}→{b['price']:.2f} on {b['level']}")
        elif br == "DROP":
            reasons.append(f"{b['leg']} {b['was']:.2f} dropped (needed ≥{b['need']:.2f}pt)")
    if not reasons:
        reasons.append("ladder already spaced")
    return (f"t1..t3 = {s(a.get('t1'))} / {s(a.get('t2'))} / {s(a.get('t3'))} "
            f"(min_gap={rec.get('min_gap')}pt via {rec.get('basis')}; "
            + "; ".join(reasons) + ")")


# ── ATR14, read straight from the canonical bar table ──────────────────────
_ATR_TTL_SEC = 30.0
_atr_cache: Tuple[float, float] = (0.0, 0.0)


def current_atr14() -> float:
    """14-bar mean TR from `v9_bars_5min_woodies` — the canonical bar table.

    Same computation as `mae_scratch.current_atr14`, but NOT gated on that
    module's own flag (S6_MAE_SCRATCH_ATR_V1): this rule must not silently lose
    its ATR basis because an unrelated feature is off. Honest 0.0 on failure —
    `min_gap` then falls back to the risk term alone and says so.
    """
    global _atr_cache
    import time as _time
    now = _time.monotonic()
    val, ts = _atr_cache
    if ts and (now - ts) < _ATR_TTL_SEC:
        return val
    atr = 0.0
    try:
        from backend.v9.db.read import read_all as _read
        n = int(load_cfg().get("atr_bars", 14))
        rows = _read(
            "SELECT high, low, close FROM v9_bars_5min_woodies "
            f"WHERE symbol='MES' ORDER BY ts DESC LIMIT {n}", {}) or []
        rows = list(reversed(rows))
        trs, prev = [], None
        for b in rows:
            h, l, c = float(b["high"]), float(b["low"]), float(b["close"])
            trs.append(h - l if prev is None
                       else max(h - l, abs(h - prev), abs(l - prev)))
            prev = c
        atr = (sum(trs) / len(trs)) if trs else 0.0
    except Exception as err:
        logger.debug("[TargetSpacing] ATR read failed (risk-only basis): %s", err)
        atr = 0.0
    _atr_cache = (atr, now)
    return atr


def reset_atr_cache() -> None:
    global _atr_cache
    _atr_cache = (0.0, 0.0)
