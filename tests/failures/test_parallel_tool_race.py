from agent_failure_lab.failures.parallel_tool_race import SCENARIO
from agent_failure_lab.scenario import Variant
from agent_failure_lab.sim import EventKind


def test_broken_variant_loses_one_of_the_two_updates() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert outcome.failure_observed
    assert outcome.metrics["tags_wanted"] == 2
    assert outcome.metrics["tags_saved"] == 1
    assert outcome.metrics["lost_updates"] == 1


def test_broken_variant_still_tells_the_user_that_both_tags_were_added() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert "Both tags are on T-77." in outcome.findings[0]
    assert outcome.metrics["model_steps"] == 2


def test_fixed_variant_ends_with_both_tags_on_the_ticket() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert not outcome.failure_observed
    assert outcome.metrics["tags_saved"] == 2
    assert outcome.metrics["lost_updates"] == 0


def test_fixed_variant_holds_back_the_second_call_and_runs_it_in_the_next_step() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert outcome.metrics["model_steps"] == 3
    (held,) = outcome.trace.of_kind(EventKind.GUARD)
    assert held.summary.startswith("ConflictSerializer: held back add_tag")
    assert held.step == 1
