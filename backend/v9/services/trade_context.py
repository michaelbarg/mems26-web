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


def get_live_day_type() -> Optional[str]:
    """Read the LIVE promoted 7-type day_type from app.state.day_type_machine.

    This is the SAME source Woodies V2Sizing uses — promoted instantly by
    _day_type_on_bar, no DB lag, no cache. Returns the mapped day_type string
    (e.g. "Trend_Normal", "Variation") or None if unavailable/UNKNOWN/FORMING.
    Gated by DAYTYPE_GATE_LIVE_V1 flag; returns None when OFF.
    Fail-safe: any error → None.
    """
    import os as _os
    if _os.getenv("DAYTYPE_GATE_LIVE_V1", "").lower() not in ("1", "true", "yes"):
        return None
    try:
        import importlib as _il
        _app_mod = _il.import_module("backend.v9.app").app
        _dtm = getattr(_app_mod.state, "day_type_machine", None)
        _mapped = None
        if _dtm:
            _raw = getattr(_dtm, "day_type", None)
            _val = _raw.value if hasattr(_raw, "value") else (str(_raw) if _raw else None)
            if _val and _val not in ("UNKNOWN", "None", "INDETERMINATE", "FORMING"):
                _mapped = {"Normal_Variation": "Variation"}.get(_val, _val)
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
            else:
                # Fallback: classify_replay (DB-based, 30s cache) — the old path.
                #
                # 07-16 20:55 (Michael command: "תבדוק צינורות מה חסם למה — תתקן"):
                # DURING the session this fallback is FORBIDDEN. classify_replay's
                # `final` is computed with end-of-day semantics — on a PARTIAL day
                # it FORCES a terminal label (yesterday+today: "Neutral_Center"
                # while live said None). That synthesized label fed location_gate/
                # playbook/rr as if S1 had ruled a rotation day → 10 doctrine
                # blocks today on a label S1 never published. This violates
                # Source-of-Truth Rule 1 (silent source ⇒ propagate None, never
                # synthesize). The fallback is now used ONLY after the RTH close
                # (>= 16:00 ET), where `final` semantics are actually valid —
                # e.g. EOD reports. Mid-session live-None stays None and every
                # day-type gate fail-opens by its own design.
                import time as _t
                import datetime as _dt
                from zoneinfo import ZoneInfo as _ZI
                _now_et = _dt.datetime.now(_ZI("America/New_York"))
                if _now_et.hour >= 16 or _now_et.hour < 9:
                    _today = _now_et.date().isoformat()
                    if _NC_CACHE.get("date") != _today or (_t.time() - _NC_CACHE.get("ts", 0.0)) > 30:
                        from backend.v9.api.v9.daytype_classify_routes import classify_replay as _cr
                        _final = (_cr(_today) or {}).get("final") or {}
                        _NC_CACHE.update({"date": _today, "ts": _t.time(), "day_type": _final.get("day_type")})
                    _ndt = _NC_CACHE.get("day_type")
                    if _ndt and _ndt != "FORMING":
                        day_type = {"Normal_Variation": "Variation"}.get(_ndt, _ndt)
                # else: mid-session + live None ⇒ HONEST None (no forced label)
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

    # session_at_entry: from killzone_system zone
    killzone_blob = systems_map.get("killzone_system") or {}
    session = _snapshot_hint(6, killzone_blob)  # returns zone or state

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
    """
    try:
        import importlib as _il
        _app = _il.import_module("backend.v9.app").app
        _res = getattr(_app.state, "last_cls_result", None) or {}
        _d = _res.get("accepted_break") or _res.get("break_dir")
        if _d in ("UP", "DOWN"):
            return {"dir": _d, "ref": _res.get("accepted_break_ref") or _res.get("reclass_ref") or "?"}
    except Exception:
        pass
    return None
