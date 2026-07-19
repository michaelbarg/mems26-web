"""Anti-tautological contracts for morning-protocol stage E."""
from scripts import fire_drill
from scripts.fire_readiness_real import (
    GateVerdict,
    SetupVerdict,
    evaluate_readiness,
)


def _stub(*, would_fire=False, blocked_by=None, unresolved_by=None):
    def evaluate(setup, **_context):
        status = "PASS" if would_fire else ("BLOCK" if blocked_by else "NOT_EVALUATED")
        gate = blocked_by or unresolved_by or "test_gate"
        return SetupVerdict(
            setup=setup,
            gates=[GateVerdict(gate, status, "fixture")],
            would_fire=would_fire,
            blocked_by=blocked_by,
            unresolved_by=unresolved_by,
        )

    return evaluate


def test_zero_real_setups_is_indeterminate():
    result = evaluate_readiness([])

    assert result.status == "INDETERMINATE"
    assert result.exit_code == 2
    assert "0 real RTH setups" in result.reason


def test_all_real_setups_blocked_is_no_go():
    setups = [{"id": 1}, {"id": 2}]

    result = evaluate_readiness(
        setups,
        evaluator=_stub(blocked_by="daytype_playbook"),
    )

    assert result.status == "NO-GO"
    assert result.exit_code == 1
    assert [row.blocked_by for row in result.setups] == [
        "daytype_playbook",
        "daytype_playbook",
    ]


def test_one_would_fire_real_setup_is_go():
    setups = [{"id": 1}]

    result = evaluate_readiness(setups, evaluator=_stub(would_fire=True))

    assert result.status == "GO"
    assert result.exit_code == 0
    assert result.setups[0].would_fire is True


def test_unresolved_active_gate_is_not_silent_go():
    result = evaluate_readiness(
        [{"id": 1}],
        evaluator=_stub(unresolved_by="cont_trend_filter"),
    )

    assert result.status == "INDETERMINATE"
    assert result.exit_code == 2


def test_fire_drill_flag_off_output_and_stage_order_unchanged(monkeypatch, capsys):
    """Unset flag must not import/run stage E or alter the A-C no-live transcript."""
    calls = []

    def stage(name):
        def run():
            calls.append(name)
            print(name)

        return run

    monkeypatch.delenv("FIRE_DRILL_STAGE_E", raising=False)
    monkeypatch.setattr(fire_drill, "stage_a", stage("A"))
    monkeypatch.setattr(fire_drill, "stage_b", stage("B"))
    monkeypatch.setattr(fire_drill, "stage_c", stage("C"))
    monkeypatch.setattr(
        fire_drill,
        "stage_e",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("stage E ran while flag OFF")),
    )
    monkeypatch.setattr(fire_drill.sys, "argv", ["fire_drill.py", "--no-live"])
    fire_drill.FAILS.clear()

    assert fire_drill.main() == 0

    assert calls == ["A", "B", "C"]
    assert capsys.readouterr().out == (
        "🔫 FIRE DRILL — ירי-יבש של שרשרת ההחלטה\n"
        "\n"
        "A\n"
        "B\n"
        "C\n"
        "\n"
        "🟢 GO — כל שרשרת ההחלטה כשרה לירי.\n"
    )
