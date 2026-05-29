"""P31.1-T5: compliance_manifest.yaml lock_state enum includes all consumer statuses."""
import yaml
from pathlib import Path


def test_lock_state_enum_covers_consumer_statuses():
    """The lock_state enum in compliance_manifest.yaml must include every
    status string DayTypeConsumer may write."""
    manifest_path = Path(__file__).parent.parent.parent.parent.parent / \
        "backend/v9/systems/day_type/compliance_manifest.yaml"
    if not manifest_path.exists():
        # Manifest is optional — skip if not present
        import pytest
        pytest.skip("compliance_manifest.yaml not found")

    with manifest_path.open() as f:
        data = yaml.safe_load(f)

    # Find lock_state enum — walk all lists looking for name=lock_state
    lock_states = set()
    def _walk(obj):
        if isinstance(obj, dict):
            if obj.get("name") == "lock_state" and "enum" in obj:
                lock_states.update(obj["enum"])
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)
    _walk(data or {})

    # These are the statuses DayTypeConsumer._map_legacy_status may write
    required = {"LOCKED", "LOCKED_LOW_CONF", "PENDING", "DEVELOPING", "ROLLED_OVER"}
    missing = required - lock_states
    assert not missing, f"compliance_manifest.yaml lock_state missing: {missing}"
