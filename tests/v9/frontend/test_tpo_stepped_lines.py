"""TPO stepped-line spec regression — Issue B fix (2026-05-22).

Pins three behaviors:

1. `parseSierraTsToMs` is exported from `tpoLevels.ts` and handles BOTH
   naive ET wall-clock strings AND TZ-tagged ones (`+00:00`, `Z`, `-04:00`).
   Without this, periods stamped by Sierra in UTC silently dropped through
   `Date.parse` → NaN and never rendered (P31-FE-TPO-1 in the 2026-05-21
   handoff §3).

2. `syncTpoPriceLines` defers to the stepped overlay (`TpoContinuityOverlay`)
   when `periods[]` already contains at least one entry for today's session.
   Flat horizontal lines remain only as a fallback while Sierra DLL has not
   yet exposed per-period developing values (see
   `docs/handoff/SIERRA_STUDIES_CONFIG_2026-05-19.md` Study ID:3 and
   `docs/reports/PROMPT30_10b_TPO_LEVELS_FIX.md` §"Still needed").

3. `TpoContinuityOverlay.periodToUnix` no longer hard-codes the `-04:00`
   suffix — it delegates to `parseSierraTsToMs` so UTC-tagged periods parse
   correctly instead of becoming silent NaN drops.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TPO_LEVELS = ROOT / "frontend/v9/src/v9/components/chart/v5b/tpoLevels.ts"
CONTINUITY = ROOT / "frontend/v9/src/v9/components/chart/v5b/TpoContinuityOverlay.tsx"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_tpolevels_exports_parse_sierra_ts_to_ms():
    src = _read(TPO_LEVELS)
    assert "export function parseSierraTsToMs" in src, (
        "parseSierraTsToMs must be an exported helper so TpoContinuityOverlay "
        "can share the same suffix-aware parser."
    )
    assert "TZ_SUFFIX_RE" in src, (
        "Must detect existing TZ suffix (Z / +HH:MM / -HH:MM) before "
        "appending the legacy -04:00 EDT shim."
    )
    assert "[Zz]" in src and "[+-]" in src, (
        "TZ_SUFFIX_RE must accept both Z and ±HH:MM forms — Sierra DLL "
        "emits a mix of naive ET and UTC-tagged periods."
    )


def test_tpolevels_period_opened_ms_uses_shared_parser():
    src = _read(TPO_LEVELS)
    assert "function periodOpenedMs" in src
    assert "function sessionOpenedMs" in src
    assert "parseSierraTsToMs(p.opened_ts)" in src, (
        "periodOpenedMs must go through parseSierraTsToMs to honour existing "
        "TZ suffixes."
    )
    assert "parseSierraTsToMs(ts)" in src, (
        "sessionOpenedMs must go through parseSierraTsToMs as well."
    )
    assert "+ '-04:00'" not in src.split("function periodOpenedMs")[1].split("}")[0], (
        "periodOpenedMs body must not concatenate '-04:00' directly — "
        "that's the P31-FE-TPO-1 bug pattern."
    )


def test_synctpopricelines_defers_to_stepped_when_periods_exist():
    src = _read(TPO_LEVELS)
    func = src.split("export function syncTpoPriceLines")[1]
    body = func.split("export function")[0]
    assert "todayPeriods" in body, (
        "syncTpoPriceLines must derive a todayPeriods filter so it can skip "
        "the flat horizontal render when the stepped overlay will handle it."
    )
    assert "periods ?? []" in body and "sessionDay(p.opened_ts) === todayDay" in body, (
        "Today-period filter must use sessionDay() to match the same date "
        "logic the stepped overlay applies."
    )
    assert "todayPeriods.length >= 1" in body, (
        "Flat lines must skip when ≥1 today period is available, so the "
        "stepped overlay owns the visual."
    )
    assert "lineStore2.set(chart, [])" in body, (
        "On the skip path we must still clear the prior flat series so we "
        "don't leak old horizontals."
    )


def test_tpo_continuity_overlay_uses_shared_parser():
    src = _read(CONTINUITY)
    assert "parseSierraTsToMs" in src, (
        "TpoContinuityOverlay must import parseSierraTsToMs from tpoLevels — "
        "without it, UTC-tagged periods like '2026-05-21 17:20:00+00:00' "
        "silently became NaN and were dropped from the stepped render."
    )
    func = src.split("function periodToUnix")[1].split("}")[0]
    assert "parseSierraTsToMs(ts)" in func, (
        "periodToUnix must delegate to parseSierraTsToMs."
    )
    # Negative assertion — the legacy hard-coded -04:00 shim must be gone
    # from this function's body.
    assert "+ '-04:00'" not in func, (
        "periodToUnix must not concatenate '-04:00' directly — handled by "
        "the shared parser."
    )


def test_tpo_continuity_overlay_still_uses_steps_for_today():
    """Sanity — the stepped rendering itself must stay intact."""
    src = _read(CONTINUITY)
    assert "LineType.WithSteps" in src, (
        "The stepped series flag must remain — that's what gives the line "
        "its half-hour step shape per Sierra Study ID:3."
    )
    assert "todayDay" in src and "isRth" in src, (
        "Today filter and RTH gate must remain — pink lines render only "
        "during 09:30–16:00 ET, per Issue B clarification."
    )


def test_yesterday_lines_bounded_to_rth_window_not_infinite():
    """Regression guard for the 2026-05-22 'infinite white lines' fix.

    Per Michael's spec ("the line starts at today's market open and goes
    until end of trading day"), yesterday's POC/VAH/VAL render as
    `LineSeries` across today's RTH window, NOT as `createPriceLine`
    (infinite horizontal) or as the legacy 2-point line (which truncated
    mid-chart when bars didn't cover the tail).
    """
    src = _read(TPO_LEVELS)
    func = src.split("export function syncYesterdayTpoLines")[1]
    body = func.split("export function")[0]
    assert "createPriceLine" not in body, (
        "syncYesterdayTpoLines must NOT use createPriceLine — that draws "
        "an infinite horizontal line which Michael explicitly rejected "
        "(2026-05-22 17:32 IL: 'still infinite')."
    )
    assert "todayRthWindowUnix" in body and "LineSeries" in body, (
        "syncYesterdayTpoLines must use a LineSeries bounded to today's "
        "RTH window (09:30 → 16:00 ET) via `todayRthWindowUnix`."
    )
    assert "STEP_SEC" in body, (
        "Dense points (every 5 min) must populate the LineSeries to dodge "
        "lightweight-charts' bar-gap truncation — single 2-point lines "
        "were silently clipped during 2026-05-22 RTH UAT."
    )


def test_yesterday_rth_window_helper_handles_dst():
    """`todayRthWindowUnix` must compute the ET 09:30/16:00 boundaries via
    the system tz database so both EDT (UTC-4) and EST (UTC-5) work, AND
    must NOT depend on the browser's local timezone for the conversion.

    Regression for the 2026-05-22 17:58 IL screenshot: previous version
    used `new Date(toLocaleString(...)).getTime()` which silently used the
    browser's local TZ (IL +3h) instead of America/New_York, drifting the
    lines by 3h (placed at 12:30 ET instead of 09:30 ET). The Intl
    formatter approach round-trips through the actual tz database.
    """
    src = _read(TPO_LEVELS)
    func = src.split("function todayRthWindowUnix")[1]
    body = func.split("function")[0]
    assert "America/New_York" in body, (
        "RTH window must reference America/New_York timezone explicitly."
    )
    assert "Intl.DateTimeFormat" in body, (
        "Window calculation must use Intl.DateTimeFormat — using a raw "
        "Date constructor on a toLocaleString string silently picks up "
        "the browser's local TZ offset (the 2026-05-22 3h drift bug)."
    )
    # The "9 + offsetHours" / "16 + offsetHours" pattern proves the
    # function shifts by the *measured* ET offset, not a hard-coded
    # value, so DST transitions Just Work.
    assert "9 + offsetHours" in body and "16 + offsetHours" in body, (
        "Open/close must be ET-09:30 and ET-16:00 plus the detected "
        "EDT/EST offset (4 or 5h) — proves DST-correct calculation."
    )
    # Negative assertion — make sure we don't regress to the buggy
    # local-TZ pattern.
    assert "new Date(new Date()" not in body, (
        "Must not use `new Date(new Date().toLocaleString(...))` — that "
        "pattern uses the browser's local TZ for the inner parse."
    )


def test_yesterday_lines_suppress_native_axis_label():
    """Regression for the 2026-05-22 17:55 IL screenshot — each yesterday
    level (VAH/POC/VAL) rendered with **two** stacked labels on the right
    price axis: the LineSeries' native lastValue badge AND the custom
    SierraLevelsOverlay TpoAxisBadge.

    SierraLevelsOverlay is the single source of truth for axis labels;
    `syncYesterdayTpoLines` must therefore disable the native badge by
    setting `lastValueVisible: false` and `title: ''` on its LineSeries.
    """
    src = _read(TPO_LEVELS)
    func = src.split("export function syncYesterdayTpoLines")[1]
    body = func.split("export function")[0]
    assert "lastValueVisible: false" in body, (
        "Yesterday LineSeries must disable native last-value badge — "
        "SierraLevelsOverlay owns the right-axis labels. "
        "(Bug regressed in screenshot showing doubled VAH/POC/VAL pills.)"
    )
    assert "title: ''" in body or 'title: ""' in body, (
        "Yesterday LineSeries must use empty title — a non-empty title "
        "puts a permanent text label on the right axis even when "
        "lastValueVisible=false, defeating the de-dup intent."
    )


def test_yesterday_window_close_follows_the_price():
    """`todayRthWindowUnix.close` must track `now + one bucket` during the
    live session, capped at the absolute RTH close. Without this the
    LineSeries drew flat horizontals 8h past the latest candle (Michael
    2026-05-22 18:05 IL "they need to follow along with the price").
    """
    src = _read(TPO_LEVELS)
    func = src.split("function todayRthWindowUnix")[1]
    body = func.split("function")[0]
    assert "Math.min(rthClose, nowSec + 300)" in body, (
        "close = min(RTH close, now + 5 min) — keeps the right edge at "
        "the latest live candle while the trading day is in progress, "
        "and pins to 16:00 ET post-RTH."
    )
    assert "Math.floor(Date.now() / 1000)" in body, (
        "Must call Date.now() inline (not cache a module-level constant) "
        "so each render reads the current time and the line extends as "
        "new bars arrive."
    )


def test_yesterday_store_survives_hmr():
    """Cleanup of orphan LineSeries must work across Next.js HMR cycles.
    A plain `new WeakMap()` is wiped when the module is reloaded, leaving
    ghost series on the chart that the new module can't see or remove
    (Michael 2026-05-22 18:05 IL "remove the previous lines"). Stash the
    WeakMap on `globalThis` so the cleanup path always sees prior refs.
    """
    src = _read(TPO_LEVELS)
    assert "globalThis" in src, (
        "Yesterday line store must live on globalThis — keeps refs alive "
        "across Next.js HMR module replacement."
    )
    assert "__mems26YdayTpoStore" in src, (
        "Use a specific global-name marker so the HMR-resilient cache is "
        "namespaced and survives unrelated globalThis pollution."
    )
    # The check pattern must guard against double-init while still
    # reusing the existing WeakMap when present.
    assert "if (!G.__mems26YdayTpoStore)" in src, (
        "Lazy init pattern preserves any pre-existing global from a "
        "prior module load (the whole point of the HMR-safe cache)."
    )
