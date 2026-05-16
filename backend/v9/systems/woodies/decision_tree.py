"""Woodies V1 decision tree — 21 stages (Option B: skeleton + delegation).

D-067 Hybrid: decision stages live here; execution for B1–B14 delegates to
trade_manager / layer4 / gateway — no duplicated trade logic.

Master Index V2 · Woodies Decision Tree V1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.v9.systems.woodies.schemas import PatternResult, WoodiesBar


class StageOwner(str, Enum):
    INTERNAL = "woodies"
    TOUCHPOINT = "touchpoint_api"
    PREFIRE = "pre_fire_validator"
    GATEWAY = "trading_gateway"
    TRADE_MANAGER = "trade_manager"
    LAYER4 = "layer4"


class StagePhase(str, Enum):
    PRE_FIRE = "A"  # A1–A7
    ACTIVE = "B"  # B1–B14


class StageStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"  # not applicable this bar (e.g. no setup)
    DELEGATED = "DELEGATED"  # owner external; not evaluated in-process
    PENDING = "PENDING"  # wired later (e.g. touch-points HTTP)


@dataclass(frozen=True)
class StageDefinition:
    stage_id: str
    name: str
    phase: StagePhase
    owner: StageOwner
    delegate_module: str = ""


@dataclass
class StageResult:
    stage_id: str
    status: StageStatus
    message: str = ""
    owner: StageOwner = StageOwner.INTERNAL
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WoodiesDecisionContext:
    """Inputs for one decision-tree pass (typically end of process_bar)."""

    bars: List[WoodiesBar]
    studies: Dict[str, Any]
    patterns: List[PatternResult]
    classification: str
    direction: Optional[str]
    sizing: str  # full | half | reject
    current_state: Dict[str, Any]
    fire_setup: Optional[Dict[str, Any]] = None  # when routing to gateway
    touchpoints: Optional[Dict[str, Any]] = None


# Canonical 21 stages per Master Index / WAVE1_S4_AUDIT
STAGE_DEFINITIONS: List[StageDefinition] = [
    # ── A: Pre-fire ──
    StageDefinition("A1", "Trend Gate (SWI / trend_state)", StagePhase.PRE_FIRE, StageOwner.INTERNAL),
    StageDefinition("A2", "Study Validity (11 studies)", StagePhase.PRE_FIRE, StageOwner.INTERNAL),
    StageDefinition("A3", "Pattern Detection (9 patterns)", StagePhase.PRE_FIRE, StageOwner.INTERNAL),
    StageDefinition("A4", "Touch-Points (S1/S5/S6/L0 advisory)", StagePhase.PRE_FIRE, StageOwner.TOUCHPOINT),
    StageDefinition("A5", "Auxiliary Alignment (SWI/CZI/TCCI/LSMA/EMA)", StagePhase.PRE_FIRE, StageOwner.INTERNAL),
    StageDefinition("A6", "Entry Classification (REACTIVE / INITIATIVE)", StagePhase.PRE_FIRE, StageOwner.INTERNAL),
    StageDefinition(
        "A7",
        "Universal Checks (pre_fire + gateway)",
        StagePhase.PRE_FIRE,
        StageOwner.PREFIRE,
        "backend.v9.shared.pre_fire_validator",
    ),
    # ── B: Active trade (delegated) ──
    StageDefinition("B1", "Active: initial stop discipline", StagePhase.ACTIVE, StageOwner.TRADE_MANAGER, "trade_manager"),
    StageDefinition("B2", "Active: break-even on T1", StagePhase.ACTIVE, StageOwner.TRADE_MANAGER, "trade_manager"),
    StageDefinition("B3", "Active: scale C1", StagePhase.ACTIVE, StageOwner.TRADE_MANAGER, "trade_manager"),
    StageDefinition("B4", "Active: scale C2", StagePhase.ACTIVE, StageOwner.TRADE_MANAGER, "trade_manager"),
    StageDefinition("B5", "Active: scale C3 / runner", StagePhase.ACTIVE, StageOwner.TRADE_MANAGER, "trade_manager"),
    StageDefinition("B6", "Active: time stop", StagePhase.ACTIVE, StageOwner.TRADE_MANAGER, "trade_manager"),
    StageDefinition("B7", "Active: EOD flatten", StagePhase.ACTIVE, StageOwner.GATEWAY, "gateway.eod"),
    StageDefinition("B8", "Active: SWI tighten stop", StagePhase.ACTIVE, StageOwner.LAYER4, "layer4.swi_tighten"),
    StageDefinition("B9", "Active: CCI flat tighten", StagePhase.ACTIVE, StageOwner.LAYER4, "layer4.cci_flat_tighten"),
    StageDefinition("B10", "Active: TCCI cross exit", StagePhase.ACTIVE, StageOwner.LAYER4, "layer4.tcci_cross_exit"),
    StageDefinition("B11", "Active: MFE peak 80% tighten", StagePhase.ACTIVE, StageOwner.LAYER4, "layer4.mfe_peak_tighten"),
    StageDefinition("B12", "Active: day-type targets verify", StagePhase.ACTIVE, StageOwner.LAYER4, "layer4.day_type_targets_verify"),
    StageDefinition("B13", "Active: direction-change exit", StagePhase.ACTIVE, StageOwner.INTERNAL, "direction_change_detector"),
    StageDefinition("B14", "Active: cluster / empty-zone management", StagePhase.ACTIVE, StageOwner.TRADE_MANAGER, "layer3.handoff"),
]

STAGE_BY_ID: Dict[str, StageDefinition] = {s.stage_id: s for s in STAGE_DEFINITIONS}

TOUCHPOINT_ENDPOINTS: Dict[str, str] = {
    "day_type": "http://localhost:8000/api/v9/day_type/v9/current",
    "tpo": "http://localhost:8000/api/v9/tpo/current",
    "veto": "http://localhost:8000/api/v9/veto/state",
    "killzone": "http://localhost:8000/api/v9/killzone/current",
    "layer0": "http://localhost:8000/api/v9/layer0/state",
}


def _a1_trend_gate(ctx: WoodiesDecisionContext) -> StageResult:
    trend = (ctx.studies.get("trend_state") or "GRAY").upper()
    if not ctx.patterns:
        return StageResult("A1", StageStatus.SKIP, "no patterns")
    if trend == "GRAY" and ctx.patterns:
        best = max(ctx.patterns, key=lambda p: p.confidence)
        if best.confidence < 0.55:
            return StageResult("A1", StageStatus.FAIL, f"trend GRAY + low conf {best.confidence:.2f}")
    return StageResult("A1", StageStatus.PASS, f"trend_state={trend}")


def _a2_study_validity(ctx: WoodiesDecisionContext) -> StageResult:
    required = (
        "cci_14", "cci_6_tcci", "ema_34", "lsma_value", "swi_value",
        "czi_value", "trend_state", "predictor_next_cci",
    )
    missing = [k for k in required if ctx.studies.get(k) is None]
    if missing:
        return StageResult("A2", StageStatus.FAIL, f"missing studies: {missing}")
    return StageResult("A2", StageStatus.PASS, "11 studies present")


def _a3_pattern_detect(ctx: WoodiesDecisionContext) -> StageResult:
    if not ctx.patterns:
        return StageResult("A3", StageStatus.SKIP, "no patterns this bar")
    ids = [p.pattern_id for p in ctx.patterns]
    return StageResult("A3", StageStatus.PASS, f"patterns={ids}", details={"count": len(ids)})


def _a4_touchpoints(ctx: WoodiesDecisionContext) -> StageResult:
    if not ctx.patterns:
        return StageResult("A4", StageStatus.SKIP, "no setup needs touch-points", owner=StageOwner.TOUCHPOINT)

    touchpoints, unavailable = _load_touchpoints(ctx)
    if unavailable:
        return StageResult(
            "A4",
            StageStatus.PENDING,
            f"touch-point context unavailable: {', '.join(unavailable)}",
            owner=StageOwner.TOUCHPOINT,
            details={"unavailable": unavailable, "touchpoints": touchpoints},
        )

    blocks = _touchpoint_blocks(ctx, touchpoints)
    if blocks:
        return StageResult(
            "A4",
            StageStatus.FAIL,
            f"touch-point blocks: {', '.join(blocks)}",
            owner=StageOwner.TOUCHPOINT,
            details={"blocks": blocks, "touchpoints": touchpoints},
        )

    return StageResult(
        "A4",
        StageStatus.PASS,
        "touch-points OK: day_type/tpo/veto/killzone/layer0",
        owner=StageOwner.TOUCHPOINT,
        details={"touchpoints": touchpoints},
    )


def _load_touchpoints(ctx: WoodiesDecisionContext) -> Tuple[Dict[str, Any], List[str]]:
    if ctx.touchpoints is not None:
        return dict(ctx.touchpoints), _missing_touchpoints(ctx.touchpoints)

    fetched: Dict[str, Any] = {}
    unavailable: List[str] = []
    for name, url in TOUCHPOINT_ENDPOINTS.items():
        try:
            import requests

            resp = requests.get(url, timeout=2)
            if resp.status_code != 200:
                unavailable.append(f"{name}:http_{resp.status_code}")
                continue
            data = resp.json()
            fetched[name] = data
            if isinstance(data, dict) and data.get("error"):
                unavailable.append(f"{name}:{data.get('error')}")
        except Exception as exc:
            unavailable.append(f"{name}:{exc}")

    unavailable.extend(item for item in _missing_touchpoints(fetched) if item not in unavailable)
    return fetched, unavailable


def _missing_touchpoints(touchpoints: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for name in TOUCHPOINT_ENDPOINTS:
        data = touchpoints.get(name)
        if not isinstance(data, dict):
            missing.append(f"{name}:missing")
    return missing


def _touchpoint_blocks(ctx: WoodiesDecisionContext, touchpoints: Dict[str, Any]) -> List[str]:
    blocks: List[str] = []

    day_type = touchpoints["day_type"]
    if day_type.get("classified") is not True:
        blocks.append("day_type:not_classified")
    elif not _day_type_name(day_type):
        blocks.append("day_type:missing_day_type")

    tpo = touchpoints["tpo"]
    if tpo.get("running") is False:
        blocks.append("tpo:not_running")
    missing_tpo = [field for field in ("poc", "vah", "val") if tpo.get(field) is None]
    if missing_tpo:
        blocks.append(f"tpo:missing_{'/'.join(missing_tpo)}")

    veto = touchpoints["veto"]
    suffering_side = str(veto.get("suffering_side") or "NONE").upper()
    if veto.get("veto_active") and ctx.direction and suffering_side == ctx.direction.upper():
        blocks.append(f"veto:{ctx.direction.upper()}")

    killzone = touchpoints["killzone"]
    zone = killzone.get("current_zone") or {}
    zone_name = str(zone.get("name") or "UNKNOWN").upper()
    edge_class = str(zone.get("edge_class") or "none").lower()
    if killzone.get("running") is False:
        blocks.append("killzone:not_running")
    elif zone_name in {"CLOSED", "WEEKEND", "UNKNOWN"} or edge_class == "none":
        blocks.append(f"killzone:{zone_name}")

    layer0 = touchpoints["layer0"]
    layer0_state = str(layer0.get("state") or "").upper()
    if not layer0_state:
        blocks.append("layer0:missing_state")
    elif layer0_state == "SEARCHING":
        blocks.append("layer0:SEARCHING")

    return blocks


def _day_type_name(day_type: Dict[str, Any]) -> Optional[str]:
    data = day_type.get("data")
    if isinstance(data, dict):
        return data.get("day_type")
    return day_type.get("day_type")


def _a5_auxiliary(ctx: WoodiesDecisionContext) -> StageResult:
    if ctx.sizing == "reject":
        return StageResult("A5", StageStatus.FAIL, "calculate_size=reject")
    return StageResult("A5", StageStatus.PASS, f"sizing={ctx.sizing}")


def _a6_entry_class(ctx: WoodiesDecisionContext) -> StageResult:
    """Map legacy TACTICAL/STRATEGIC → REACTIVE/INITIATIVE for spec traceability."""
    spec_class = "NO_SETUP"
    if ctx.classification == "TACTICAL":
        spec_class = "REACTIVE"
    elif ctx.classification == "STRATEGIC":
        spec_class = "INITIATIVE"
    if spec_class == "NO_SETUP":
        return StageResult("A6", StageStatus.SKIP, "NO_SETUP")
    return StageResult(
        "A6",
        StageStatus.PASS,
        f"code={ctx.classification} spec={spec_class}",
        details={"code_classification": ctx.classification, "spec_classification": spec_class},
    )


def _a7_universal(ctx: WoodiesDecisionContext) -> StageResult:
    setup = ctx.fire_setup
    if not setup:
        if ctx.patterns and ctx.sizing != "reject":
            return StageResult(
                "A7",
                StageStatus.FAIL,
                "missing fire_setup for routable pattern",
                owner=StageOwner.PREFIRE,
            )
        return StageResult(
            "A7",
            StageStatus.SKIP,
            "no fire_setup — gateway/pre_fire run at route_setup",
            owner=StageOwner.PREFIRE,
        )
    try:
        from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire

        req = FireRequest(
            system_id="T2_WOODIES",
            direction=setup["direction"],
            entry_price=setup["entry_price"],
            stop_price=setup["stop_price"],
            t1_price=setup["t1_price"],
            t2_price=setup["t2_price"],
            time_stop_minutes=int(setup.get("time_stop_minutes", 60)),
            confidence=int(setup.get("confidence", 70)),
        )
        resp = validate_fire(req)
        if resp.valid:
            return StageResult("A7", StageStatus.PASS, "pre_fire OK", owner=StageOwner.PREFIRE)
        return StageResult("A7", StageStatus.FAIL, resp.fail_reason or "pre_fire failed", owner=StageOwner.PREFIRE)
    except Exception as exc:
        return StageResult("A7", StageStatus.FAIL, f"pre_fire error: {exc}", owner=StageOwner.PREFIRE)


_PRE_FIRE_EVALUATORS: Dict[str, Callable[[WoodiesDecisionContext], StageResult]] = {
    "A1": _a1_trend_gate,
    "A2": _a2_study_validity,
    "A3": _a3_pattern_detect,
    "A4": _a4_touchpoints,
    "A5": _a5_auxiliary,
    "A6": _a6_entry_class,
    "A7": _a7_universal,
}


def _delegated_b_stage(defn: StageDefinition) -> StageResult:
    return StageResult(
        defn.stage_id,
        StageStatus.DELEGATED,
        f"owner={defn.owner.value} module={defn.delegate_module}",
        owner=defn.owner,
    )


class WoodiesDecisionTree:
    """Runs A1–A7 on each bar; B1–B14 reported as delegated (D-067)."""

    def run_pre_fire(self, ctx: WoodiesDecisionContext) -> List[StageResult]:
        results: List[StageResult] = []
        for defn in STAGE_DEFINITIONS:
            if defn.phase != StagePhase.PRE_FIRE:
                continue
            ev = _PRE_FIRE_EVALUATORS.get(defn.stage_id)
            if ev:
                results.append(ev(ctx))
            else:
                results.append(StageResult(defn.stage_id, StageStatus.FAIL, "no evaluator"))
        return results

    def run_active_trade(self, _trade_state: Optional[Dict[str, Any]] = None) -> List[StageResult]:
        """B-stages: never duplicate trade_manager — return DELEGATED markers."""
        return [_delegated_b_stage(d) for d in STAGE_DEFINITIONS if d.phase == StagePhase.ACTIVE]

    def evaluate_bar(self, ctx: WoodiesDecisionContext) -> Dict[str, Any]:
        """Full pass for persistence in current_state."""
        pre = self.run_pre_fire(ctx)
        active = self.run_active_trade()
        failed = [r.stage_id for r in pre if r.status == StageStatus.FAIL]
        pending = [r.stage_id for r in pre if r.status == StageStatus.PENDING]
        return {
            "pre_fire": [r.__dict__ for r in pre],
            "active_trade": [r.__dict__ for r in active],
            "ready_to_route": not failed and not pending and bool(ctx.patterns) and ctx.sizing != "reject",
            "failed_stages": failed,
            "pending_stages": pending,
            "entry_classification_spec": next(
                (r.details.get("spec_classification") for r in pre if r.stage_id == "A6"),
                None,
            ),
        }


def all_stage_ids() -> List[str]:
    return [s.stage_id for s in STAGE_DEFINITIONS]
