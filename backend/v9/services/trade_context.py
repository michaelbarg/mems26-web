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
