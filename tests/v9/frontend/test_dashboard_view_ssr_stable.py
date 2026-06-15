"""Dashboard view-switcher SSR-stability regression — hydration fix (2026-06-15).

Pins the fix for the React hydration error Michael hit on `/?view=build_status`:

  Hydration failed because the server rendered HTML didn't match the client.

Root cause: `V9Dashboard` initialized the top-level `view` state by reading
`window.location.search` *inside the useState initializer*, guarded by
`if (typeof window !== 'undefined')`. On the server `window` is undefined → the
initializer returned 'main'; on the client with `?view=build_status` it returned
'build_status'. The two initial renders diverged → hydration mismatch (React's
own error text even names the `typeof window` branch as a cause).

Fix: make the initial render SSR-stable (default 'main' on both server and
client) and apply the `?view=` deep-link in a useEffect that runs only on the
client, after mount — mirroring the existing `chartH` pattern in the same file.

This is a static source guard (the frontend has no JS test runner — package.json
exposes only dev/build/start/lint). Reverting to the window-in-initializer
pattern removes the SSR-stable default literal below → this test goes RED.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DASHBOARD = ROOT / "frontend/v9/src/v9/components/layout/V9Dashboard.tsx"
VIEWTABS = ROOT / "frontend/v9/src/v9/components/layout/ViewTabs.tsx"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_view_state_has_ssr_stable_default():
    src = _read(DASHBOARD)
    assert "useState<DashboardView>('main')" in src, (
        "view state must initialize to a constant SSR-stable default ('main') so "
        "the server and client produce the same first render. Reading window in "
        "the useState initializer reintroduces the hydration mismatch."
    )


def test_view_initializer_does_not_read_window():
    """The `view` useState must NOT read window/location in its initializer."""
    src = _read(DASHBOARD)
    idx = src.index("useState<DashboardView>")
    # Inspect the statement that initializes the view state (up to its semicolon).
    stmt = src[idx : src.index(";", idx)]
    assert "window" not in stmt and "location" not in stmt, (
        "view useState initializer must be SSR-stable — no window/location reads. "
        f"Found: {stmt!r}"
    )


def test_deep_link_applied_in_effect_on_mount():
    src = _read(DASHBOARD)
    assert "window.location.search" in src, (
        "the ?view= deep-link must still be honored — read it on the client."
    )
    assert "useEffect" in src and "setView(" in src, (
        "deep-link must be applied via setView inside a useEffect (client-only, "
        "post-mount), not in the render-time initializer."
    )


def test_trade_review_tab_is_wired():
    """Pin the new dashboard tab so it isn't dropped by a later refactor."""
    tabs = _read(VIEWTABS)
    assert "'trade_review'" in tabs, "trade_review must be a DashboardView + a tab."
    assert "Trade Review" in tabs, "trade_review tab needs its label."
    dash = _read(DASHBOARD)
    assert "TradeReviewPanel" in dash, "V9Dashboard must render TradeReviewPanel."
