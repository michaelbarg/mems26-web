"""P31.1-T5: /api/v9/day_type/v9/current uses et_today(), not system TZ."""
from unittest.mock import patch
from datetime import date


def test_current_uses_et_today():
    """The query binds et_today() — not date.today() or date('now')."""
    # Verify the import exists in the route module
    import backend.v9.api.v9.day_type_v9_routes as mod
    source = open(mod.__file__).read()
    assert "et_today" in source, "day_type_v9_routes must use et_today()"
    assert "date.today()" not in source, "date.today() must not appear in production code"
    assert "date('now')" not in source, "SQLite date('now') must not appear"
