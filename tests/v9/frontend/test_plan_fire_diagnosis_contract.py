"""P30.10b — Plan tab BLOCKED chain contract (mirrors planFireDiagnosis + systemPlanLive)."""

from __future__ import annotations

# Keep in sync with planFireDiagnosis.ts / systemPlanLive.tsx
LIFECYCLE_RANK = {
    "SCANNING": 0,
    "APPROACHING": 1,
    "READY": 2,
    "FIRING": 3,
    "BLOCKED": 4,
}


def max_lifecycle(a: str, b: str) -> str:
    return a if LIFECYCLE_RANK[a] >= LIFECYCLE_RANK[b] else b


def diagnose_firing_s2_s3(system_id: int, raw: dict) -> tuple[str, str]:
    """Minimal mirror of diagnoseFiringSystem for S2/S3 BLOCKED paths."""
    if system_id == 2:
        mode = str(raw.get("mode") or "")
        if mode in ("MAINTENANCE", "WEEKEND", "OVERNIGHT_MODE"):
            return "GATEWAY_BLOCK", f"חסום · {mode}"

    failed = raw.get("last_fire") or {}
    if failed.get("blocked_by"):
        return "TREE_FAIL", f"חסום · {failed['blocked_by']}"

    pattern = raw.get("last_pattern") or raw.get("combined_class")
    return ("PATTERN_WAIT" if pattern else "NO_SETUP", str(pattern) if pattern else "אין תבנית")


def lifecycle_from_situation(situation: str, health: str) -> str:
    if health == "error":
        return "BLOCKED"
    if situation in ("ROUTED_SHADOW", "ROUTED_DEMO", "ROUTED_LIVE"):
        return "FIRING"
    if situation == "TREE_READY":
        return "READY"
    if situation in ("TREE_FAIL", "GATEWAY_BLOCK", "NO_GATEWAY"):
        return "BLOCKED"
    if situation in ("PATTERN_WAIT", "TREE_PENDING"):
        return "APPROACHING"
    return "SCANNING"


def plan_lifecycle_s2(raw: dict, health: str) -> str:
    if health == "error":
        return "BLOCKED"
    mode = str(raw.get("mode") or "")
    if mode in ("MAINTENANCE", "WEEKEND", "OVERNIGHT_MODE"):
        return "BLOCKED"
    if raw.get("last_pattern"):
        return "READY"
    if mode in ("FIRST_HOUR_TACTICAL", "DAY_TYPE_MODE"):
        return "APPROACHING"
    return "SCANNING"


def plan_lifecycle_s3(raw: dict, health: str) -> str:
    if health == "error":
        return "BLOCKED"
    last_fire = raw.get("last_fire") or {}
    if last_fire.get("blocked_by"):
        return "BLOCKED"
    if str(raw.get("combined_class") or "NO_SETUP") != "NO_SETUP":
        return "APPROACHING"
    return "SCANNING"


def merged_lifecycle(system_id: int, raw: dict, health: str = "healthy") -> str:
    plan = plan_lifecycle_s2(raw, health) if system_id == 2 else plan_lifecycle_s3(raw, health)
    situation, _badge = diagnose_firing_s2_s3(system_id, raw)
    diag = lifecycle_from_situation(situation, health)
    return max_lifecycle(plan, diag)


def test_s2_maintenance_stays_blocked_not_scanning():
    raw = {"mode": "MAINTENANCE", "buffer_size": 0}
    assert merged_lifecycle(2, raw) == "BLOCKED"


def test_s2_overnight_mode_is_blocked_not_scanning():
    """S2 spec: OVERNIGHT_MODE must map to BLOCKED, not SCANNING (AGENT_S2 SHOULD_BLOCK)."""
    raw = {"mode": "OVERNIGHT_MODE", "buffer_size": 307}
    assert merged_lifecycle(2, raw) == "BLOCKED"


def test_s2_weekend_is_blocked():
    raw = {"mode": "WEEKEND", "buffer_size": 0}
    assert merged_lifecycle(2, raw) == "BLOCKED"


def test_s3_last_fire_blocked_stays_blocked_with_pattern():
    raw = {
        "combined_class": "ABSORPTION",
        "last_fire": {"blocked_by": "killzone", "route_reason": "gate closed"},
    }
    assert merged_lifecycle(3, raw) == "BLOCKED"


def test_s3_pattern_without_block_is_approaching():
    raw = {"combined_class": "ABSORPTION"}
    assert merged_lifecycle(3, raw) == "APPROACHING"
