"""T8: Redundancy verification — LaunchAgents + status hook.

Verifies the infrastructure guardrails from CLAUDE.md are in place:
- LaunchAgents use conditional KeepAlive (not KeepAlive=true)
- V9_DISABLE_WATCHDOG exported
- Bridge local-only (CLOUD_URL=localhost)
- /api/v9/admin/services/status endpoint exists

if reverted → RED because: these are infrastructure invariants; the tests
verify the plist files and route registration exist.
"""
import os
from pathlib import Path


def test_bridge_launchagent_conditional_keepalive():
    """Bridge LaunchAgent uses conditional KeepAlive (not KeepAlive=true)."""
    plist = Path.home() / "Library/LaunchAgents/com.mems26.bridge.plist"
    if not plist.exists():
        import pytest
        pytest.skip("bridge plist not found (not on Mac)")
    content = plist.read_text()
    assert "<key>SuccessfulExit</key>" in content, \
        "Bridge plist must use conditional KeepAlive (SuccessfulExit)"
    # Must NOT have a bare <true/> right after KeepAlive (that would be KeepAlive=true)
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "<key>KeepAlive</key>" in line:
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            assert next_line != "<true/>", \
                "Bridge plist has KeepAlive=true — must use conditional dict"
            break


def test_bridge_launchagent_exports_watchdog():
    """Bridge plist exports V9_DISABLE_WATCHDOG."""
    plist = Path.home() / "Library/LaunchAgents/com.mems26.bridge.plist"
    if not plist.exists():
        import pytest
        pytest.skip("bridge plist not found")
    content = plist.read_text()
    assert "V9_DISABLE_WATCHDOG" in content


def test_bridge_launchagent_local_only():
    """Bridge plist sets CLOUD_URL to localhost."""
    plist = Path.home() / "Library/LaunchAgents/com.mems26.bridge.plist"
    if not plist.exists():
        import pytest
        pytest.skip("bridge plist not found")
    content = plist.read_text()
    assert "http://localhost:8000" in content


def test_backend_launchagent_conditional_keepalive():
    """Backend LaunchAgent uses conditional KeepAlive."""
    plist = Path.home() / "Library/LaunchAgents/com.mems26.backend.plist"
    if not plist.exists():
        import pytest
        pytest.skip("backend plist not found")
    content = plist.read_text()
    assert "<key>SuccessfulExit</key>" in content


def test_services_status_endpoint_registered():
    """GET /api/v9/admin/services/status route exists."""
    import inspect
    from backend.v9.api.v9.admin_routes import services_status
    assert callable(services_status)
