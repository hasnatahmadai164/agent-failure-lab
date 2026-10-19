from agent_failure_lab.failures.runaway_cost import SCENARIO
from agent_failure_lab.failures.runaway_cost.world import COST_CEILING, MAX_STEPS
from agent_failure_lab.scenario import Variant
from agent_failure_lab.sim import EventKind


def test_broken_variant_runs_to_the_step_cap_and_passes_the_cost_ceiling() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert outcome.failure_observed
    assert outcome.metrics["steps"] == MAX_STEPS
    assert outcome.metrics["stop_reason"] == "step_limit"
    assert outcome.metrics["cost_units"] > COST_CEILING


def test_fixed_variant_stops_before_the_ceiling_is_passed() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert not outcome.failure_observed
    assert outcome.metrics["stop_reason"] == "guard_stop"
    assert outcome.metrics["cost_units"] <= COST_CEILING
    assert outcome.metrics["steps"] < MAX_STEPS


def test_the_searches_all_differ_so_a_loop_detector_would_not_have_helped() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    queries = [e.data["arguments"]["query"] for e in outcome.trace.of_kind(EventKind.TOOL_CALL)]
    assert len(set(queries)) == len(queries)


def test_each_step_costs_more_than_the_one_before() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    prompts = [e.data["prompt_tokens"] for e in outcome.trace.of_kind(EventKind.MODEL)]
    assert prompts == sorted(prompts)
    assert prompts[-1] > prompts[0]
