"""Stop buffer = 6 ticks beyond structure — Michael ruling 2026-07-20 (was 3T).

The protective offset was fragmented across three sites (config YAML, the
resolve_stop default param, and a hardcoded 3*TICK in the ZLR-confluence path).
Michael ruled it widened to 6T (fewer false stop-outs). These pins guard every
site so the value cannot silently drift back or diverge between paths.
"""
import inspect

from backend.v9.systems.stop_anchors import stop_resolver
from backend.v9.systems.confluence import confluence_ri_zlr as C


def test_resolve_stop_default_offset_is_6t():
    """stop_resolver.resolve_stop default offset_ticks == 6 (was 3)."""
    sig = inspect.signature(stop_resolver.resolve_stop)
    assert sig.parameters["offset_ticks"].default == 6


def test_confluence_zlr_signal_bar_uses_6t():
    """ZLR-confluence structural stop = signal-bar extreme ± 6T (was 3T).

    entry 7400 LONG, signal-bar low 7398 → raw = 7398 - 6*0.25 = 7396.5,
    risk 3.5pt (inside [floor, cap]) → stop 7396.5, src labelled *_6t.
    """
    bars = [{"low": 7398.0, "high": 7402.0}]
    stop, src = C._resolve_stop("LONG", 7400.0, {}, bars)
    assert src == "signal_bar_extreme_6t"
    assert stop == 7396.5

    # SHORT mirror: entry 7400, signal-bar high 7402 → raw = 7402 + 6*0.25 = 7403.5
    bars_s = [{"low": 7398.0, "high": 7402.0}]
    stop_s, src_s = C._resolve_stop("SHORT", 7400.0, {}, bars_s)
    assert src_s == "signal_bar_extreme_6t"
    assert stop_s == 7403.5


def test_config_anchor_offset_is_6():
    """config/stop_anchors.yaml anchor_offset_ticks == 6 (the live pattern buffer)."""
    import yaml
    cfg = yaml.safe_load(open("config/stop_anchors.yaml"))
    assert cfg["principles"]["anchor_offset_ticks"] == 6
