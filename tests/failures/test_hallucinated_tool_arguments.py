from agent_failure_lab.failures.hallucinated_tool_arguments import SCENARIO
from agent_failure_lab.scenario import Variant
from agent_failure_lab.sim import EventKind


def test_broken_variant_stores_a_value_that_is_not_a_real_option() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert outcome.failure_observed
    assert outcome.metrics["invalid_values_stored"] == 1
    assert outcome.metrics["final_speed"] == "next_day"
    assert "now set" in outcome.findings[0]


def test_fixed_variant_ends_with_a_valid_value() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert not outcome.failure_observed
    assert outcome.metrics["invalid_values_stored"] == 0
    assert outcome.metrics["final_speed"] == "overnight"


def test_fixed_variant_rejects_the_first_call_before_the_tool_runs() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert outcome.metrics["tool_calls"] == 1
    (rejection,) = outcome.trace.of_kind(EventKind.GUARD)
    assert "next_day" in rejection.summary


def test_the_error_the_model_receives_lists_the_allowed_values() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    errors = [
        e.data["content"]
        for e in outcome.trace.of_kind(EventKind.TOOL_RESULT)
        if e.data["is_error"]
    ]
    assert len(errors) == 1
    assert '["standard", "express", "overnight"]' in errors[0]
