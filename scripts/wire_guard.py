#!/usr/bin/env python3
"""wire_guard — prove every command/exit/alert call site can actually be called.

THE BUG THIS EXISTS FOR (2026-08-14, live, real money):
`write_trade_command` declares `trade_id` as a REQUIRED keyword-only argument.
Three production call sites passed it inside `context` instead. Every one of
them raised TypeError before a single byte was written:

  • MAE_SCRATCH        — trade #682 was booked CLOSED / $0 while Sierra held
                         SHORT 4 @7799.25. Real loss −$75, booked $0.
  • TARGET_APPROACH_REALIZE — never executed once, ever. It announced twice on
                         trade 670, 21 minutes apart, which is impossible if the
                         first had closed anything.
  • the phone FLATTEN button — Michael's emergency kill switch.

Six regression tests were green the whole time. They were `inspect.getsource()`
string matches: they asserted the code LOOKED right and never called it.

This checker binds each call site's arguments against the real signature with
`inspect.Signature.bind`, at import time, without executing anything. A missing
required argument, a misspelled keyword, or a positional/keyword mismatch fails
here instead of at 20:00 on a live position.

It deliberately does NOT run the functions — a checker that places orders to
prove orders can be placed is not a checker.

    python3 scripts/wire_guard.py            # human output, exit 1 on a problem
    python3 scripts/wire_guard.py --json     # machine output for the pre-open gate
"""
from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ["backend"]

#: The functions whose call sites must be verifiable. These are the ones that
#: move money or raise an alarm — the places where a silent TypeError is
#: expensive. `module_path: function_name`.
GUARDED = {
    "backend.v9.services.sierra_command": [
        "write_trade_command", "write_flatten_account", "write_exit",
        "write_modify_stop", "write_place_bracket", "write_flatten_orphan",
    ],
    "backend.v9.services.phone_alert": ["push"],
    "backend.v9.services.ntfy_notify": ["on_fire", "on_close", "notify"],
    # 2026-08-18: added after the reconciler called on_trade_close(int) against
    # a def on_trade_close(trade: dict). Every call raised on the first
    # trade.get(), the except swallowed it at DEBUG, and two things silently did
    # not happen — the slot was not released and the close push was never sent.
    # The guard exists for exactly this shape, so the notifier's own callers
    # have to be inside it.
    "backend.v9.gateway.trading_gateway": ["TradingGateway.on_trade_close"],
}

# name → (module, signature)
_SIGS: Dict[str, Tuple[str, inspect.Signature]] = {}


def _load_signatures() -> List[str]:
    problems = []
    for mod_name, fns in GUARDED.items():
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:                       # pragma: no cover
            problems.append(f"cannot import {mod_name}: {e}")
            continue
        for fn in fns:
            # "Class.method" as well as a module-level function, so a guarded
            # signature can live on a class (2026-08-18).
            f, _short = mod, fn
            for part in fn.split("."):
                f = getattr(f, part, None)
                if f is None:
                    break
                _short = part
            if f is None:
                problems.append(f"{mod_name}.{fn} does not exist")
                continue
            fn = _short
            try:
                _sig = inspect.signature(f)
                # Call sites reach a method through an instance (`gw.close(x)`),
                # so `self` is already bound and must not be counted against
                # them — otherwise every correct call reads as "missing a
                # required argument".
                _params = list(_sig.parameters.values())
                if _params and _params[0].name in ("self", "cls"):
                    _sig = _sig.replace(parameters=_params[1:])
                _SIGS[fn] = (mod_name, _sig)
            except (TypeError, ValueError) as e:     # pragma: no cover
                problems.append(f"cannot read signature of {fn}: {e}")
    return problems


def _arg_placeholder(node: ast.AST) -> Any:
    """A stand-in value. Binding checks SHAPE, never values, so anything works."""
    return object()


def _check_call(call: ast.Call, fname: str, path: Path) -> Optional[str]:
    mod_name, sig = _SIGS[fname]
    args = [_arg_placeholder(a) for a in call.args]
    kwargs: Dict[str, Any] = {}
    star_kwargs = False
    for kw in call.keywords:
        if kw.arg is None:          # f(**something) — shape is unknowable here
            star_kwargs = True
            continue
        kwargs[kw.arg] = _arg_placeholder(kw.value)
    if star_kwargs:
        return None                 # honest skip rather than a false alarm
    if any(isinstance(a, ast.Starred) for a in call.args):
        return None
    try:
        sig.bind(*args, **kwargs)
    except TypeError as e:
        rel = path.relative_to(ROOT)
        return (f"{rel}:{call.lineno}  {fname}(...) → {e}\n"
                f"      signature: {fname}{sig}")
    return None


def _alias_map(tree: ast.AST) -> Dict[str, str]:
    """local name -> guarded name, for `from ... import write_x as _y`.

    Found by adversarial review 2026-08-17: the checker missed aliased imports,
    and the #682 call site is now written `write_flatten_account as _mae_write`
    — so the one site this tool exists for was being skipped.
    """
    out: Dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name in _SIGS and a.asname:
                    out[a.asname] = a.name
    return out


def scan() -> Tuple[List[str], int]:
    findings: List[str] = []
    checked = 0
    for d in SCAN_DIRS:
        for path in sorted((ROOT / d).rglob("*.py")):
            if "/tests/" in str(path) or path.name.startswith("test_"):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            aliases = _alias_map(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                name = (f.id if isinstance(f, ast.Name)
                        else f.attr if isinstance(f, ast.Attribute) else None)
                name = aliases.get(name, name)
                if name not in _SIGS:
                    continue
                checked += 1
                problem = _check_call(node, name, path)
                if problem:
                    findings.append(problem)
    return findings, checked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    load_problems = _load_signatures()
    findings, checked = scan()
    findings = load_problems + findings

    if args.json:
        print(json.dumps({
            "ok": not findings,
            "call_sites_checked": checked,
            "findings": findings,
        }, ensure_ascii=False, indent=2))
        return 1 if findings else 0

    print(f"wire_guard — {checked} call sites bound against "
          f"{len(_SIGS)} guarded signatures")
    if not findings:
        print("✅ every guarded call site can actually be called")
        return 0
    print(f"\n🔴 MISBOUND — {len(findings)} call site(s) would raise "
          f"TypeError before doing anything:\n")
    for f in findings:
        print("  " + f)
    print("\nThis is the #682 class: the command is never written, the failure is\n"
          "swallowed, and the books close over a live position.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
