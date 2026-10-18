from agent_failure_lab.failures.infinite_tool_loop import SCENARIO
from agent_failure_lab.failures.infinite_tool_loop.world import MAX_STEPS
from agent_failure_lab.scenario import Variant
from agent_failure_lab.sim import EventKind


def test_broken_variant_runs_to_the_step_limit_calling_the_same_tool() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert outcome.failure_observed
    assert outcome.metrics["steps"] == MAX_STEPS
    assert outcome.metrics["tool_calls"] == MAX_STEPS
    assert outcome.metrics["stop_reason"] == "step_limit"


def test_fixed_variant_is_stopped_by_a_guard_long_before_the_step_limit() -> None:
    broken = SCENARIO.run(Variant.BROKEN)
    fixed = SCENARIO.run(Variant.FIXED)

    assert not fixed.failure_observed
    assert fixed.metrics["stop_reason"] == "guard_stop"
    assert fixed.metrics["steps"] < MAX_STEPS
    assert fixed.metrics["total_tokens"] < broken.metrics["total_tokens"]


def test_fixed_variant_lets_three_calls_run_then_warns_then_stops() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert outcome.metrics["tool_calls"] == 3
    warnings = [e.summary for e in outcome.trace.of_kind(EventKind.GUARD)]
    assert warnings[0].startswith("LoopDetector: blocked")
    assert warnings[1].startswith("LoopDetector: stopped the run")
