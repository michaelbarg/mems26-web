"""narrator_he: 4-line Hebrew narrative in mobile_monitor payload.

Test: given a payload resembling yesterday 17:05, all 4 lines are built.
Missing fields → narrator_he=null (not a crash).
"""
from backend.v9.api.v9.mobile_monitor import _build_narrator_he


def _payload_1705():
    """Simulated payload from 02.09 17:05 IL (RTH open + IB forming)."""
    return {
        "radar": {
            "opening": {"type": "OPEN_DRIVE", "dir": "DOWN", "conf": 0.73},
            "day_type": "Normal",
            "volume_vs_median": 1.4,
            "ib_locked": False,
            "gate": {
                "last": {
                    "pattern": "REACTIVE_SHORT",
                    "blocked_by": "location_gate",
                    "reason": "SHORT at mid_value — wrong location",
                }
            },
        },
        "sierra": {"position_qty": 0},
    }


def test_four_lines_built():
    """All 4 lines present with proper emoji prefixes."""
    result = _build_narrator_he(_payload_1705())
    assert result is not None
    lines = result.strip().split("\n")
    assert len(lines) == 4, f"Expected 4 lines, got {len(lines)}"
    assert lines[0].startswith("🔍")
    assert lines[1].startswith("📖")
    assert lines[2].startswith("🚫")
    assert lines[3].startswith("⏭️")


def test_identification_line():
    """Line 1 contains opening type + confidence + day type."""
    result = _build_narrator_he(_payload_1705())
    line1 = result.split("\n")[0]
    assert "OPEN_DRIVE" in line1
    assert "73%" in line1
    assert "Normal" in line1


def test_dalton_line():
    """Line 2 is the doctrine sentence for OPEN_DRIVE × Normal."""
    result = _build_narrator_he(_payload_1705())
    line2 = result.split("\n")[1]
    assert "📖" in line2
    assert "קצוות" in line2  # "נורמלי עם דרייב — לחכות לקצוות"


def test_blocked_line():
    """Line 3 shows the last blocked candidate."""
    result = _build_narrator_he(_payload_1705())
    line3 = result.split("\n")[2]
    assert "location_gate" in line3
    assert "REACTIVE_SHORT" in line3


def test_missing_radar_returns_string():
    """Empty payload → 4 lines with defaults, not crash."""
    result = _build_narrator_he({})
    assert result is not None
    lines = result.strip().split("\n")
    assert len(lines) == 4


def test_position_line():
    """In position → line 4 shows direction and size."""
    payload = _payload_1705()
    payload["sierra"]["position_qty"] = -3
    result = _build_narrator_he(payload)
    line4 = result.split("\n")[3]
    assert "שורט" in line4
    assert "3" in line4
