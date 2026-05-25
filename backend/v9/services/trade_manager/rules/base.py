"""RiskRule registry — S2_TRADEMGR_HOOKS_V1 §2.1-§2.4.

Provides:
  - Layer4Context: frozen dataclass passed to every rule's evaluate()
  - RiskRule: ABC that each concrete rule subclasses
  - register_rule(*, order): decorator that registers a RiskRule subclass
  - get_registered_rules(): returns list of instances sorted by order
  - unregister_rule(cls): removes a rule class from the registry
  - log_skipped_rule: public helper using _SkipLogLimiter
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Type

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phase constants
# ---------------------------------------------------------------------------
PRE_TIGHTEN = "PRE_TIGHTEN"
POST_TIGHTEN = "POST_TIGHTEN"


# ---------------------------------------------------------------------------
# §2.1 Layer4Context
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Layer4Context:
    """Immutable snapshot passed to every RiskRule.evaluate() call.

    All fields are Optional — rules must guard against None.
    """

    cci_history: Optional[List[float]] = None
    direction_change_event: Optional[dict] = None
    swi: Optional[dict] = None
    current_day_type: Optional[str] = None


# ---------------------------------------------------------------------------
# §2.2 RiskRule ABC
# ---------------------------------------------------------------------------
class RiskRule(ABC):
    """Abstract base class for every Layer 4 risk rule.

    Subclasses MUST set:
        name  : str  — unique identifier used in audit payloads
        phase : str  — PRE_TIGHTEN | POST_TIGHTEN
    """

    name: str
    phase: str = PRE_TIGHTEN

    @abstractmethod
    def evaluate(self, trade: dict, ctx: Layer4Context) -> Optional[Dict[str, Any]]:
        """Evaluate rule given the trade dict and current Layer4Context.

        Args:
            trade: dict representation of the active trade.
            ctx:   frozen Layer4Context snapshot.

        Returns:
            Action dict (with at minimum ``"action"`` key) or None.
        """


# ---------------------------------------------------------------------------
# §2.3 Registry — List[Tuple[int, RiskRule]] per spec (NOT a dict)
# ---------------------------------------------------------------------------
_REGISTRY: List[Tuple[int, RiskRule]] = []


def register_rule(*, order: int):
    """Class decorator that instantiates and registers a RiskRule subclass.

    Args:
        order: integer sort key; lower = earlier in evaluation loop.

    Raises:
        TypeError:  if the decorated class is not a subclass of RiskRule.
        ValueError: if a rule with the same name is already registered.
    """
    def decorator(cls: Type[RiskRule]) -> Type[RiskRule]:
        if not (isinstance(cls, type) and issubclass(cls, RiskRule)):
            raise TypeError(
                f"register_rule: {cls!r} must be a subclass of RiskRule"
            )

        instance = cls()
        # Guard duplicate names
        for _ord, existing in _REGISTRY:
            if existing.name == instance.name:
                raise ValueError(
                    f"register_rule: duplicate rule name {instance.name!r} "
                    f"(already registered at order={_ord})"
                )
        _REGISTRY.append((order, instance))
        return cls

    return decorator


def get_registered_rules() -> List[RiskRule]:
    """Return registered rule instances sorted ascending by order."""
    return [rule for _order, rule in sorted(_REGISTRY, key=lambda t: t[0])]


def unregister_rule(cls: Type[RiskRule]) -> None:
    """Remove all registry entries whose instance is of type *cls*.

    Takes the CLASS (not a name string) per spec §2.3.
    Silently no-ops if the class is not currently registered.

    Uses in-place mutation to preserve the identity of the list object so that
    any code that captured a reference to _REGISTRY sees the updated contents.
    """
    to_remove = [
        (order, rule)
        for order, rule in _REGISTRY
        if isinstance(rule, cls)
    ]
    for item in to_remove:
        _REGISTRY.remove(item)


# ---------------------------------------------------------------------------
# §2.4 _SkipLogLimiter — rate-limits skip-log messages per rule
# ---------------------------------------------------------------------------
_SKIP_LOG_INTERVAL = 60.0  # seconds between repeated skip logs per rule


class _SkipLogLimiter:
    """Suppresses repeated skip-log messages within a cooldown window."""

    def __init__(self, interval: float = _SKIP_LOG_INTERVAL) -> None:
        self._interval = interval
        self._last: Dict[str, float] = {}

    def should_log(self, rule_name: str) -> bool:
        """Return True if enough time has passed to emit a log for *rule_name*."""
        now = time.monotonic()
        # Default to negative infinity so first call always passes
        last = self._last.get(rule_name, -self._interval)
        if now - last >= self._interval:
            self._last[rule_name] = now
            return True
        return False

    def reset(self, rule_name: Optional[str] = None) -> None:
        """Reset limiter state.  Pass rule_name to reset only that entry."""
        if rule_name is None:
            self._last.clear()
        else:
            self._last.pop(rule_name, None)


# Module-level singleton used by log_skipped_rule
_skip_limiter = _SkipLogLimiter()


def log_skipped_rule(rule_name: str, reason: str) -> None:
    """Emit a rate-limited DEBUG log when a rule is skipped.

    Args:
        rule_name: the rule's ``name`` attribute.
        reason:    short explanation (e.g. "cci_history=None").
    """
    if _skip_limiter.should_log(rule_name):
        logger.debug("[RiskRule] skipped %s: %s", rule_name, reason)
