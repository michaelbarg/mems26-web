"""§5+§7 fix: _resolve_live_cls() replaces broken getattr(app, ...).

The gateway used getattr(app, "state", None) at :1812 and :2642.
`app` was not in scope → NameError → except → accepted_break=None always.
Fix: use _resolve_live_cls() which imports app from backend.main.

Mutation: replacing _resolve_live_cls() back with getattr(app, ...) → fails.
"""
import subprocess
import unittest


class TestAppResolveFix(unittest.TestCase):

    def test_no_bare_app_getattr_in_new_code(self):
        """No getattr(app, ...) with bare `app` in §5/§7 code paths."""
        out = subprocess.run(
            ["grep", "-n", 'getattr(app,', "backend/v9/gateway/trading_gateway.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        # There should be ZERO bare `getattr(app,` — all should use _resolve_live_cls
        # or getattr(_main_app, ...) inside the helper
        for line in out.stdout.strip().split("\n"):
            if not line:
                continue
            # Lines within _resolve_live_cls itself are OK (they use _main_app)
            self.assertNotIn("getattr(app,", line,
                              f"Bare getattr(app, ...) found: {line}")

    def test_resolve_live_cls_used_at_elq_and_rg(self):
        """_resolve_live_cls() is used at both §5 and §7 callsites."""
        out = subprocess.run(
            ["grep", "-n", "_resolve_live_cls",
             "backend/v9/gateway/trading_gateway.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        lines = out.stdout.strip().split("\n")
        # At least: def + 2 existing callers + 2 new callers (§5, §7) = 5+
        call_lines = [l for l in lines if "def " not in l and l.strip()]
        self.assertGreaterEqual(len(call_lines), 4,
                                 f"_resolve_live_cls must have >=4 call sites, "
                                 f"got {len(call_lines)}")

    def test_mutation_replacing_back_fails(self):
        """MUTATION: the old pattern `getattr(app, "state", None)` must not
        appear as a standalone call (only inside _resolve_live_cls helper)."""
        out = subprocess.run(
            ["grep", "-c", 'getattr(app, "state"',
             "backend/v9/gateway/trading_gateway.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        count = int(out.stdout.strip())
        # Should be 0 outside of _resolve_live_cls (which uses _main_app, not app)
        self.assertEqual(count, 0,
                          "getattr(app, \"state\"...) must not appear — "
                          "use _resolve_live_cls()")


if __name__ == "__main__":
    unittest.main()
