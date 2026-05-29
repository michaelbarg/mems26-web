"""P31.1-T5: /api/v9/key_levels uses et_today(), not SQLite date('now')."""


def test_key_levels_uses_et_today():
    """key_levels_routes must use et_today() for date queries."""
    import backend.v9.api.v9.key_levels_routes as mod
    source = open(mod.__file__).read()
    assert "et_today" in source, "key_levels_routes must use et_today()"
    assert "date('now')" not in source, "SQLite date('now') must not appear"
