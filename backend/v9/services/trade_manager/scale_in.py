"""SCALE_IN_V1 (Michael ruling 2026-08-13: "אם הכיוון ממשיך אפשר לחזק בעוד חוזים").

Reinforce a WINNING trade with extra contracts — a pure position-management add-on.
It NEVER touches the entry path (no gate, no filter): it only fires on an already-open
trade that has proven itself (T1 banked) and whose direction keeps going. The add-on
gets its own protective stop at the parent's entry (breakeven), so a scale-in can never
turn the winning parent into a loss beyond the entry level. Once per parent, capped size,
with-trend only, flag-gated OFF.

Pure function — no I/O, no env reads here (caller passes cfg + live dir_bias). Fully
testable; the caller (bar_level_detector.on_bar) does the flag check + child-trade PLACE.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ScaleInCfg:
    min_profit_pts: float = 6.0      # price must have run this far past entry (proof it works)
    add_contracts: int = 2           # how many to add
    max_total_contracts: int = 8     # never let parent+add exceed this
    require_with_trend: bool = True  # only reinforce WITH the day trend
    add_stop_at_entry: bool = True   # add-on stop = parent entry (BE) — bounded downside
    # ── P3 (CC_NEXT_2026-08-23B §4): computed spacing + avg stop + edge ban ──
    atr_spacing_mult: float = 1.5    # min spacing = 1.5×ATR (not 0.5)
    min_rr_spacing: float = 1.5      # min spacing = 1.5× initial risk (R)
    avg_stop: bool = True            # stop = structural average across entries
    edge_ban: bool = True            # don't add at session extreme (31/49 died)


@dataclass
class ScaleInDecision:
    add_contracts: int
    direction: str
    entry: float          # approx current favorable price (add-on entry)
    stop: float           # protective stop for the add-on (parent BE by default)
    reason: str


def margin_precheck(add_contracts: int,
                    available_funds: Optional[float],
                    per_contract_margin: float) -> tuple:
    """T-111 (broker reject 27.08 21:05 IL): never PLACE a scale-in child the
    broker will margin-reject. Live case: cmd #405 placed two 1c parents while
    avail_funds was ~$59 — 10700 filled, 10703 rejected ("Insufficient Account
    Value... Needed 1,428.90, Account Value: 1,162.34") — and the half-filled
    add desynced the books (SYS-3 divergence every 30s until corrected).

    Pure function. Returns (ok, reason).
    available_funds None => UNDETERMINED => pass-through (absence of knowledge
    is not negative knowledge — the broker remains the final arbiter); a
    POSITIVE shortfall is the only veto.
    """
    if available_funds is None:
        return True, "margin UNDETERMINED (no acct feed) — pass-through"
    need = add_contracts * per_contract_margin
    if available_funds < need:
        return False, ("margin precheck: avail %.2f < need %.2f (%dc x %.2f)"
                       % (available_funds, need, add_contracts,
                          per_contract_margin))
    return True, "margin ok: avail %.2f >= need %.2f" % (available_funds, need)


def should_scale_in(
    *,
    direction: str,
    entry_price: Optional[float],
    t1_hit: bool,
    already_scaled: bool,
    n_contracts_open: int,
    bar_high: float,
    bar_low: float,
    dir_bias: Optional[str],
    cfg: Optional[ScaleInCfg] = None,
    # P3 additions
    atr: Optional[float] = None,
    initial_risk_pts: Optional[float] = None,
    session_high: Optional[float] = None,
    session_low: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> Optional[ScaleInDecision]:
    """Return a ScaleInDecision to reinforce the trade, or None to do nothing.

    Fires only when ALL hold:
      - t1_hit — the entry proved itself (banked T1); we never add before proof.
      - not already_scaled — once per parent.
      - n_contracts_open > 0 — there is a live position to reinforce.
      - with-trend — dir_bias agrees with the trade direction (when known + required).
      - price continued ≥ min_profit_pts past entry (the move has legs).
      - parent + add-on ≤ max_total_contracts.
      - P3: spacing ≥ 1.5×ATR from parent entry.
      - P3: spacing ≥ 1.5R from parent entry.
      - P3: NOT at session extreme (edge-ban: 31/49 add-ons at extreme died).
    """
    cfg = cfg or ScaleInCfg()
    d = (direction or "").upper()
    if d not in ("LONG", "SHORT"):
        return None
    if not t1_hit or already_scaled:
        return None
    if entry_price is None or n_contracts_open <= 0:
        return None
    if n_contracts_open + cfg.add_contracts > cfg.max_total_contracts:
        return None
    if cfg.require_with_trend and dir_bias in ("UP", "DOWN"):
        counter = (d == "LONG" and dir_bias != "UP") or (d == "SHORT" and dir_bias != "DOWN")
        if counter:
            return None
    e = float(entry_price)
    # favorable excursion of THIS bar past entry
    fav = (float(bar_high) - e) if d == "LONG" else (e - float(bar_low))
    if fav < cfg.min_profit_pts:
        return None

    add_entry = float(bar_high) if d == "LONG" else float(bar_low)
    spacing = abs(add_entry - e)

    # ── P3: ATR-based minimum spacing (1.5×ATR, not 0.5) ──
    if atr is not None and atr > 0 and cfg.atr_spacing_mult > 0:
        min_atr_spacing = cfg.atr_spacing_mult * atr
        if spacing < min_atr_spacing:
            return None

    # ── P3: R-based minimum spacing (≥1.5R) ──
    if initial_risk_pts is not None and initial_risk_pts > 0 and cfg.min_rr_spacing > 0:
        min_r_spacing = cfg.min_rr_spacing * initial_risk_pts
        if spacing < min_r_spacing:
            return None

    # ── P3: Edge-ban (don't add at session extreme: 31/49 died) ──
    if cfg.edge_ban and session_high is not None and session_low is not None:
        edge_margin = max(1.0, (session_high - session_low) * 0.05)
        at_high = add_entry >= session_high - edge_margin
        at_low = add_entry <= session_low + edge_margin
        if (d == "LONG" and at_high) or (d == "SHORT" and at_low):
            return None  # adding at the extreme = chasing, 63% loss rate

    # ── P3: Averaged structural stop ──
    if cfg.avg_stop and stop_price is not None:
        # Average the parent's structural stop with the add-on's BE stop
        parent_stop = float(stop_price)
        be_stop = e  # parent entry = breakeven for add-on
        add_stop = round((parent_stop + be_stop) / 2, 2)
    elif cfg.add_stop_at_entry:
        add_stop = e
    else:
        add_stop = (add_entry - cfg.min_profit_pts if d == "LONG"
                    else add_entry + cfg.min_profit_pts)

    return ScaleInDecision(
        add_contracts=cfg.add_contracts,
        direction=d,
        entry=round(add_entry, 2),
        stop=round(add_stop, 2),
        reason=(f"P3 reinforce {d}: T1 banked + {fav:.1f}pt (spacing {spacing:.1f}pt "
                f"≥ 1.5×ATR) + with-trend ({dir_bias}) → +{cfg.add_contracts}c, "
                f"avg-stop {add_stop:.2f}"),
    )
