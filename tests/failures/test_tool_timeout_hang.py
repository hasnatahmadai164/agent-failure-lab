from agent_failure_lab.failures.tool_timeout_hang import SCENARIO
from agent_failure_lab.failures.tool_timeout_hang.world import HANG_SECONDS, RUN_SLA_SECONDS
from agent_failure_lab.scenario import Variant
from agent_failure_lab.sim import EventKind


def test_broken_variant_waits_out_the_full_hang_and_misses_the_time_limit() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert outcome.failure_observed
    assert outcome.metrics["elapsed_seconds"] == HANG_SECONDS
    assert outcome.metrics["elapsed_seconds"] > RUN_SLA_SECONDS


def test_fixed_variant_gives_up_on_the_slow_tool_and_finishes_within_the_limit() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert not outcome.failure_observed
    assert outcome.metrics["elapsed_seconds"] == 5
    assert outcome.metrics["answered"] is True


def test_fixed_variant_returns_a_partial_summary_that_says_what_is_missing() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert "sales are ready" in str(outcome.metrics["final_answer"])
    assert "Inventory data is missing" in str(outcome.metrics["final_answer"])


def test_fixed_variant_tells_the_model_to_carry_on_with_what_it_has() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    errors = [e.data["content"] for e in outcome.trace.of_kind(EventKind.TOOL_RESULT)]
    assert any("cancelled after 5s" in content for content in errors)
    assert any("say clearly what is missing" in content for content in errors)
