from collections.abc import Callable

import pytest

from agent_failure_lab.errors import LiveNotSupportedError, ScenarioContractError
from agent_failure_lab.failures.duplicate_side_effect import SCENARIO as DUPLICATE
from agent_failure_lab.failures.duplicate_side_effect.world import billing_agent
from agent_failure_lab.registry import build_registry
from agent_failure_lab.runner import run_scenario_live
from agent_failure_lab.scenario import Outcome, ScenarioDefinition, Variant
from agent_failure_lab.sim import ManualClock, Reply, ScriptedLLM, Trace

LIVE_SLUGS = [
    "duplicate-side-effect",
    "tool-output-injection",
    "hallucinated-tool-arguments",
    "parallel-tool-race",
]


def _live_scenarios() -> list[ScenarioDefinition]:
    return [s for s in build_registry().scenarios() if s.supports_live]  # type: ignore[misc]


def test_the_failures_that_can_run_against_a_real_model_are_the_ones_judged_by_their_effects() -> (
    None
):
    assert [s.slug for s in _live_scenarios()] == LIVE_SLUGS


@pytest.mark.parametrize("variant", list(Variant))
@pytest.mark.parametrize(
    "slug", ["duplicate-side-effect", "tool-output-injection", "hallucinated-tool-arguments"]
)
def test_a_model_that_answers_at_once_leaves_the_world_untouched(
    slug: str, variant: Variant
) -> None:
    scenario = build_registry().get(slug)

    outcome = scenario.run_live(variant, ScriptedLLM([Reply("Nothing to do.")]))

    assert outcome.variant is variant
    assert not outcome.failure_observed


@pytest.mark.parametrize("variant", list(Variant))
def test_a_model_that_never_tags_the_ticket_is_judged_by_the_missing_tag(variant: Variant) -> None:
    scenario = build_registry().get("parallel-tool-race")

    outcome = scenario.run_live(variant, ScriptedLLM([Reply("Nothing to do.")]))

    assert outcome.variant is variant
    assert outcome.failure_observed


def test_running_live_with_the_scripted_billing_model_gives_the_same_result_as_the_normal_run() -> (
    None
):
    model = ScriptedLLM([billing_agent], repeat_last=True)

    live = DUPLICATE.run_live(Variant.BROKEN, model)
    normal = DUPLICATE.run(Variant.BROKEN)

    assert dict(live.metrics) == dict(normal.metrics)
    assert live.failure_observed


def test_a_failure_without_a_live_variant_says_so() -> None:
    runaway = build_registry().get("runaway-cost")

    assert not runaway.supports_live
    with pytest.raises(LiveNotSupportedError, match="runaway-cost"):
        runaway.run_live(Variant.BROKEN, ScriptedLLM([Reply("x")]))


def test_a_live_run_that_returns_the_wrong_variant_is_rejected(
    make_scenario: Callable[..., ScenarioDefinition],
) -> None:
    def wrong(model: object) -> Outcome:
        return Outcome(Variant.FIXED, False, Trace(ManualClock()))

    scenario = make_scenario()
    mismatched = ScenarioDefinition(
        slug="mismatched-live",
        title=scenario.title,
        category=scenario.category,
        summary=scenario.summary,
        broken=scenario.broken,
        fixed=scenario.fixed,
        broken_live=wrong,
        fixed_live=wrong,
    )

    with pytest.raises(ScenarioContractError, match="mismatched-live"):
        run_scenario_live(mismatched, Variant.BROKEN, ScriptedLLM([Reply("x")]))
