"""Opening-type ENTRY triggers (Dalton) — REVISED per the 31-session historical
validation (2026-07-22 agent report) and run in SHADOW first.

Michael (07-22): "לפי דלתון יש סוגי פתיחה — המערכת צריכה לבצע ירי בהתאם...
תבצע בניה עכשיו... תשלח סוכן שיבדוק האם זה נכון גם על העבר."
The agent's verdict on the NAIVE spec was −6.12R/31 sessions → NOT enabled live.
This module implements the REVISED rules the evidence pointed to, emitting
SHADOW-only setups (metadata.shadow_only) to collect forward evidence:

  • OPEN_DRIVE   — close beyond the opening-range extreme, one-directional,
                   ONLY when the opening bar is NARROW (or_width <= narrow_max;
                   the single historical winner had OR 4.75pt; wide-OR drives
                   were noise: avg bar-1 range 16.5pt, 06-12 lost on 51pt R).
  • OPEN_TEST_DRIVE — excursion beyond the session open of >= td_frac * OR
                   measured from bar 2 onward (bar-1 wick does NOT arm — the
                   'weak' artifact fired 84% of days historically), then a
                   close back through the open → entry on the reclaim side.
  • OPEN_REJECTION_REVERSE — a drive-close happened (any OR width), then a
                   bar closes back through the open OPPOSITE → reversal entry.
                   SUPERSEDES an earlier drive entry (historically the only
                   trigger >50% to +1R: 4/5, avg MFE 4.67R — but must BANK,
                   so T1 = +1R, not hold-to-EOD).
  • OPEN_AUCTION — none of the above by the window end → no entry (honest).

One DRIVE/TEST_DRIVE entry max per session; ORR may follow once as the
superseding reversal. Pure logic — no env reads, no I/O; caller gates on
OPENING_ENTRY_V1 (shadow|1) and provides the session bars.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Revised parameters (agent report §4; YAML-tunable later if promoted)
# B2 (2026-08-12): parameterized OR threshold — was hardcoded 10pt, but
# real opening ranges are 14-22pt. Env-tunable; the historical range says
# ~20pt is correct for MES. When OPENING_OR_ATR_SCALE_V1=1, the threshold
# is max(OR_NARROW_MAX_PTS, 0.25 × daily_atr) — scales with volatility.
import os as _os_or
OR_NARROW_MAX_PTS = float(_os_or.getenv("OR_NARROW_MAX_PTS", "10.0") or "10.0")
TD_EXCURSION_FRAC = 0.5      # TEST excursion >= 50% of OR width, from bar 2
WINDOW_LAST_BAR = 6          # bars 2..6 (first 30 min)
ORR_FIRST_BAR = 3            # reversal earliest at bar 3

# ── OPEN-FIRE v1 (flag OPENING_FIRE_V1, caller-gated) — 60-min window +
# PULLBACK-CONT entry. Dalton: never chase the drive; fade the counter-bias
# excursion once it is REJECTED and enter with the trend. Params are the ones
# Michael ruled 07-23 (33% retrace / 16T stop / 1.5R via T1_BANK_R); YAML-tunable
# if refined. When the caller leaves enable_pullback=False the block below is
# never reached → byte-identical to the 30-min SHADOW spec.
WINDOW_LAST_BAR_EXTENDED = 12     # bars 2..12 (first 60 min) when OPENING_FIRE_V1
PULLBACK_RETRACE_FRAC = 0.33      # enter after price retraces ≥33% of the excursion
PULLBACK_STOP_OFFSET_TICKS = 16   # stop behind the rejected extreme
PULLBACK_MIN_EXCURSION_PTS = 6.0  # ignore noise: the excursion must be ≥ this


def _f(bar: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = bar.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def evaluate_opening_entry(session_bars: List[Dict[str, Any]],
                           already_fired: Optional[set] = None,
                           *, window_last_bar: int = WINDOW_LAST_BAR,
                           enable_pullback: bool = False,
                           bias: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Evaluate the LAST bar of `session_bars` (closed 5-min RTH bars, bar 1 =
    the 16:30 IL open bar) for an opening entry. Returns a trigger dict or None.
    `already_fired` = set of trigger types already emitted this session
    (enforces one DRIVE/TD + at most one superseding ORR).

    OPEN-FIRE v1 (caller passes when OPENING_FIRE_V1=1): `window_last_bar`
    extends the window to 12 bars (60 min) and `enable_pullback` activates the
    PULLBACK-CONT trigger. `bias` ("LONG"/"SHORT", from the opening-type seed)
    is an optional safety filter. Defaults reproduce the 30-min SHADOW spec
    exactly (window 6, no pullback, no bias)."""
    fired = already_fired or set()
    n = len(session_bars)
    if n < 2 or n > window_last_bar:
        return None

    b1 = session_bars[0]
    or_high = _f(b1, "h", "high")
    or_low = _f(b1, "l", "low")
    open_price = _f(b1, "o", "open")
    if None in (or_high, or_low, open_price):
        return None
    or_width = or_high - or_low
    last = session_bars[-1]
    close = _f(last, "c", "close")
    if close is None:
        return None

    closes = [_f(b, "c", "close") for b in session_bars[1:]]  # bars 2..n
    prior_closes = closes[:-1]  # bars 2..n-1

    drove_up_before = any(c is not None and c > or_high for c in prior_closes)
    drove_dn_before = any(c is not None and c < or_low for c in prior_closes)

    # ── ORR: a prior drive-close + this bar closes back through the OPEN
    # opposite. Supersedes an earlier DRIVE/TD entry (one ORR max).
    if "ORR" not in fired and n >= ORR_FIRST_BAR:
        if drove_up_before and close < open_price:
            return {"type": "ORR", "direction": "SHORT", "entry": close,
                    "or_width": or_width, "reverses": "UP_DRIVE"}
        if drove_dn_before and close > open_price:
            return {"type": "ORR", "direction": "LONG", "entry": close,
                    "or_width": or_width, "reverses": "DOWN_DRIVE"}

    # ── PULLBACK-CONT (OPEN-FIRE v1) — take the dominant excursion off the open
    # (up vs down), and once price has retraced ≥ PULLBACK_RETRACE_FRAC of it
    # with a rejection bar closing back the other way, enter WITH the rejection.
    # Stop behind the rejected extreme (16T), T1 = 1.5R (via build_opening_setup
    # + T1_BANK_R). `bias` (opening-type seed) only permits agreeing entries —
    # never fade a with-bias move. Only reached when enable_pullback (OFF ⇒ the
    # block is skipped and behaviour is byte-identical). One per session.
    if enable_pullback and "PULLBACK_CONT" not in fired and n >= 3:
        _highs = [_f(b, "h", "high") for b in session_bars]
        _lows = [_f(b, "l", "low") for b in session_bars]
        _prior_c = _f(session_bars[-2], "c", "close")
        _last_o = _f(last, "o", "open")
        if (_prior_c is not None and _last_o is not None
                and all(v is not None for v in _highs)
                and all(v is not None for v in _lows)):
            peak = max(_highs)
            trough = min(_lows)
            up_exc = peak - open_price      # counter-bias rally → fade = SHORT
            dn_exc = open_price - trough    # counter-bias dip   → fade = LONG
            cand = None
            if up_exc >= dn_exc and up_exc >= PULLBACK_MIN_EXCURSION_PTS:
                if (peak - close >= PULLBACK_RETRACE_FRAC * up_exc
                        and close < _last_o and close < _prior_c):
                    cand = ("SHORT", peak)
            elif dn_exc > up_exc and dn_exc >= PULLBACK_MIN_EXCURSION_PTS:
                if (close - trough >= PULLBACK_RETRACE_FRAC * dn_exc
                        and close > _last_o and close > _prior_c):
                    cand = ("LONG", trough)
            if cand is not None and bias in (None, cand[0]):
                return {"type": "PULLBACK_CONT", "direction": cand[0],
                        "entry": close, "or_width": or_width, "extreme": cand[1],
                        "stop_offset_ticks": PULLBACK_STOP_OFFSET_TICKS,
                        "excursion": round(max(up_exc, dn_exc), 2),
                        "t1_r": 1.5}

    # only one initiating entry (DRIVE or TD) per session
    if fired & {"DRIVE", "TEST_DRIVE"}:
        return None

    # ── DRIVE: close beyond OR extreme, one-directional, NARROW OR only.
    # B2: ATR-scaled threshold when OPENING_OR_ATR_SCALE_V1=1
    _or_max = OR_NARROW_MAX_PTS
    try:
        import os as _os_drive
        if _os_drive.getenv("OPENING_OR_ATR_SCALE_V1", "0").lower() in ("1", "true", "yes"):
            from backend.v9.systems.day_type.detector import compute_daily_atr
            _daily_atr = compute_daily_atr(14)
            if _daily_atr and _daily_atr > 0:
                _or_max = max(OR_NARROW_MAX_PTS, 0.25 * _daily_atr)
    except Exception:
        pass
    if or_width <= _or_max:
        if close > or_high and not drove_dn_before:
            return {"type": "DRIVE", "direction": "LONG", "entry": close,
                    "or_width": or_width}
        if close < or_low and not drove_up_before:
            return {"type": "DRIVE", "direction": "SHORT", "entry": close,
                    "or_width": or_width}

    # ── TEST_DRIVE: excursion beyond open (>= frac*OR) measured from BAR 2
    # onward on one side, no drive-close on that side, then close through the
    # open to the other side.
    need = TD_EXCURSION_FRAC * or_width
    if need > 0 and n >= 3:  # excursion bars 2..n-1, reclaim on bar n
        exc_up = max((_f(b, "h", "high") or open_price) - open_price
                     for b in session_bars[1:-1])
        exc_dn = max(open_price - (_f(b, "l", "low") or open_price)
                     for b in session_bars[1:-1])
        if exc_up >= need and not drove_up_before and close < open_price:
            return {"type": "TEST_DRIVE", "direction": "SHORT", "entry": close,
                    "or_width": or_width, "excursion": exc_up}
        if exc_dn >= need and not drove_dn_before and close > open_price:
            return {"type": "TEST_DRIVE", "direction": "LONG", "entry": close,
                    "or_width": or_width, "excursion": exc_dn}

    # ── EXTREME_REJECT (Michael's opening rule, 07-22 "מדויק" — validated on
    # 31 sessions): a bar tests the RUNNING session extreme (touch ≤0.5,
    # rejection close >0.5 back), the NEXT bar CONFIRMS (closes further away).
    # Validation verdicts applied: confirm-filter kept (12/14 to +1R),
    # stop widened to extreme ∓10T (6T re-probed routinely; sweep 10-16T
    # flips expectancy), entry at confirm close, bank at +1R (setup t1).
    # SHADOW evidence collection — one per session.
    if "EXTREME_REJECT" not in fired and n >= 3:
        test_i = n - 2   # candidate test bar = previous bar (index n-2)
        if test_i >= 1:  # bar 2+
            prior = session_bars[:test_i]
            prior_low = min((_f(b, "l", "low") or open_price) for b in prior)
            prior_high = max((_f(b, "h", "high") or open_price) for b in prior)
            tb = session_bars[test_i]
            tb_l, tb_h, tb_c = _f(tb, "l", "low"), _f(tb, "h", "high"), _f(tb, "c", "close")
            if None not in (tb_l, tb_h, tb_c):
                # low test + confirm
                if tb_l <= prior_low + 0.5 and tb_c > prior_low + 0.5 and close > tb_c:
                    return {"type": "EXTREME_REJECT", "direction": "LONG",
                            "entry": close, "or_width": or_width,
                            "extreme": min(prior_low, tb_l), "stop_offset_ticks": 10}
                # high test + confirm
                if tb_h >= prior_high - 0.5 and tb_c < prior_high - 0.5 and close < tb_c:
                    return {"type": "EXTREME_REJECT", "direction": "SHORT",
                            "entry": close, "or_width": or_width,
                            "extreme": max(prior_high, tb_h), "stop_offset_ticks": 10}

    return None


def build_opening_setup(trigger: Dict[str, Any], session_bars: List[Dict[str, Any]],
                        shadow_only: bool, offset_ticks: int = 6) -> Optional[Dict[str, Any]]:
    """Gateway setup from a trigger: stop behind the session-structure extreme
    (+offset), T1 = +1R (BANK — the historical ORR lesson: hold-to-EOD gives
    the move back). All normal gateway gates still apply."""
    from backend.v9.systems.stop_anchors import resolver as SA

    direction = trigger["direction"]
    entry = float(trigger["entry"])
    if trigger.get("extreme") is not None:
        # EXTREME_REJECT: stop behind the TESTED extreme, wider offset per the
        # 31-session sweep (6T re-probed routinely; 10T+ flips expectancy).
        anchor = float(trigger["extreme"])
        offset_ticks = int(trigger.get("stop_offset_ticks", offset_ticks))
    else:
        lows = [_f(b, "l", "low") for b in session_bars]
        highs = [_f(b, "h", "high") for b in session_bars]
        if direction == "LONG":
            anchor = min(v for v in lows if v is not None)
        else:
            anchor = max(v for v in highs if v is not None)
    stop = SA.apply_offset(anchor, direction, offset_ticks)
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    # OPENING STOP CAP (Michael 2026-07-31 17:45 "למה לונג פתיחה על סכום כזה"):
    # trade #575 — a 40pt opening bar made "stop behind the structure" a
    # 39.75pt / $199-per-contract stop, 20% of the account on one trade. The
    # structural rule is right on a normal open and ruinous on a volatile one.
    # Same doctrine as the ZLR cap ruling (06-12) and the cap-clamp (07-30):
    #   raw risk > OPENING_MAX_RISK_PTS (25) -> the open is chaos, NO trade;
    #   raw risk > OPENING_STOP_CAP_PTS (15) -> stop capped at 15pt; T1 scales
    #   off the capped risk. Env-tunable; Michael's word can revoke.
    import os as _oc_os
    import logging as _oc_logging
    _oc_log = _oc_logging.getLogger(__name__)
    _oc_max = float(_oc_os.getenv("OPENING_MAX_RISK_PTS", "25") or 25)
    _oc_cap = float(_oc_os.getenv("OPENING_STOP_CAP_PTS", "15") or 15)
    if risk > _oc_max:
        _oc_log.warning(
            "[OpeningEntry] SKIP %s %s: structural risk %.2fpt > max %.1fpt — "
            "opening too volatile for a structural stop", trigger.get("type"),
            direction, risk, _oc_max)
        return None
    if risk > _oc_cap:
        stop = round(entry - _oc_cap, 2) if direction == "LONG" else round(entry + _oc_cap, 2)
        _oc_log.warning(
            "[OpeningEntry] STOP CAP %s %s: structural %.2fpt -> capped %.1fpt "
            "(stop %.2f)", trigger.get("type"), direction, risk, _oc_cap, stop)
        risk = _oc_cap
    # PULLBACK-CONT carries an explicit T1 (1.5R, Michael 07-23) so it does not
    # depend on the global T1_BANK_R; all other triggers keep the T1_BANK_R bank.
    _t1r_override = trigger.get("t1_r")
    if _t1r_override is not None:
        try:
            _t1r = float(_t1r_override)
        except (TypeError, ValueError):
            _t1r = 1.0
    else:
        try:
            _t1r = float(__import__("os").getenv("T1_BANK_R", "1.0") or 1.0)
        except (TypeError, ValueError):
            _t1r = 1.0
    t1 = entry + _t1r * risk if direction == "LONG" else entry - _t1r * risk
    return {
        "firing_system": 2,
        "direction": direction,
        "classification": f"OPENING_{trigger['type']}",
        "confidence": 0.6,
        "entry_price": entry,
        "stop": stop,
        "t1": round(t1, 2),
        "t2": None,
        "t3": None,
        "metadata": {
            "opening_entry": trigger["type"],
            "shadow_only": bool(shadow_only),
            "or_width": trigger.get("or_width"),
            "reverses": trigger.get("reverses"),
        },
    }


# ── OPENING_DIR_FUSION_V1 (empirical study 2026-07-24, docs/reports/OPENING_SIGNAL_EDGE) ──
# Volume-confirmed opening direction: on the days it fires it called the day direction
# 73% vs the classifier's 53%. Pure function (DB-free) so it is unit-testable; the caller
# supplies the first-30-min bars, the opening volume, the trailing-median opening volume,
# and prior-day reference levels. Returns "UP" / "DOWN" / None. None = low-conviction
# (auction) OR a level-break that conflicts with momentum → NO opening trade (the skip
# is half the edge). Caller-gated on OPENING_DIR_FUSION_V1; used only as a direction
# gate over the existing opening entries (never fires a trade by itself).
FUSION_MOM_MIN_PTS = 2.0
FUSION_ACCEPT_BUFFER_PTS = 1.0


def opening_dir_fusion(bars: List[Dict[str, Any]], open_price: Optional[float],
                       opening_vol: Optional[float], median_open_vol: Optional[float],
                       *, pdh: Optional[float] = None, pdl: Optional[float] = None,
                       prior_vah: Optional[float] = None, prior_val: Optional[float] = None,
                       mom_min_pts: float = FUSION_MOM_MIN_PTS) -> Optional[str]:
    # B4 (2026-08-12): permanent fusion logging — inputs + decision, always.
    # The fusion was silent when it dropped (vol < median → None, no log line).
    import logging as _log_fus
    _fus_log = _log_fus.getLogger(__name__)

    if not bars or open_price is None or opening_vol is None or median_open_vol is None:
        _fus_log.info(
            "[OPENING_DIR_FUSION] SKIP: missing inputs (bars=%d open=%s vol=%s median=%s)",
            len(bars or []), open_price, opening_vol, median_open_vol)
        return None
    if opening_vol < median_open_vol:
        _fus_log.info(
            "[OPENING_DIR_FUSION] SKIP: opening_vol %.0f < median %.0f — auction/low-conviction",
            opening_vol, median_open_vol)
        return None
    closes = [_f(b, "c", "close") for b in bars]
    highs = [_f(b, "h", "high") for b in bars]
    lows = [_f(b, "l", "low") for b in bars]
    b6c = closes[-1]
    hs = [h for h in highs if h is not None]
    ls = [l for l in lows if l is not None]
    if b6c is None or not hs or not ls:
        return None
    delta = b6c - open_price                       # 30-min momentum
    mom = "UP" if delta > mom_min_pts else ("DOWN" if delta < -mom_min_pts else None)
    if mom is None:
        return None
    b6h, b6l = max(hs), min(ls)
    refs_up = [x for x in (pdh, prior_vah) if x is not None]
    refs_dn = [x for x in (pdl, prior_val) if x is not None]
    acc = None                                     # accepted level-break in the 30-min
    if refs_up and b6c > max(refs_up) and b6l >= min(refs_up) - FUSION_ACCEPT_BUFFER_PTS:
        acc = "UP"
    elif refs_dn and b6c < min(refs_dn) and b6h <= max(refs_dn) + FUSION_ACCEPT_BUFFER_PTS:
        acc = "DOWN"
    if acc is not None and acc != mom:
        _fus_log.info(
            "[OPENING_DIR_FUSION] CONFLICT: mom=%s acc=%s — skip", mom, acc)
        return None
    _fus_log.info(
        "[OPENING_DIR_FUSION] RESULT=%s (vol=%.0f/%.0f delta=%.2f mom=%s acc=%s)",
        mom, opening_vol, median_open_vol, delta, mom, acc)
    return mom


def opening_first_trade_ok(session_bars, direction, opening_conf,
                           min_conf=None, min_bars=None,
                           trigger_type=None, opening_type=None):
    """OPENING_FIRST_TRADE_STRICT_V1 (Michael ruling 2026-07-31 18:20:
    "העסקה הראשונה צריכה להגיע רק בוודאות של סוג הפתיחה ולהחמיר כניסה").

    Trade #575 fired on the bar-1 close of a 40pt opening bar with opening
    confidence 0.00 and no confirmation — long at the top of a spike that
    reversed. Two strict conditions, both required, fail-CLOSED:

      1. CERTAINTY  — the opening-type detector's confidence must be >=
         OPENING_MIN_CONF (0.7). Unknown/None confidence = no certainty = no
         first trade. (Dalton grading: Drive .85 / Test .75 / ORR .65 — a
         graded Drive passes, an ungraded guess never does.)
      2. CONFIRMATION — at least OPENING_CONFIRM_BARS (3) closed bars, and
         the LAST closed bar must close in the trigger direction (c>o for
         LONG, c<o for SHORT). One impulsive bar is not an entry; the market
         must confirm once.

    B1 (2026-08-12): OPENING_CONF_ENGINE_FUSE_V1 — when the entry engine's
    own trigger agrees with the direction, use the engine's graded confidence
    (DRIVE=0.85, TEST=0.75, ORR=0.65) instead of the detector's opening_conf.
    This prevents auction days (conf=0.0) from killing valid engine triggers.

    Returns (ok: bool, reason: str)."""
    import os as _os
    if min_conf is None:
        min_conf = float(_os.getenv("OPENING_MIN_CONF", "0.7") or 0.7)
    if min_bars is None:
        min_bars = int(_os.getenv("OPENING_CONFIRM_BARS", "3") or 3)
    try:
        conf = float(opening_conf) if opening_conf is not None else None
    except (TypeError, ValueError):
        conf = None

    # B1 CONF_FUSE: REMOVED (binary-gates, Michael 25-26.08).
    # Was dead code: built to rescue conf=0.0 but its own guard was conf>=0.5.
    # The entire conf gate is replaced above by the binary structural check.

    # Binary gate (replaces conf<min_conf per Michael 25-26.08:
    # "למה יש אחוזים" / "בלתי אפשרי למדוד באופן לא שקוף").
    # LEGACY_CONF_GATES=1 restores the old path as a rollback.
    import os as _lcg_os
    if _lcg_os.getenv("LEGACY_CONF_GATES", "0").lower() in ("1", "true", "yes"):
        if conf is None or conf < min_conf:
            return False, f"opening confidence {conf} < {min_conf} — no certainty, no first trade"
    else:
        # Binary: veto only if the classifier POSITIVELY says the opposite direction.
        # UNKNOWN / None / low-confidence = UNDETERMINED = no veto (Rule: absence ≠ negative).
        if opening_type and direction:
            _ot = str(opening_type).upper()
            _dir = str(direction).upper()
            # Classifier says DOWN but we want LONG → positive conflict → veto
            _classified_down = _ot in ("OPEN_DRIVE_DOWN", "TEST_DRIVE_DOWN")
            _classified_up = _ot in ("OPEN_DRIVE_UP", "TEST_DRIVE_UP")
            if (_dir == "LONG" and _classified_down) or (_dir == "SHORT" and _classified_up):
                return False, (f"binary veto: opening classifier says {_ot} "
                               f"conflicts with {_dir} — positive opposing signal")
    if not session_bars or len(session_bars) < min_bars:
        return False, f"only {len(session_bars or [])} bars < {min_bars} — confirmation bar required"
    last = session_bars[-1]
    o, c = _f(last, "o", "open"), _f(last, "c", "close")
    if o is None or c is None:
        return False, "last bar unreadable — fail-closed"
    confirmed = (c > o) if direction == "LONG" else (c < o)
    if not confirmed:
        return False, f"last bar did not confirm {direction} (o={o} c={c})"
    _conf_s = f"{conf:.2f}" if conf is not None else "n/a"
    return True, f"confirmed: conf={_conf_s}, {len(session_bars)} bars, last bar with-direction"
