"""Extract SHADOW trade display fields from v9_trades rows (pattern, trigger, context)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _first_dict(*candidates: Any) -> Dict[str, Any]:
    for c in candidates:
        if isinstance(c, dict):
            return c
    return {}


def _system_state(cross_context: Any, system_key: str) -> Dict[str, Any]:
    if not isinstance(cross_context, list):
        if isinstance(cross_context, dict):
            # Gateway registry snapshot: system blobs at top level
            top = cross_context.get(system_key)
            if isinstance(top, dict):
                return dict(top)
            systems = cross_context.get("systems") or cross_context.get("gateway_registry")
            if isinstance(systems, dict):
                return _first_dict(systems.get(system_key))
        return {}
    for item in cross_context:
        if not isinstance(item, dict):
            continue
        systems = item.get("systems")
        if isinstance(systems, dict) and system_key in systems:
            return dict(systems[system_key])
    for item in cross_context:
        if isinstance(item, dict) and system_key.replace("_system", "") in str(item.get("trigger", "")):
            return item
    return {}


_SYSTEM_REGISTRY_KEYS = {
    1: ("day_type_machine", "day_type_system"),
    2: ("five_min_system",),
    3: ("footprint_system",),
    4: ("woodies_system",),
    5: ("tpo_system",),
    6: ("killzone_system",),
}

_SYSTEM_NAMES = {
    1: "Day Type",
    2: "5-Min",
    3: "Footprint",
    4: "Woodies",
    5: "TPO",
    6: "Killzone",
}

MES_POINT_VALUE = 5.0  # MES $5/point — keep in sync with TradeManager


def _valid_target(price: Any) -> Optional[float]:
    if price is None:
        return None
    try:
        p = float(price)
    except (TypeError, ValueError):
        return None
    return p if p > 0 else None


def compute_trade_pnl(trade) -> Dict[str, Any]:
    """Per-contract P&L; partial = sum of hit targets only (C3 open = $0)."""
    entry = trade.entry_price
    if entry is None:
        return {
            "pnl_usd": trade.pnl_usd,
            "pnl_r": trade.pnl_r,
            "pnl_mode": "open",
            "contracts_pnl": [],
        }

    direction_mult = 1.0 if trade.direction == "LONG" else -1.0
    stop = _valid_target(trade.stop)
    t1 = _valid_target(trade.t1)
    t2 = _valid_target(trade.t2)
    t3 = _valid_target(trade.t3)
    risk_per_contract = abs(entry - stop) * MES_POINT_VALUE if stop is not None else None

    def _leg(label: str, target: Optional[float], hit: bool, exit_price: float) -> Dict[str, Any]:
        pts = (exit_price - entry) * direction_mult
        pnl = round(pts * MES_POINT_VALUE, 2)
        r = None
        if risk_per_contract and risk_per_contract > 0:
            r = round(pnl / risk_per_contract, 2)
        return {
            "id": label,
            "status": "HIT" if hit else "OPEN",
            "exit_price": exit_price,
            "pnl_usd": pnl,
            "pnl_r": r,
        }

    legs: List[Dict[str, Any]] = []
    is_closed = trade.state == "CLOSED" or trade.exit_reason is not None

    if is_closed and trade.exit_reason == "STOP_HIT" and stop is not None:
        for label, target, hit_ts in (("C1", t1, trade.t1_hit_ts), ("C2", t2, trade.t2_hit_ts), ("C3", t3, trade.t3_hit_ts)):
            hit = hit_ts is not None
            exit_p = target if hit and target is not None else stop
            legs.append(_leg(label, target, hit, exit_p))
    elif is_closed:
        exit_p = _valid_target(trade.exit_price) or entry
        for label, target, hit_ts in (("C1", t1, trade.t1_hit_ts), ("C2", t2, trade.t2_hit_ts), ("C3", t3, trade.t3_hit_ts)):
            hit = hit_ts is not None
            ep = target if hit and target is not None else exit_p
            legs.append(_leg(label, target, hit, ep))
    else:
        for label, target, hit_ts in (("C1", t1, trade.t1_hit_ts), ("C2", t2, trade.t2_hit_ts), ("C3", t3, trade.t3_hit_ts)):
            if hit_ts is not None and target is not None:
                legs.append(_leg(label, target, True, target))
            else:
                legs.append(_leg(label, target, False, entry))

    total = round(sum(l["pnl_usd"] for l in legs), 2)
    hits = sum(1 for l in legs if l["status"] == "HIT")
    if is_closed:
        mode = "closed"
    elif hits > 0:
        mode = "partial"
    else:
        mode = "open"

    pnl_r = trade.pnl_r
    if risk_per_contract and risk_per_contract > 0 and hits > 0:
        pnl_r = round(total / (hits * risk_per_contract), 2)
    elif trade.pnl_r is not None:
        pnl_r = trade.pnl_r

    pnl_usd = trade.pnl_usd if is_closed and trade.pnl_usd is not None else total

    return {
        "pnl_usd": pnl_usd,
        "pnl_r": pnl_r,
        "pnl_mode": mode,
        "contracts_pnl": legs,
    }


def _snapshot_hint(system_id: int, blob: Dict[str, Any]) -> Optional[str]:
    if not blob or blob.get("error"):
        return None
    if system_id == 1:
        return blob.get("day_type") or blob.get("state")
    if system_id == 2:
        return blob.get("last_classification") or blob.get("mode")
    if system_id == 3:
        return blob.get("last_classification") or blob.get("combined_class")
    if system_id == 4:
        ap = blob.get("active_patterns")
        if isinstance(ap, list) and ap and isinstance(ap[0], dict):
            return ap[0].get("pattern_id") or ap[0].get("pattern")
        return blob.get("classification") or blob.get("signal")
    if system_id == 5:
        return blob.get("day_type") or blob.get("profile")
    if system_id == 6:
        return blob.get("zone") or blob.get("state")
    return None


def _registry_key_names() -> tuple:
    out: list = []
    for keys in _SYSTEM_REGISTRY_KEYS.values():
        out.extend(keys)
    return tuple(out)


def _systems_blob_at_entry(cross_context: Any) -> Dict[str, Dict[str, Any]]:
    """Gateway entry snapshot: systems map inside first cross_context row.

    Supports:
    * TradeManager list row: ``[{"systems": {day_type_machine: {...}, ...}}]``
    * Legacy gateway flat dict: ``{day_type_machine: {...}, five_min_system: ...}``
    * CrossSystemSnapshotService row: ``[{"systems": {"1": {...}, "2": ...}}]`` (numeric keys)
    """
    registry_keys = _registry_key_names()

    def _normalize_systems_map(raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for k, v in raw.items():
            if not isinstance(v, dict):
                continue
            if k in registry_keys:
                out[k] = dict(v)
            elif str(k).isdigit() and int(k) in _SYSTEM_REGISTRY_KEYS:
                for name in _SYSTEM_REGISTRY_KEYS[int(k)]:
                    out[name] = dict(v)
                    break
        return out

    if isinstance(cross_context, list):
        for item in cross_context:
            if not isinstance(item, dict):
                continue
            systems = item.get("systems")
            if isinstance(systems, dict) and systems:
                mapped = _normalize_systems_map(systems)
                if mapped:
                    return mapped
    if isinstance(cross_context, dict):
        systems = cross_context.get("systems")
        if isinstance(systems, dict) and systems:
            mapped = _normalize_systems_map(systems)
            if mapped:
                return mapped
        mapped = _normalize_systems_map(cross_context)
        if mapped:
            return mapped
    return {}


def _stop_initial_from_trade(trade) -> Optional[float]:
    quality = trade.quality if isinstance(trade.quality, dict) else {}
    meta = quality.get("metadata") if isinstance(quality.get("metadata"), dict) else {}
    raw = meta.get("stop_initial")
    if raw is not None:
        try:
            return float(raw)
        except (TypeError, ValueError):
            pass
    if trade.stop is not None and not trade.t1_hit_ts:
        return float(trade.stop)
    return None


def _system_agrees(sid: int, direction: str, blob: Dict[str, Any]) -> Optional[bool]:
    """True=agrees with trade direction, False=against, None=neutral/unknown."""
    if not blob or blob.get("error"):
        return None
    d = direction.upper()
    if sid == 1:
        dt = (blob.get("day_type") or blob.get("state") or "").lower()
        if "trend" in dt and d == "LONG":
            return True
        if "trend" in dt and d == "SHORT":
            return True
        if dt in ("nontrend", "neutral", "normal"):
            return None
        return None
    if sid == 2:
        mode = (blob.get("mode") or blob.get("last_classification") or "").upper()
        if "LONG" in mode or mode == "BULL":
            return d == "LONG"
        if "SHORT" in mode or mode == "BEAR":
            return d == "SHORT"
        return None
    if sid == 3:
        sig = blob.get("last_signal") if isinstance(blob.get("last_signal"), dict) else {}
        sig_dir = (sig.get("direction") or "").upper()
        if sig_dir in ("LONG", "SHORT"):
            return sig_dir == d
        dom = (blob.get("dominance") or blob.get("combined_class") or "").upper()
        if dom == "BUYERS" or dom == "BULLISH":
            return d == "LONG"
        if dom == "SELLERS" or dom == "BEARISH":
            return d == "SHORT"
        return None
    if sid == 4:
        trend = (blob.get("trend_state") or "").upper()
        if trend in ("GREEN", "BULL"):
            return d == "LONG"
        if trend in ("RED", "BEAR"):
            return d == "SHORT"
        ap = blob.get("active_patterns")
        if isinstance(ap, list) and ap and isinstance(ap[0], dict):
            pd = (ap[0].get("direction") or "").upper()
            if pd in ("LONG", "SHORT"):
                return pd == d
        return None
    if sid == 5:
        mig = blob.get("poc_migration") if isinstance(blob.get("poc_migration"), dict) else {}
        mig_dir = (mig.get("direction") or "").upper()
        if mig_dir == "UP":
            return d == "LONG"
        if mig_dir == "DOWN":
            return d == "SHORT"
        return None
    if sid == 6:
        cz = blob.get("current_zone") if isinstance(blob.get("current_zone"), dict) else blob
        edge = cz.get("edge_class") if isinstance(cz, dict) else None
        if edge == "high":
            return d == "SHORT"
        if edge == "low":
            return d == "LONG"
        return None
    return None


def extract_system_agreement(trade) -> List[Dict[str, Any]]:
    """Per-system agree / disagree / neutral at entry (for trades table)."""
    direction = (trade.direction or "LONG").upper()
    firing = int(trade.firing_system or 0)
    systems_map = _systems_blob_at_entry(trade.cross_context)
    out: List[Dict[str, Any]] = []
    for sid in (1, 2, 3, 4, 5, 6):
        blob: Dict[str, Any] = {}
        for key in _SYSTEM_REGISTRY_KEYS.get(sid, ()):
            if key in systems_map:
                blob = systems_map[key]
                break
        agree = _system_agrees(sid, direction, blob)
        out.append({
            "id": sid,
            "name": _SYSTEM_NAMES[sid],
            "agree": agree,
            "is_firing": sid == firing,
            "hint": _snapshot_hint(sid, blob),
        })
    return out


def _recognition_lines(sid: int, blob: Dict[str, Any]) -> List[str]:
    """Human-readable lines: what this system 'saw' at entry."""
    if not blob:
        return ["No snapshot at entry"]
    lines: List[str] = []
    if sid == 1:
        for key in ("day_type", "state", "probability", "directional_certainty", "trading_confidence"):
            if blob.get(key) is not None:
                lines.append(f"{key}={blob[key]}")
    elif sid == 2:
        for key in ("mode", "last_classification", "last_pattern", "last_confluence"):
            if blob.get(key) is not None:
                lines.append(f"{key}={blob[key]}")
    elif sid == 3:
        dom = blob.get("dominance") or blob.get("combined_class")
        if dom:
            lines.append(f"dominance={dom}")
        sig = blob.get("last_signal") if isinstance(blob.get("last_signal"), dict) else None
        if sig:
            lines.append(f"signal={sig.get('signal')} {sig.get('direction', '')}".strip())
        if blob.get("last_classification"):
            lines.append(f"class={blob['last_classification']}")
    elif sid == 4:
        for key in ("trend_state", "trend_original", "cci_14", "signal", "classification"):  # D-WDIAG
            if blob.get(key) is not None:
                val = blob[key]
                lines.append(f"{key}={val:.2f}" if isinstance(val, float) else f"{key}={val}")
        ap = blob.get("active_patterns")
        if isinstance(ap, list) and ap:
            p0 = ap[0] if isinstance(ap[0], dict) else {}
            pid = p0.get("pattern_id") or p0.get("pattern")
            if pid:
                lines.append(f"active_pattern={pid}")
    elif sid == 5:
        for key in ("day_type", "profile_shape", "poc", "vah", "val"):
            if blob.get(key) is not None:
                lines.append(f"{key}={blob[key]}")
        mig = blob.get("poc_migration") if isinstance(blob.get("poc_migration"), dict) else None
        if mig and mig.get("direction"):
            lines.append(f"poc_migration={mig['direction']}")
    elif sid == 6:
        cz = blob.get("current_zone") if isinstance(blob.get("current_zone"), dict) else blob
        if isinstance(cz, dict):
            if cz.get("name"):
                lines.append(f"zone={cz['name']}")
            if cz.get("edge_class"):
                lines.append(f"edge={cz['edge_class']}")
    if not lines and blob:
        for key in ("running", "hydrated", "status", "mode", "day_type", "trend_state"):
            if blob.get(key) is not None:
                lines.append(f"{key}={blob[key]}")
    return lines[:10] if lines else ["(empty snapshot)"]


def extract_trade_lifecycle(cross_context: Any) -> List[Dict[str, Any]]:
    """Timeline of registry snapshots on this trade."""
    if not isinstance(cross_context, list):
        return []
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(cross_context):
        if not isinstance(item, dict):
            continue
        if i == 0 and item.get("systems"):
            out.append({
                "event": "entry",
                "label": "Entry — systems snapshot",
                "detail": item.get("trigger") or item.get("classification"),
            })
            continue
        trig = item.get("trigger") or item.get("event") or f"snapshot_{i}"
        systems = item.get("systems") if isinstance(item.get("systems"), dict) else {}
        out.append({
            "event": str(trig),
            "label": str(trig).replace("_", " "),
            "detail": f"{len(systems)} systems captured" if systems else None,
        })
    return out


def extract_trade_insight(trade) -> Dict[str, Any]:
    """What fired and what each system recognized — for trade detail modal."""
    display = extract_trade_display(trade)
    firing = int(trade.firing_system or 0)
    direction = (trade.direction or "").upper()
    trigger = display.get("trigger") or ""
    pattern = display.get("pattern_id") or ""
    classification = display.get("classification") or ""
    confidence = display.get("confidence")
    systems_map = _systems_blob_at_entry(trade.cross_context)

    headline = f"S{firing} { _SYSTEM_NAMES.get(firing, '')} · {direction} · FIRE"
    if trigger:
        headline += f" · {trigger}"
    if pattern:
        headline += f" ({pattern})"

    recognition: List[Dict[str, Any]] = []
    for sid in (1, 2, 3, 4, 5, 6):
        blob: Dict[str, Any] = {}
        for key in _SYSTEM_REGISTRY_KEYS.get(sid, ()):
            if key in systems_map:
                blob = systems_map[key]
                break
        recognition.append({
            "id": sid,
            "name": _SYSTEM_NAMES[sid],
            "role": "fire" if sid in (2, 3, 4) else "observe",
            "is_firing": sid == firing,
            "agree": _system_agrees(sid, direction, blob),
            "lines": _recognition_lines(sid, blob),
        })

    return {
        "fire": {
            "headline": headline,
            "firing_system": firing,
            "firing_name": _SYSTEM_NAMES.get(firing, ""),
            "direction": direction,
            "trigger": trigger,
            "pattern_id": pattern,
            "classification": classification,
            "confidence": confidence,
            "day_type": display.get("day_type"),
            "blocked_by": display.get("blocked_by"),
        },
        "recognition": recognition,
        "lifecycle": extract_trade_lifecycle(trade.cross_context),
    }


def extract_trade_systems_panel(trade) -> Dict[str, Any]:
    """Per-system involvement at trade entry for cockpit ActiveTrade + Switcher."""
    firing = int(trade.firing_system or 0)
    entry_price = trade.entry_price
    systems_map = _systems_blob_at_entry(trade.cross_context)
    out: List[Dict[str, Any]] = []

    for sid in (1, 2, 3, 4, 5, 6):
        blob: Dict[str, Any] = {}
        for key in _SYSTEM_REGISTRY_KEYS.get(sid, ()):
            if key in systems_map:
                blob = systems_map[key]
                break
        hint = _snapshot_hint(sid, blob)
        involved = sid == firing or bool(hint) or bool(blob)
        is_firing = sid == firing
        out.append({
            "id": sid,
            "name": _SYSTEM_NAMES[sid],
            "role": "fire" if sid in (2, 3, 4) else "observe",
            "involved": involved,
            "is_firing": is_firing,
            "hint": hint,
            "entry_price": entry_price if is_firing else None,
        })

    return {
        "firing_system": firing,
        "entry_price": entry_price,
        "systems": out,
    }


# Cache for the S1_NEW_CLASSIFIER promotion — recompute at most every 30s (a fire-burst
# must not re-run the full classify pipeline per trade). Mutated in place; no global needed.
_NC_CACHE: Dict[str, Any] = {}

# ── Anti-flap hysteresis state (Michael 2026-07-09). Module-level, mutated in place. ──
_ANTIFLAP_STATE: Dict[str, Any] = {"stable": None, "pending": None, "since": 0.0}


def _antiflap_day_type(raw: Optional[str], now: float, hold_s: float, state: Dict[str, Any]) -> Optional[str]:
    """Hysteresis on the LIVE day-type (2026-07-09 incident): a CHANGE must persist >= hold_s
    before it propagates to the gates, so a bar-to-bar flapping machine can't jerk them
    (07-09: REACTIVE/ZLR were SKIP'd on a transient 'Nontrend' on a +50pt drive-up day, while
    classify_replay stayed stable). Pure + testable; `state` = {"stable","pending","since"}.

    - first-ever value is accepted immediately (nothing to protect);
    - a transient None keeps the last stable value (no flap-to-None);
    - a value equal to the current stable clears any pending candidate;
    - a differing value must hold >= hold_s (≈ a bar) before it becomes the new stable.
    """
    if raw is None:
        return state.get("stable")                       # transient gap → hold last stable
    if raw == state.get("stable"):
        state["pending"] = None                          # confirms current → drop candidate
        return state["stable"]
    if raw != state.get("pending"):                      # a new candidate starts its clock
        state["pending"] = raw
        state["since"] = now
    if state.get("stable") is None:                      # no prior stable → accept immediately
        state["stable"] = raw
        state["pending"] = None
        return raw
    if now - float(state.get("since", now)) >= hold_s:   # held long enough → promote
        state["stable"] = raw
        state["pending"] = None
        return raw
    return state["stable"]                                # not held long enough → keep stable


def _live_day_type_machine() -> Any:
    """The RUNNING app's day_type machine — backend.main's, never the dead wrapper.

    P0 (07-22 17:40, Michael "למה אין זיהוי"): importing backend.v9.app gives a
    DIFFERENT, EMPTY instance (the documented dead-wrapper trap, CLAUDE.md
    §Codebase Index). Read the live process' app first via sys.modules (present in
    production, absent in unit tests → fallback). Factored out so get_live_day_type()
    and daytype_is_provisional() cannot drift onto two different machines.
    """
    import importlib as _il
    import sys as _sys
    _main_mod = _sys.modules.get("backend.main")
    _live_app = getattr(_main_mod, "app", None) if _main_mod else None
    _app_mod = _live_app if _live_app is not None else _il.import_module("backend.v9.app").app
    return getattr(_app_mod.state, "day_type_machine", None)


def daytype_is_provisional() -> bool:
    """DAYTYPE_HONEST_PRELOCK_V1 (T-47 / F6 — Michael 2026-08-19, re-confirmed 08-20).

    True while the published live label is PRE-IB-LOCK, i.e. provisional: the
    Market Profile foundation it reasons from is not formed yet, so the label is a
    working hypothesis and must never masquerade as settled.

    This does NOT suppress the label (see get_live_day_type). It marks it, and the
    gates that VETO on day type degrade that veto to advisory — reusing the
    existing `conf < DAYTYPE_PLAYBOOK_MIN_CONF (0.4)` degrade path
    (`trading_gateway._daytype_conf_sufficient`, `setup_emitter` AUTH_LOWCONF_REDUCED)
    rather than inventing a second notion of "untrustworthy label".

    Default OFF → always False → byte-identical.
    Fail-safe: any error → False (a bug must never degrade a gate).
    """
    import os as _os
    if _os.getenv("DAYTYPE_HONEST_PRELOCK_V1", "").lower() not in ("1", "true", "yes"):
        return False
    try:
        _dtm = _live_day_type_machine()
        if _dtm is None:
            return False
        return not bool(getattr(_dtm, "ib_locked", False))
    except Exception:
        return False


def get_live_day_type() -> Optional[str]:
    """Read the LIVE promoted 7-type day_type from app.state.day_type_machine.

    This is the SAME source Woodies V2Sizing uses — promoted instantly by
    _day_type_on_bar, no DB lag, no cache. Returns the mapped day_type string
    (e.g. "Trend_Normal", "Variation") or None if unavailable/UNKNOWN/FORMING.
    Gated by DAYTYPE_GATE_LIVE_V1 flag; returns None when OFF.
    Fail-safe: any error → None.
    """
    import os as _os
    # ── DAY_TYPE_MANUAL_OVERRIDE (Michael live ruling 2026-07-16 21:20 "היום
    # הפך ליום נייטרלי" · dev directive SYNC-21:35): date-scoped manual label,
    # format "YYYY-MM-DD:Label". Applies ONLY while today (ET) equals the date
    # → auto-expires at the ET day roll; any other date is inert. Overrides
    # machine+antiflap (Michael IS the S1 authority until N1 lands).
    # Fail-safe: malformed/error → ignored.
    _ovr = _os.getenv("DAY_TYPE_MANUAL_OVERRIDE", "").strip()
    if _ovr and ":" in _ovr:
        try:
            from datetime import datetime as _ovr_dt
            from zoneinfo import ZoneInfo as _ovr_zi
            _ovr_date, _ovr_label = _ovr.split(":", 1)
            if (_ovr_label.strip()
                    and _ovr_date.strip() == _ovr_dt.now(_ovr_zi("America/New_York")).date().isoformat()):
                return _ovr_label.strip()
        except Exception:
            pass
    if _os.getenv("DAYTYPE_GATE_LIVE_V1", "").lower() not in ("1", "true", "yes"):
        return None
    try:
        # The RUNNING app's machine (dead-wrapper trap — see _live_day_type_machine).
        _dtm = _live_day_type_machine()
        _mapped = None
        if _dtm:
            _raw = getattr(_dtm, "day_type", None)
            _val = _raw.value if hasattr(_raw, "value") else (str(_raw) if _raw else None)
            if _val and _val not in ("UNKNOWN", "None", "INDETERMINATE", "FORMING"):
                _mapped = {"Normal_Variation": "Variation"}.get(_val, _val)
            # ── N1c (2026-07-17): before the IB locks (~60min/12 bars), `.day_type`
            # can still hold the OLD base engine's own low-confidence read (e.g.
            # "Trend_Normal" 0.35 seen live 07-15/07-16 at ~10:00 ET) — that value is
            # NOT in the excluded-string list above, so it passes through this
            # function looking exactly like a canonical verdict.
            #
            # T-47 / F6 (Michael 2026-08-19, re-confirmed 08-20) REPLACES the original
            # remedy, which returned None pre-lock. That was measured wrong TWICE on
            # the same live day: on 2026-07-20 Michael turned `S2_DETECTION_LIVE_DAYTYPE_V1`
            # off at 10:58 ET and `S4_HONEST_DAYTYPE_FALLBACK_V1` off at 10:10 ET, because
            # a null label pre-lock made S2 skip every setup and S4 skip a classified
            # down-day — a first-hour dead zone (both notes in config/RULED_FLAGS.yaml).
            # Suppressing the label costs trades. The ruled remedy keeps publishing it
            # and marks it PROVISIONAL via daytype_is_provisional(), so a pre-lock label
            # can inform but cannot VETO — degraded by the consumers through the
            # existing conf<0.4 path. Nothing to do here: the label flows unchanged.
        # ── anti-flap (DAYTYPE_ANTIFLAP_V1, Michael 2026-07-09): a live CHANGE must persist
        #    >= hold before it reaches the gates. Default OFF → returns the raw mapped value
        #    unchanged (byte-identical). The classify_replay engine is NOT touched. ──
        if _os.getenv("DAYTYPE_ANTIFLAP_V1", "").lower() in ("1", "true", "yes"):
            import time as _time
            _hold = float(_os.getenv("DAYTYPE_ANTIFLAP_HOLD_S", "300"))  # ~1 bar; set 600 for strict 2-bar
            return _antiflap_day_type(_mapped, _time.time(), _hold, _ANTIFLAP_STATE)
        return _mapped
    except Exception:
        pass
    return None


def _g1_replay_fallback_ok() -> bool:
    """classify_replay fallback allowed ONLY outside the live session (ET h>=16 or h<9).

    Michael URGENT root-fix (2026-07-16 ~19:15, live directive): classify_replay
    computes `final` with is_eod=True — on a PARTIAL day it FORCES a terminal
    label (e.g. "Neutral_Center" on a two-sided range day), which fed the
    playbook/location gates an invented label mid-session (wrong blocks; the
    #28 ladder clamp). Post-close / pre-open analytics may still use it.
    Fail-safe: clock error → False (never force a label).
    """
    try:
        from datetime import datetime as __dt
        from zoneinfo import ZoneInfo as __zi
        _h = __dt.now(__zi("America/New_York")).hour
        return _h >= 16 or _h < 9
    except Exception:
        return False


def extract_g1_entry_context(cross_context: Any) -> Dict[str, Optional[str]]:
    """G1: Extract day_type, pattern_id, session from cross_context at entry.

    Uses the SAME extraction paths as extract_trade_display to ensure the
    promoted columns match what the UI shows. Silent → None (Rule 1).
    """
    systems_map = _systems_blob_at_entry(cross_context)

    # day_type_at_entry: from day_type_machine (the OLD live engine)
    day_type_blob = systems_map.get("day_type_machine") or {}
    day_type = (
        day_type_blob.get("day_type")
        or day_type_blob.get("state")
        or None
    )
    if day_type and day_type == "UNKNOWN":
        day_type = None

    # ── S1 PROMOTION (flag S1_NEW_CLASSIFIER, Michael 2026-06-20) ──────────────────────────────
    # When ON, the day_type that gates the trade + stamps the row comes from the NEW validated
    # state-machine classifier (7 types) instead of the old DECISION_MATRIX (3 types). Fully
    # FAIL-SAFE: any error / no-bars / FORMING → keep the old engine's value above (never blocks a
    # fire). Enum mapped to the playbook (`Normal_Variation`→`Variation`). Cached ~30s.
    import os as _os
    if _os.getenv("S1_NEW_CLASSIFIER", "").lower() in ("1", "true", "yes"):
        try:
            # ── DAYTYPE_GATE_LIVE_V1: read the LIVE in-memory promoted attribute first ──
            # Uses the shared get_live_day_type() helper (single source of truth).
            # I-44/I-50 fix: the old classify_replay path lagged the live engine.
            _live_dt = get_live_day_type()

            if _live_dt:
                day_type = _live_dt
            elif _g1_replay_fallback_ok():
                # Fallback: classify_replay (DB-based, 30s cache) — the old path.
                # Michael root-fix 07-16: gated to OUTSIDE the live session only
                # (see _g1_replay_fallback_ok). Mid-session with live-None the
                # day_type stays None — gates fail-OPEN on unclassified instead
                # of fail-WRONG on an is_eod-forced label.
                import time as _t
                import datetime as _dt
                from zoneinfo import ZoneInfo as _ZI
                _today = _dt.datetime.now(_ZI("America/New_York")).date().isoformat()
                if _NC_CACHE.get("date") != _today or (_t.time() - _NC_CACHE.get("ts", 0.0)) > 30:
                    from backend.v9.api.v9.daytype_classify_routes import classify_replay as _cr
                    _final = (_cr(_today) or {}).get("final") or {}
                    _NC_CACHE.update({"date": _today, "ts": _t.time(), "day_type": _final.get("day_type")})
                _ndt = _NC_CACHE.get("day_type")
                if _ndt and _ndt != "FORMING":
                    day_type = {"Normal_Variation": "Variation"}.get(_ndt, _ndt)
                elif _ndt == "FORMING" and _os.getenv("OPENING_FIRE_CVD_V1", "").lower() in ("1", "true", "yes"):
                    day_type = None
        except Exception:
            pass  # fail-safe — keep the old engine's day_type set above

    # pattern_id_at_entry: from woodies_system active_patterns or quality
    woodies_blob = systems_map.get("woodies_system") or {}
    pattern_id = None
    ap = woodies_blob.get("active_patterns")
    if isinstance(ap, list) and ap and isinstance(ap[0], dict):
        pattern_id = ap[0].get("pattern_id") or ap[0].get("pattern")
    if not pattern_id:
        pattern_id = woodies_blob.get("classification") or woodies_blob.get("signal")
    if pattern_id and pattern_id in ("STRATEGIC", "TACTICAL", "NO_SETUP"):
        pattern_id = None

    # session_at_entry: from killzone_system zone, with fallback to
    # time-based session computation when the killzone blob is empty
    # (the blob has been empty on all 47 recent trades — the killzone
    # system doesn't write to systems_map).
    killzone_blob = systems_map.get("killzone_system") or {}
    session = _snapshot_hint(6, killzone_blob)  # returns zone or state
    if session is None:
        # Fallback: compute session from wall clock (IL time)
        try:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            _il = datetime.now(ZoneInfo("Asia/Jerusalem"))
            _h = _il.hour
            if 16 <= _h < 17:
                session = "OPENING"
            elif 17 <= _h < 18:
                session = "AM_SESSION"
            elif 18 <= _h < 20:
                session = "MIDDAY"
            elif 20 <= _h < 23:
                session = "PM_SESSION"
            else:
                session = "OFF_HOURS"
        except Exception:
            pass

    return {
        "day_type_at_entry": str(day_type)[:20] if day_type else None,
        "pattern_id_at_entry": str(pattern_id)[:40] if pattern_id else None,
        "session_at_entry": str(session)[:20] if session else None,
    }


def extract_trade_display(trade) -> Dict[str, Any]:
    """Build API/journal fields: PnL, pattern, trigger, day type, system hints."""
    quality = trade.quality if isinstance(trade.quality, dict) else {}
    meta = quality.get("metadata") if isinstance(quality.get("metadata"), dict) else {}
    cross = trade.cross_context

    entry_row = {}
    if isinstance(cross, list):
        for item in cross:
            if isinstance(item, dict) and (
                item.get("classification") or item.get("trigger") or item.get("systems")
            ):
                entry_row = item
                break

    woodies = _system_state(cross, "woodies_system")
    footprint = _system_state(cross, "footprint_system")
    day_type = _system_state(cross, "day_type_machine")

    classification = (
        quality.get("classification")
        or entry_row.get("classification")
        or footprint.get("last_classification")
        or woodies.get("classification")
        or meta.get("pattern")
        or meta.get("signal")
        or ""
    )
    trigger = (
        quality.get("trigger")
        or entry_row.get("trigger")
        or footprint.get("last_pattern")
        or classification
        or f"S{trade.firing_system}"
    )

    pattern_id = (
        meta.get("pattern")
        or meta.get("signal")
        or (classification if classification and classification not in ("STRATEGIC", "TACTICAL", "NO_SETUP") else None)
    )

    pattern_detail = pattern_id or woodies.get("signal") or footprint.get("last_pattern")
    if not pattern_detail and woodies.get("active_patterns"):
        ap = woodies["active_patterns"]
        if isinstance(ap, list) and ap:
            best = max(ap, key=lambda p: (p.get("confidence") or 0) if isinstance(p, dict) else 0)
            pattern_detail = best.get("pattern_id") if isinstance(best, dict) else None

    day_type_label = (
        day_type.get("day_type")
        or day_type.get("state")
        or woodies.get("day_type")
        or "UNKNOWN"
    )

    blocked = meta.get("blocked_by") or quality.get("blocked_by")
    confidence = quality.get("confidence")

    return {
        "pattern_id": pattern_detail,
        "pattern_group": meta.get("group") or woodies.get("classification"),
        "trigger": str(trigger),
        "classification": str(classification) if classification else None,
        "confidence": confidence,
        "firing_system": trade.firing_system,
        "pnl_usd": trade.pnl_usd,
        "pnl_r": trade.pnl_r,
        "outcome": trade.outcome,
        "exit_reason": trade.exit_reason,
        "state": trade.state,
        "day_type": day_type_label,
        "woodies_trend": woodies.get("trend_state"),
        "footprint_classification": footprint.get("last_classification"),
        "footprint_confluence": footprint.get("last_confluence"),
        "blocked_by": blocked,
        "metadata": meta,
    }


def get_live_expansion():
    """07-15 (Michael: 'לוודא שהמערכת תדע לזהות הרחבה') — the CANONICAL live
    expansion signal: the classifier's volume-accepted reference break
    (P0-1-v2: IB / PDH / PDL / prior-VA), promoted per bar into
    app.state.last_cls_result. Returns {"dir": "UP"|"DOWN", "ref": str} or
    None when no accepted expansion exists right now (honest None — the LSMA
    color proxy in require_with_trend stays as fallback, never replaced here).

    S1_DAY_DIRECTION_V1 (cowork 2026-08-25) — ROOT FIX, flag-gated, default OFF.

    The `backend.v9.app` module resolved below is a DIFFERENT FastAPI object from
    the one that actually runs. The single writer of `last_cls_result` is
    `backend/main.py:674` (`app.state.last_cls_result = _cls_result`) on
    `backend.main.app`. So `backend.v9.app.state.last_cls_result` is NEVER set →
    this function returned None on every call → priority-1 of the gateway
    `day_direction` chain (`trading_gateway.py:1234-1239`) was dead code, and
    day_direction always fell through to `get_live_dir_bias` (LSMA 60%-majority
    over 6 Woodies bars = 30 min of lag). System-1 computed the Dalton IB-expansion
    direction and the gateway never received it.

    The correct resolution already exists twice in this repo — `trading_gateway.
    _resolve_live_cls()` (line 195) and `daytype_watchdog._resolve_app_state()` —
    both of which import `backend.main`. When `S1_DAY_DIRECTION_V1` is ON this
    function uses that same resolution; when OFF it is byte-identical to the
    pre-existing (dead) behaviour, so enabling is the only thing that can change
    a verdict.

    NO confidence percentages at any stage (Michael ruling: Dalton is binary).
    Fail-safe: any exception → None → the existing fallback chain continues
    untouched.
    """
    import os as _os
    _mode = _os.getenv("S1_DAY_DIRECTION_V1", "0").strip().lower()
    # shadow (Michael 2026-08-25 15:55: "אפשר להפעיל בשדואו ולראות מה זה ייתן"):
    # resolve the LIVE app and LOG what the fix WOULD return — then return the
    # legacy value anyway. Byte-identical behaviour, real evidence from bar one.
    # Michael's read of today's three failures — "they weren't built right" — is
    # exactly why: each was enabled on reasoning instead of on measurement.
    _shadow = _mode == "shadow"
    # T-37 (Michael 28.08): "apply" = live direction from System-1/IB.
    # LSMA demoted to tiebreaker only. None early = UNDETERMINED (no veto).
    _flag_on = _mode in ("1", "true", "yes", "on", "apply")
    try:
        import importlib as _il
        if _flag_on:
            # The app that actually runs and actually gets written to.
            _app = _il.import_module("backend.main").app
            _src = "backend.main"
        else:
            # Legacy (dead) path — preserved byte-for-byte while the flag is OFF.
            _app = _il.import_module("backend.v9.app").app
            _src = "backend.v9.app"
        if _shadow:
            # Observation only — never touches the returned value below.
            try:
                _sapp = _il.import_module("backend.main").app
                _sres = getattr(_sapp.state, "last_cls_result", None) or {}
                _sd = _sres.get("accepted_break") or _sres.get("break_dir")
                import logging as _slg
                _slog = _slg.getLogger(__name__)
                # Source B — v9_day_type_state.direction. RICHER than
                # accepted_break: it carries the Dalton INSTRUCTION, not just a
                # side. Observed values 2026-08-25: with_extension(UP|DOWN) =
                # one-sided IB extension → trend day, trade WITH; fade_both(
                # UP|DOWN) = both sides broke → balance day, FADE both edges.
                # 13 of 26 rows are fade_both, so a plain UP/DOWN from
                # accepted_break would tell the gateway "go with DOWN" on half
                # the sessions where System-1 actually says "fade both extremes".
                # Log both so tonight shows where they disagree — that
                # disagreement is the whole decision.
                _sdb = _sdb_raw = None
                try:
                    from backend.v9.db.read import read_one as _s_read
                    _srow = _s_read(
                        "SELECT direction FROM v9_day_type_state "
                        "ORDER BY id DESC LIMIT 1", {})
                    _sdb_raw = (_srow or {}).get("direction")
                    if _sdb_raw:
                        _t = str(_sdb_raw)
                        if _t.startswith("with_extension("):
                            _sdb = "UP" if "UP" in _t else "DOWN"
                        elif _t == "with_extension":
                            # Phase 3 fix: bare with_extension without
                            # parentheses/direction — UNDETERMINED (we know
                            # it's a trend day but not which direction).
                            _sdb = "UNDETERMINED"
                        elif _t.startswith("fade_both("):
                            # Balance day: NO directional requirement.
                            _sdb = "UNDETERMINED"
                        elif _t == "fade_both":
                            _sdb = "UNDETERMINED"
                except Exception:
                    pass
                _slog.info(
                    "[S1DayDir] SHADOW accepted_break=%s | s1_state=%s→%s | "
                    "agree=%s (live returns legacy None → LSMA fallback)",
                    _sd if _sd in ("UP", "DOWN") else "none",
                    _sdb_raw or "none", _sdb or "none",
                    "n/a" if (_sdb is None or _sd not in ("UP", "DOWN"))
                    else str(_sd == _sdb),
                )
            except Exception as _serr:  # never raises into the trading path
                import logging as _slg2
                _slg2.getLogger(__name__).warning(
                    "[S1DayDir] shadow probe failed (fail-open): %s", _serr)
        _res = getattr(_app.state, "last_cls_result", None) or {}
        _d = _res.get("accepted_break") or _res.get("break_dir")
        if _d in ("UP", "DOWN"):
            _ref = _res.get("accepted_break_ref") or _res.get("reclass_ref") or "?"
            if _flag_on:
                import logging as _lg
                _lg.getLogger(__name__).info(
                    "[S1DayDir] day_direction=%s ref=%s src=%s.app.state.last_cls_result",
                    _d, _ref, _src,
                )
            return {"dir": _d, "ref": _ref}
        # T-37: when flag is ON and S1 has no direction yet (early session,
        # before IB expansion), return UNDETERMINED — not None. None falls
        # through to the LSMA fallback which vetoes wrong-side on stale data.
        # UNDETERMINED = "no opinion yet" = NO directional veto (binary doctrine:
        # absence of knowledge ≠ veto).
        if _flag_on:
            # Also check v9_day_type_state for the Dalton instruction
            try:
                from backend.v9.db.read import read_one as _s_read
                # T-37 fix #5 (cowork 29.08): add date filter + freshness
                # check. Without it, Monday morning returns Friday's row.
                _srow = _s_read(
                    "SELECT direction FROM v9_day_type_state "
                    "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
                    "(now() AT TIME ZONE 'America/New_York')::date "
                    "ORDER BY id DESC LIMIT 1", {})
                _sdb_raw = (_srow or {}).get("direction")
                if _sdb_raw:
                    _t = str(_sdb_raw)
                    if _t.startswith("with_extension("):
                        _sdb = "UP" if "UP" in _t else "DOWN"
                        import logging as _lg2
                        _lg2.getLogger(__name__).info(
                            "[S1DayDir] T-37 from v9_day_type_state: %s → %s",
                            _t, _sdb)
                        return {"dir": _sdb, "ref": f"v9_day_type_state:{_t}"}
                    elif _t.startswith("fade_both"):
                        # Balance day: NO directional requirement
                        return {"dir": "UNDETERMINED", "ref": f"v9_day_type_state:{_t}"}
            except Exception:
                pass
            import logging as _lg3
            _lg3.getLogger(__name__).info(
                "[S1DayDir] T-37 UNDETERMINED: S1 has no direction yet "
                "(early session / no IB break) — no directional veto")
            return {"dir": "UNDETERMINED", "ref": "s1_not_ready"}
    except Exception:
        pass
    return None


def get_live_dir_bias(window: int = 6, min_frac: float = 0.6):
    """HELD directional bias from the LSMA trend color over the last ``window``
    Woodies bars (RED→DOWN, BLUE→UP; GRAY ignored). Returns "UP" / "DOWN" only on
    a strong majority (>= min_frac of the decisive bars agree, >= 3 decisive bars,
    and a strict plurality), else None.

    This is the robust day-direction source for RESPONSIVE_WITH_DAY_TREND_V1
    (Michael ruling 2026-07-23). It is deliberately NOT the momentary
    ``trend_state`` — that blips GRAY at a pullback (observed 07-23 16:45, the
    exact bar the with-trend SHORT was needed) which the playbook must not read
    as "no trend". A held window survives the blip: 07-23 was RED on ~11 of the
    last 12 bars → DOWN. Used only as a fallback when get_live_expansion() has no
    volume-accepted break. Read-only; fail-closed to None on any error."""
    try:
        from backend.v9.db.read import read_all
        rows = read_all(
            "SELECT trend_state FROM v9_bars_5min_woodies ORDER BY ts DESC LIMIT :n",
            {"n": int(window)},
        )
        colors = [str((r or {}).get("trend_state") or "").upper() for r in rows]
        red = sum(1 for c in colors if c == "RED")
        blue = sum(1 for c in colors if c == "BLUE")
        decisive = red + blue
        if decisive >= 3:
            if red > blue and red >= min_frac * decisive:
                return "DOWN"
            if blue > red and blue >= min_frac * decisive:
                return "UP"
    except Exception:
        pass
    return None


def get_opening_type_seed():
    """OPENING_TYPE_SEEDS_S1_V1 — directional bias from opening-type classification.

    Within the first 15 minutes of RTH (3 bars), if the opening type indicates
    a directional open (OPEN_DRIVE, OPEN_TEST_DRIVE) or a clear reversal,
    seed a directional bias:
      OPEN_DRIVE UP / OPEN_TEST_DRIVE UP → "UP"
      OPEN_DRIVE DOWN / OPEN_TEST_DRIVE DOWN → "DOWN"
      OPEN_REJECTION_REVERSE direction → the REVERSAL direction
      OPEN_AUCTION_* → None (no directional seed)

    The seed is escalation-only: once set, it can only strengthen but never
    flip (UP→DOWN) until IB-lock. This prevents the day-type flapping
    observed on 07-23 (8× flips in 90min).

    Returns "UP" / "DOWN" / None. Flag-gated; fail-closed to None.
    """
    import os
    if os.getenv("OPENING_TYPE_SEEDS_S1_V1", "0").lower() not in ("1", "true", "yes"):
        return None
    try:
        from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type
        from backend.v9.db.read import read_all, read_one
        from backend.v9.services.market_clock import now_et, get_previous_trading_day

        et = now_et()
        from datetime import time as _time
        # Only seed in the first 15 minutes of RTH (09:30-09:45 ET)
        if et.time() < _time(9, 30) or et.time() >= _time(9, 45):
            return None

        bars_rows = read_all(
            "SELECT ts, open, high, low, close, volume "
            "FROM v9_bars_5min_woodies "
            "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
            "(now() AT TIME ZONE 'America/New_York')::date "
            "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
            "ORDER BY ts ASC LIMIT 3",
            {},
        )
        if not bars_rows:
            return None

        def _f(v):
            return float(v) if v is not None else None
        rth_bars = [
            {"o": _f(r["open"]), "h": _f(r["high"]), "l": _f(r["low"]),
             "c": _f(r["close"]), "v": _f(r.get("volume"))}
            for r in bars_rows
        ]
        open_price = rth_bars[0]["o"]

        prev_date = get_previous_trading_day()
        prev_row = read_one(
            "SELECT vah_price, val_price FROM v9_tpo_sessions "
            "WHERE trading_date = :prev_date AND session_type = 'CASH' "
            "ORDER BY id DESC LIMIT 1",
            {"prev_date": prev_date.isoformat()},
        )
        prev_vah = float(prev_row["vah_price"]) if prev_row and prev_row.get("vah_price") else None
        prev_val = float(prev_row["val_price"]) if prev_row and prev_row.get("val_price") else None

        result = detect_opening_type(
            rth_bars, open_price, prior_vah=prev_vah, prior_val=prev_val,
        )
        otype = result.get("opening_type")
        direction = result.get("direction")

        if otype in ("OPEN_DRIVE", "OPEN_TEST_DRIVE", "OPEN_REJECTION_REVERSE"):
            if direction in ("UP", "DOWN"):
                return direction
        return None
    except Exception:
        return None


def get_opening_dir_fusion(oe_bars):
    """OPENING_DIR_FUSION_V1 — volume-confirmed opening direction (empirical study
    2026-07-24, docs/reports/OPENING_SIGNAL_EDGE: 73% on the days it fires vs the
    classifier's 53%). Fetches the trailing-median opening (first-30-min) volume + the
    prior-day reference levels, then calls opening_entry.opening_dir_fusion over the
    caller's first-6 RTH bars. Returns 'UP'/'DOWN'/None (None = low-conviction/auction or
    a level-break that conflicts with momentum → no opening trade). Flag-gated;
    fail-closed to None."""
    import os
    if os.getenv("OPENING_DIR_FUSION_V1", "0").lower() not in ("1", "true", "yes"):
        return None
    try:
        from backend.v9.systems.opening_entry import opening_dir_fusion
        from backend.v9.db.read import read_scalar, read_one
        from backend.v9.services.market_clock import get_previous_trading_day
        if not oe_bars or len(oe_bars) < 6:
            return None
        b6 = oe_bars[:6]

        def _f(v):
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        def _bg(b, *keys):
            for k in keys:
                v = b.get(k) if isinstance(b, dict) else getattr(b, k, None)
                if v is not None:
                    return v
            return None

        open_price = _f(_bg(b6[0], "o", "open"))

        # T7 ROOT-FIX 2026-08-15 — the gate had passed 0/8 times, ever.
        # MEASURED, not theorised: 08-14 the fusion computed opening_vol=2,212
        # against median=114,590 and logged "auction/low-conviction"; the
        # canonical table says that morning's first six RTH bars traded 89,246.
        # The 40× gap is a UNIT MISMATCH, not a quiet market: the bars handed to
        # S2 are `current_bar` snapshots (bars.py routing override — deliberate,
        # it carries live study values), so each one holds the volume accrued in
        # the first seconds of its 5-minute window. Comparing a partial-bar sum
        # to a full-bar median can only ever say "too quiet", which is why the
        # gate silently dropped 8/8 opening candidates (08-13 DRIVE LONG ×5,
        # 08-14 ORR LONG + DRIVE SHORT ×2 — the 08-14 pair alone was +$227.50).
        # Both sides of the comparison must come from the same measure, so the
        # opening volume is read from the canonical CLOSED bars — the same table
        # and the same first-6 window the median is built from. Fewer than six
        # closed bars → None (honest unknown, Rule 1: never a partial sum
        # dressed up as a full one).
        _ov = read_scalar(
            "SELECT sum(volume) FROM ("
            "  SELECT volume, row_number() OVER (ORDER BY ts) rn "
            "  FROM v9_bars_5min_woodies WHERE symbol='MES' "
            "  AND (ts AT TIME ZONE 'America/New_York')::date = "
            "      (now() AT TIME ZONE 'America/New_York')::date "
            "  AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
            "  AND (ts AT TIME ZONE 'America/New_York')::time < '16:00' "
            "  AND ts <= now() - interval '5 minutes' "
            ") x WHERE rn <= 6", {})
        _n_closed = read_scalar(
            "SELECT count(*) FROM v9_bars_5min_woodies WHERE symbol='MES' "
            "AND (ts AT TIME ZONE 'America/New_York')::date = "
            "    (now() AT TIME ZONE 'America/New_York')::date "
            "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
            "AND ts <= now() - interval '5 minutes'", {})
        if not _n_closed or int(_n_closed) < 6:
            return None
        opening_vol = _f(_ov)
        med = read_scalar(
            "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY ov) FROM ("
            "  SELECT d, sum(volume) ov FROM ("
            "    SELECT (ts AT TIME ZONE 'America/New_York')::date d, volume, "
            "           row_number() OVER (PARTITION BY (ts AT TIME ZONE 'America/New_York')::date ORDER BY ts) rn "
            "    FROM v9_bars_5min_woodies WHERE symbol='MES' "
            "    AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
            "    AND (ts AT TIME ZONE 'America/New_York')::time < '16:00' "
            "    AND (ts AT TIME ZONE 'America/New_York')::date < current_date "
            "  ) x WHERE rn <= 6 GROUP BY d "
            ") y", {})
        prev = get_previous_trading_day()
        pdh = pdl = pvah = pval = None
        if prev is not None:
            _p = prev.isoformat() if hasattr(prev, "isoformat") else str(prev)
            hl = read_one(
                "SELECT max(high) AS h, min(low) AS l FROM v9_bars_5min_woodies "
                "WHERE symbol='MES' AND (ts AT TIME ZONE 'America/New_York')::date = :d "
                "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
                "AND (ts AT TIME ZONE 'America/New_York')::time < '16:00'", {"d": _p})
            if hl:
                pdh, pdl = _f(hl.get("h")), _f(hl.get("l"))
            pv = read_one(
                "SELECT vah_price AS vah, val_price AS val FROM v9_tpo_sessions "
                "WHERE trading_date = :d ORDER BY id DESC LIMIT 1", {"d": _p})
            if pv:
                pvah, pval = _f(pv.get("vah")), _f(pv.get("val"))
        return opening_dir_fusion(b6, open_price, opening_vol, _f(med),
                                  pdh=pdh, pdl=pdl, prior_vah=pvah, prior_val=pval)
    except Exception:
        return None
