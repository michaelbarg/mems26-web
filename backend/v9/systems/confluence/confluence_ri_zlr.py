"""CONFLUENCE_RI_ZLR — S2 (REACTIVE/INITIATIVE) × S4 (ZLR) same-bar coincidence detector.

Spec (authoritative): docs/handoff/CONFLUENCE_PATTERN_SPEC_2026-07-17.md.
Research verdict (spec §0/§3.3): n=5 measured coincidences, +4-first hit-rate
40% (2/5) — raw EV negative-to-zero BEFORE location/day-type filters. The
evidence supports building the detector and collecting >=15 REAL shadow
samples, NOT trading it. Therefore V1 is SHADOW-ONLY: the combined setup is
routed through the normal gateway gate chain (session, feed_watchdog,
playbook, location, rr, halts) but NEVER reaches demo/live execution — see
the shadow-only guard in trading_gateway._route_setup_inner. Live routing is
separately gated by CONFLUENCE_RI_ZLR_LIVE and is NOT implemented (the guard
refuses even when that flag is set).

Flags
-----
CONFLUENCE_RI_ZLR_V1  (default OFF) — master switch. When unset,
    ``observe_route()`` returns None without registering anything: zero change
    to today's behavior.
CONFLUENCE_RI_ZLR_LIVE (default OFF) — RESERVED gate for future live routing.
    Not implemented; the gateway stub refuses demo/live for this
    classification either way. Enabling live = trading-risk-surface change →
    n>=15 shadow samples + explicit Michael sign-off (Pre-LIVE Discipline).

Join rule (spec §1.2)
---------------------
An S2 route (pattern REACTIVE_*/INITIATIVE_*, system_id=2) and an S4 route
(pattern ZLR, system_id=4) join into ONE combined setup when ALL of:
  1. same signal bar — ``bar_ts`` equality is CANONICAL when both routes carry
     it; the <=5s route-time window is the safety net (today neither
     build_s2_gateway_setup nor woodies_system.py:1101 puts bar_ts on the
     setup, so the window is the operative test);
  2. same direction (LONG/LONG or SHORT/SHORT);
  3. |entry_S2 − entry_S4| <= 1.0pt (both quote the close of the same bar; a
     larger delta = suspected bar-source split → do NOT fire).

G-fresh location filter (spec §1.3, recommended gate)
-----------------------------------------------------
The signal bar must CLOSE beyond the prior-3-bar extreme in the trade
direction (LONG: close > max(high[-3..-1]); SHORT: close < min(low[-3..-1])).
Evaluated on the canonical S4 bar series (v9_bars_5min_woodies — the series S4
actually fires on, spec §3.1; same convention as the gateway's
S4_ENTRY_CONFIRM_V1 block: the newest row at route time IS the signal bar).
Missing/short/mismatched bars → HONEST reject (Source-of-Truth Rule 1): no
setup, reason logged — never a synthesized pass.

Combined setup (spec §2)
------------------------
  entry     = nearest-tick midpoint of the two parent entries
  C1 (t1)   = entry ± 4.0pt · C2 (t2) = entry ± 8.0pt · no T3, no runner
  stop      = structural: the S4 parent's registered stop (stop_anchors.yaml
              anchor ``breakout_bar`` window=1, −3 ticks — the ZLR signal-bar
              extreme), fallback = signal-bar extreme ± 3 ticks computed from
              the same canonical bars; then floor 4 ticks / CAP 7.0pt.
  contracts = EXACTLY 2 (sizing "tactical", mode_caps.tactical) — carries
              metadata.fixed_contracts_exempt=1 so effective_contracts()
              (sierra_command.py) exempts it from the FIXED_CONTRACTS_4 force.
  BE        = after C1 → existing be_after_t1 canon (MODIFY_STOP path /
              System6 protective) — nothing pattern-specific here.

Slot competition / double-count caveat (spec §4.4 V1)
-----------------------------------------------------
Parents are NOT suppressed. By the time the join completes (on the SECOND
parent's route, seconds after the first), the first parent — usually the ZLR —
has already routed and may already hold the live slot; holding/suppressing
parents is the V2 "confluence-priority" design and needs a separate Michael
ruling (spec §4.4-2). V1 emits the combined setup as an ADDITIONAL shadow-only
record alongside both parents, so no live/demo double-fire is possible. The
n>=15 analysis MUST dedup by metadata.confluence.parents — the same move is
counted up to 3× across records (S2 shadow + S4 shadow/live + confluence
shadow).
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

CLASSIFICATION = "CONFLUENCE_RI_ZLR"
SPEC_REF = "docs/handoff/CONFLUENCE_PATTERN_SPEC_2026-07-17.md"

TICK = 0.25
ENTRY_TOL_PTS = 1.0        # spec §1.2-3: larger delta = bar-source-split suspicion
ROUTE_WINDOW_S = 5.0       # spec §1.2-1: route-level sync window (safety net)
REGISTRY_TTL_S = 300.0     # spec §4.1: pending parent fires live one 5-min bar
EMITTED_TTL_S = 900.0      # emitted-key memory (dedup) — outlives the bar comfortably
C1_PTS = 4.0               # spec §2
C2_PTS = 8.0               # spec §2
STOP_CAP_PTS = 7.0         # spec §2: deliberately tighter than ZLR's max_risk_points 15
STOP_FLOOR_PTS = 1.0       # spec §2: 4-tick floor (existing stop_params floor)
G_FRESH_LOOKBACK = 3       # spec §1.3: prior-3-bar extreme


def enabled() -> bool:
    """CONFLUENCE_RI_ZLR_V1, default OFF (no env var needed for the code default)."""
    return os.getenv("CONFLUENCE_RI_ZLR_V1", "0").strip().lower() in ("1", "true", "yes")


def _round_tick(price: float) -> float:
    """Snap to the MES 0.25 tick grid."""
    return round(round(float(price) * 4.0) / 4.0, 2)


def load_signal_bars(limit: int = G_FRESH_LOOKBACK + 1) -> List[Dict[str, Any]]:
    """Last ``limit`` bars of the canonical S4 series, OLDEST-first.

    bars[-1] is the just-closed signal bar (same convention as the gateway's
    S4_ENTRY_CONFIRM_V1 block, which reads the newest v9_bars_5min_woodies row
    as the signal bar at route time). Returns [] on any DB problem (read_all
    already swallows + logs) — the caller then rejects honestly, never
    synthesizes. Tests monkeypatch this function.
    """
    from backend.v9.db.read import read_all

    rows = read_all(
        "SELECT ts, open, high, low, close FROM v9_bars_5min_woodies "
        "ORDER BY ts DESC LIMIT :n",
        {"n": int(limit)},
    )
    return [dict(r) for r in reversed(rows)]


def g_fresh_check(direction: str, entry_mid: float,
                  bars: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    """Spec §1.3 G-fresh: signal bar closes beyond the prior-3-bar extreme.

    Returns ``(passed, evidence)``. Fail-honest (Rule 1): not enough bars, bad
    rows, or a signal-bar close farther than ENTRY_TOL_PTS from the joined
    entry (we would be measuring the wrong bar / a split series) → (False,
    evidence-with-reason). Never a synthesized pass.
    """
    need = G_FRESH_LOOKBACK + 1
    if not isinstance(bars, list) or len(bars) < need:
        return False, {"pass": False,
                       "reason": f"insufficient_bars({len(bars) if isinstance(bars, list) else 'none'}<{need})"}
    try:
        sig = bars[-1]
        sig_close = float(sig["close"])
        prior = bars[-need:-1]
        highs = [float(b["high"]) for b in prior]
        lows = [float(b["low"]) for b in prior]
    except (KeyError, TypeError, ValueError) as err:
        return False, {"pass": False, "reason": f"bad_bar_rows({err})"}
    if abs(sig_close - float(entry_mid)) > ENTRY_TOL_PTS:
        return False, {"pass": False, "reason": "signal_bar_mismatch",
                       "signal_close": sig_close, "entry_mid": float(entry_mid),
                       "signal_ts": str(sig.get("ts"))}
    if direction == "LONG":
        extreme = max(highs)
        ok = sig_close > extreme
    else:
        extreme = min(lows)
        ok = sig_close < extreme
    evidence: Dict[str, Any] = {
        "pass": ok,
        "rule": "close beyond prior-3-bar extreme in trade direction",
        "direction": direction,
        "signal_close": sig_close,
        "prior3_extreme": extreme,
        "signal_ts": str(sig.get("ts")),
    }
    if not ok:
        evidence["reason"] = "stale_signal_not_beyond_prior3"
    return ok, evidence


class ConfluenceRegistry:
    """Per-bar registry of parent route attempts (spec §4.1 buffer, TTL = 1 bar).

    Values are SNAPSHOTS (scalars copied at registration) — the gateway mutates
    the parent setup dict downstream (stop resolver, target producers), so we
    never hold a reference to it.
    """

    def __init__(self, now_fn=time.monotonic):
        self._now = now_fn
        # (kind, direction) -> latest pending parent record
        self._pending: Dict[Tuple[str, str], Dict[str, Any]] = {}
        # (signal_key, direction) -> emitted-at monotonic ts (one emission per bar+dir)
        self._emitted: Dict[Tuple[str, str], float] = {}

    def prune(self) -> None:
        now = self._now()
        self._pending = {k: r for k, r in self._pending.items()
                         if now - r["mono"] <= REGISTRY_TTL_S}
        self._emitted = {k: t for k, t in self._emitted.items()
                         if now - t <= EMITTED_TTL_S}

    def register_and_match(self, rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Store ``rec`` (latest fire of its kind+direction wins) and return the
        matching counterpart record if the join conditions hold, else None."""
        self.prune()
        self._pending[(rec["kind"], rec["direction"])] = rec
        other_kind = "S4" if rec["kind"] == "S2" else "S2"
        other = self._pending.get((other_kind, rec["direction"]))
        if other is None:
            return None
        # Same signal bar: bar_ts equality is CANONICAL when both carry it
        # (spec §1.2-1); the <=5s route window is only the safety net.
        bt_a, bt_b = rec.get("bar_ts"), other.get("bar_ts")
        if bt_a is not None and bt_b is not None:
            if str(bt_a) != str(bt_b):
                return None
        elif abs(rec["mono"] - other["mono"]) > ROUTE_WINDOW_S:
            return None
        if abs(rec["entry"] - other["entry"]) > ENTRY_TOL_PTS:
            return None
        return other

    def mark_emitted(self, direction: str, signal_key: Any) -> bool:
        """True exactly once per (signal bar, direction) — caller may emit."""
        key = (str(signal_key), direction)
        if key in self._emitted:
            return False
        self._emitted[key] = self._now()
        return True

    def consume(self, direction: str) -> None:
        """Drop both pending parents for ``direction`` after an emission."""
        self._pending.pop(("S2", direction), None)
        self._pending.pop(("S4", direction), None)


_registry = ConfluenceRegistry()


def reset_registry(now_fn=None) -> None:
    """Test hygiene only — fresh registry (optionally with an injected clock)."""
    global _registry
    _registry = ConfluenceRegistry(now_fn or time.monotonic)


def _parent_kind(cls: str, system_id: int) -> Optional[str]:
    """S2 = REACTIVE_*/INITIATIVE_* from system 2 · S4 = exactly ZLR from system 4.

    Exact-"ZLR" match mirrors sierra_command._is_zlr_setup — no other pattern
    uses that id, and other woodies patterns (TLB/TT/GB100/…) must NOT join.
    """
    if system_id == 2 and cls.startswith(("REACTIVE", "INITIATIVE")):
        return "S2"
    if system_id == 4 and cls == "ZLR":
        return "S4"
    return None


def _resolve_stop(direction: str, entry: float, s4_rec: Dict[str, Any],
                  bars: List[Dict[str, Any]]) -> Tuple[Optional[float], str]:
    """Structural stop per spec §2, floored at 4 ticks and CAPPED at 7.0pt.

    Preference order (both are the SAME structural definition — the ZLR
    breakout_bar window=1 anchor, ±3 ticks beyond the signal-bar extreme):
      1. the S4 parent's own registered stop (raw detector stop, snapshotted
         at registration BEFORE any gateway resolver mutation);
      2. computed from the canonical signal bar (bars[-1]) directly.
    A candidate on the wrong side of entry is skipped (corrupted source). No
    valid structural source → (None, reason): honest reject, never synthesized.
    """
    sign_against = -1.0 if direction == "LONG" else 1.0
    candidates: List[Tuple[float, str]] = []
    s4_stop = s4_rec.get("stop")
    if s4_stop:  # 0.0 (woodies "no stop" placeholder) is falsy → skipped
        candidates.append((float(s4_stop), "s4_parent_stop"))
    if isinstance(bars, list) and bars:
        try:
            sig = bars[-1]
            # 6T beyond structure — Michael ruling 2026-07-20 (was 3T); keep in
            # sync with config/stop_anchors.yaml anchor_offset_ticks.
            raw = (float(sig["low"]) - 6 * TICK) if direction == "LONG" \
                else (float(sig["high"]) + 6 * TICK)
            candidates.append((raw, "signal_bar_extreme_6t"))
        except (KeyError, TypeError, ValueError):
            pass
    for raw, src in candidates:
        risk = (entry - raw) if direction == "LONG" else (raw - entry)
        if risk <= 0:
            continue  # wrong side — try the next structural source
        risk = min(max(risk, STOP_FLOOR_PTS), STOP_CAP_PTS)
        return round(entry + sign_against * risk, 2), src
    return None, "no_structural_stop_source"


def _build_combined(rec: Dict[str, Any], other: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build the CONFLUENCE_RI_ZLR setup from two matched parent records."""
    s2 = rec if rec["kind"] == "S2" else other
    s4 = rec if rec["kind"] == "S4" else other
    direction = rec["direction"]
    sign = 1.0 if direction == "LONG" else -1.0

    entry = _round_tick((s2["entry"] + s4["entry"]) / 2.0)
    bars = load_signal_bars(G_FRESH_LOOKBACK + 1)
    ok, evidence = g_fresh_check(direction, entry, bars)
    if not ok:
        logger.info("[Confluence] join found but G-fresh REJECT (%s %s @%s): %s",
                    direction, CLASSIFICATION, entry, evidence)
        return None

    signal_key = s4.get("bar_ts") or s2.get("bar_ts") or evidence.get("signal_ts")
    if not _registry.mark_emitted(direction, signal_key):
        logger.info("[Confluence] already emitted for bar %s %s — skipping duplicate",
                    signal_key, direction)
        return None
    _registry.consume(direction)

    stop, stop_src = _resolve_stop(direction, entry, s4, bars)
    if stop is None:
        logger.info("[Confluence] join found but NO structural stop source "
                    "(%s @%s) — honest reject", direction, entry)
        return None

    t1 = round(entry + sign * C1_PTS, 2)
    t2 = round(entry + sign * C2_PTS, 2)
    confidence = max(float(s2.get("confidence") or 0.0), float(s4.get("confidence") or 0.0))

    setup = {
        "firing_system": 4,          # spec §4.1: routed on the S4 execution path
        "direction": direction,
        "classification": CLASSIFICATION,
        "pattern": CLASSIFICATION,
        "confidence": confidence,
        "entry_price": entry,
        "stop": stop,
        "t1": t1,
        "t2": t2,
        "t3": None,                  # spec §2: no T3, no runner
        "contracts": 2,              # spec §2: exactly 2 (tactical)
        "bar_ts": signal_key,
        "metadata": {
            "pattern": CLASSIFICATION,
            "sizing": 2,
            "sizing_mode": "tactical",           # mode_caps.tactical (stop_anchors.yaml)
            "fixed_contracts_exempt": 1,         # spec §4.3 — see effective_contracts()
            "confluence": {
                "spec": SPEC_REF,
                "parents": [
                    {"system": 2, "pattern": s2.get("pattern"),
                     "entry": s2.get("entry"), "bar_ts": s2.get("bar_ts")},
                    {"system": 4, "pattern": s4.get("pattern"),
                     "entry": s4.get("entry"), "bar_ts": s4.get("bar_ts"),
                     "stop": s4.get("stop")},
                ],
                "entry_delta_pts": round(abs(s2["entry"] - s4["entry"]), 2),
                "g_fresh": evidence,
                "stop_source": stop_src,
                "shadow_only": True,             # V1 — see gateway guard
            },
        },
    }
    logger.info("[Confluence] EMIT %s %s entry=%.2f stop=%.2f (src=%s) t1=%.2f t2=%.2f "
                "contracts=2 (parents: S2 %s @%.2f · S4 %s @%.2f)",
                CLASSIFICATION, direction, entry, stop, stop_src, t1, t2,
                s2.get("pattern"), s2["entry"], s4.get("pattern"), s4["entry"])
    return setup


def observe_route(setup: Dict[str, Any], system_id: int) -> Optional[Dict[str, Any]]:
    """Gateway hook — called for EVERY route attempt (trading_gateway.route_setup).

    Registers parent fires (S2 REACTIVE_*/INITIATIVE_* · S4 ZLR) and returns the
    combined CONFLUENCE_RI_ZLR setup when ``setup`` completes a join per the
    spec; else None. Flag OFF → immediate None (zero registration). NEVER
    mutates ``setup``; the caller wraps this in try/except so a bug here can
    never break parent routing.
    """
    if not enabled():
        return None
    if not isinstance(setup, dict):
        return None
    cls = str(setup.get("classification")
              or (setup.get("metadata") or {}).get("pattern") or "").strip().upper()
    if cls == CLASSIFICATION:
        return None  # never join on our own emission (recursion guard)
    kind = _parent_kind(cls, int(system_id))
    if kind is None:
        return None
    direction = str(setup.get("direction") or "").strip().upper()
    if direction not in ("LONG", "SHORT"):
        return None
    try:
        entry = float(setup.get("entry_price"))
    except (TypeError, ValueError):
        return None
    try:
        stop = float(setup.get("stop")) if setup.get("stop") else None
    except (TypeError, ValueError):
        stop = None
    rec = {
        "kind": kind,
        "direction": direction,
        "entry": entry,
        "stop": stop,
        "pattern": cls,
        "confidence": setup.get("confidence") or 0.0,
        "bar_ts": setup.get("bar_ts"),
        "mono": _registry._now(),
    }
    other = _registry.register_and_match(rec)
    if other is None:
        return None
    return _build_combined(rec, other)
