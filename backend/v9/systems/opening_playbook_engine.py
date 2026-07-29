"""Opening Playbook Engine — P1 (2026-07-29).

Reads `config/opening_playbook.yaml` and returns the trade template for
the current opening type. The engine is a thin resolver — the actual
entry/stop/target calculations live in opening_entry.py and the gateway.

Flag: OPENING_PLAYBOOK_V1 (default OFF). When OFF, resolve() returns None
and opening_entry.py uses its existing triggers unchanged (byte-identical).

The config defines per-opening-type: entry trigger, stop rule, T1 formula,
runner strategy, invalidation condition, and exempt gates.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from backend.v9.config_loader import _load_yaml

logger = logging.getLogger(__name__)

_cache: Optional[Dict] = None
_loaded = False


@dataclass
class OpeningTemplate:
    opening_type: str
    entry: str
    stop: str
    t1: str
    runner: str
    invalidation: str
    exempt_gates: List[str]


def _flag_on() -> bool:
    return os.getenv("OPENING_PLAYBOOK_V1", "0").lower() in ("1", "true", "yes")


def _cfg() -> Optional[Dict]:
    global _cache, _loaded
    if not _loaded:
        _loaded = True
        _cache = _load_yaml("opening_playbook.yaml")
    return _cache


def reset_cache() -> None:
    """Testing only."""
    global _cache, _loaded
    _cache = None
    _loaded = False


def resolve(opening_type: str) -> Optional[OpeningTemplate]:
    """Return the trade template for the given opening type.

    Returns None when the flag is OFF or the opening type is unknown/unmatched.
    Consumers treat None as "use existing triggers" (fail-open).
    """
    if not _flag_on():
        return None

    cfg = _cfg()
    if not cfg:
        return None

    types = cfg.get("opening_types", {})
    entry = types.get(opening_type)
    if not entry:
        return None

    return OpeningTemplate(
        opening_type=opening_type,
        entry=entry.get("entry", ""),
        stop=entry.get("stop", ""),
        t1=entry.get("t1", "1.5R"),
        runner=entry.get("runner", "none"),
        invalidation=entry.get("invalidation", ""),
        exempt_gates=entry.get("exempt_gates", []),
    )


def is_gate_exempt(opening_type: str, gate_name: str) -> bool:
    """Check if a gate is exempted for the given opening type.

    Used by the gateway to skip awaiting_release/lsma_flat for opening trades.
    Returns False when the flag is OFF (no exemptions — byte-identical).
    """
    tmpl = resolve(opening_type)
    if tmpl is None:
        return False
    return gate_name in tmpl.exempt_gates
