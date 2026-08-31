"""T-182: safe_execute() must REJECT a Mapping instead of silently writing nothing.

Live finding 2026-08-30: `scripts/t160_pnl_trust_audit.py --apply` called
safe_execute with `:named` SQL and a DICT of binds. safe_execute takes
POSITIONAL `?` params. The dict reached _convert_positional_to_named, whose
mismatch branch does `dict(enumerate(params))` — and enumerate() over a dict
walks its KEYS, so {"q": ..., "id": ...} became {0: "q", 1: "id"}. The engine
raised "A value is required for bind parameter 'q'", the broad `except` in
safe_execute swallowed it and returned None, and the script printed
"Marked 62 trades as pnl_trusted=false" while ZERO rows were written.

The silent-write-loss is the dangerous half: a remediation script reported
success on an empty write. safe_execute now raises TypeError on a Mapping.

Anti-tautological: test_dict_is_mangled_without_the_guard reproduces the
ACTUAL mangling through the real _convert_positional_to_named, so the test
documents the mechanism rather than restating the guard. Removing the
isinstance(params, Mapping) raise turns test_dict_params_raises RED.
"""
import ast
import os

import pytest

from backend.v9.db import safe_writer
from backend.v9.db.safe_writer import _convert_positional_to_named, safe_execute

REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


# ---------------------------------------------------------------- the guard

def test_dict_params_raises():
    """A dict of :named binds must fail LOUD, not write zero rows quietly."""
    with pytest.raises(TypeError) as exc:
        safe_execute(
            "UPDATE v9_trades SET quality = :q WHERE id = ?",
            {"q": '{"pnl_trusted": false}', "id": 939},
        )
    msg = str(exc.value)
    assert "POSITIONAL" in msg
    assert "T-182" in msg


@pytest.mark.parametrize("mapping", [{}, {"a": 1}])
def test_any_mapping_raises_including_empty(mapping):
    """Empty dict too — it is still the wrong calling convention."""
    with pytest.raises(TypeError):
        safe_execute("UPDATE t SET a = ? WHERE b = ?", mapping)


def test_tuple_params_still_work(monkeypatch):
    """The positional path is untouched: tuple params reach the engine."""
    captured = {}

    class _FakeResult:
        lastrowid = 7

    class _FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, stmt, params):
            captured["sql"] = str(stmt)
            captured["params"] = params
            return _FakeResult()

        def commit(self):
            captured["committed"] = True

    class _FakeEngine:
        url = "postgresql://localhost/mems26"

        def connect(self):
            return _FakeConn()

    monkeypatch.setattr(safe_writer, "_get_engine", lambda db_path=None: _FakeEngine())

    out = safe_execute("UPDATE v9_trades SET quality = ? WHERE id = ?", ('{"x":1}', 939))

    assert out == 7
    assert captured["committed"] is True
    # positional binds were converted to :p0/:p1 with the VALUES, not the keys
    assert captured["params"] == {"p0": '{"x":1}', "p1": 939}
    assert ":p0" in captured["sql"] and ":p1" in captured["sql"]


def test_list_params_still_work(monkeypatch):
    """Sequences other than tuple are still a valid positional convention."""
    monkeypatch.setattr(safe_writer, "_get_engine", lambda db_path=None: _StubEngine())
    assert safe_execute("UPDATE t SET a = ? WHERE b = ?", ["x", 1]) == 0


class _StubEngine:
    url = "postgresql://localhost/mems26"

    def connect(self):
        class _C:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return False

            def execute(self_inner, stmt, params):
                class _R:
                    lastrowid = 0

                return _R()

            def commit(self_inner):
                pass

        return _C()


# ------------------------------------------------- the mechanism it prevents

def test_dict_is_mangled_without_the_guard():
    """Documents WHY the guard exists: enumerate() over a dict walks its KEYS.

    This calls the converter directly (bypassing the guard) to prove the
    mangling is real — the binds become {0: 'q', 1: 'id'}, i.e. the parameter
    NAMES as values, and the actual payload is gone. Any engine given this
    raises, and the caller's `except` used to swallow it.
    """
    sql = "UPDATE v9_trades SET quality = :q WHERE id = :id"
    out_sql, binds = _convert_positional_to_named(
        sql, {"q": '{"pnl_trusted": false}', "id": 939}
    )
    assert out_sql == sql              # no `?` to convert
    assert binds == {0: "q", 1: "id"}  # the KEYS, not the values
    assert '{"pnl_trusted": false}' not in binds.values()
    assert 939 not in binds.values()


# ------------------------------------------------ no caller may regress this

def _call_sites():
    """AST-sweep every safe_execute call site in the repo."""
    skip = {".git", "node_modules", "__pycache__", ".venv", "venv", ".next"}
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", None)
                if name != "safe_execute":
                    continue
                arg = node.args[1] if len(node.args) >= 2 else next(
                    (k.value for k in node.keywords if k.arg == "params"), None
                )
                yield os.path.relpath(path, REPO_ROOT), node.lineno, arg


def test_no_caller_passes_a_dict_literal():
    """The sweep that justified raising — re-run every time, so it can't rot.

    If someone adds a dict-passing caller, this fails HERE (at test time)
    instead of at runtime inside a swallowed except.
    """
    offenders = [
        f"{path}:{lineno}"
        for path, lineno, arg in _call_sites()
        if isinstance(arg, (ast.Dict, ast.DictComp))
        and "tests/" not in path.replace(os.sep, "/")
    ]
    assert offenders == [], (
        "safe_execute() called with a dict — it takes POSITIONAL `?` params "
        f"and will now raise TypeError at runtime: {offenders}"
    )


def test_sweep_actually_finds_call_sites():
    """Guards the guard: a broken sweep must not pass by finding nothing."""
    sites = list(_call_sites())
    assert len(sites) >= 30, f"AST sweep found only {len(sites)} call sites"
