from collections.abc import Callable

import pytest

from agent_failure_lab.errors import ScenarioContractError
from agent_failure_lab.registry import ScenarioRegistry
from agent_failure_lab.runner import run_all, run_pair, run_scenario
from agent_failure_lab.scenario import Outcome, ScenarioDefinition, Variant
from agent_failure_lab.sim import ManualClock, Trace

MakeScenario = Callable[..., ScenarioDefinition]


def test_a_definition_runs_the_function_for_the_requested_variant(
    make_scenario: MakeScenario,
) -> None:
    scenario = make_scenario()

    assert scenario.run(Variant.BROKEN).variant is Variant.BROKEN
    assert scenario.run(Variant.FIXED).variant is Variant.FIXED


def test_run_scenario_returns_the_outcome_for_the_requested_variant(
    make_scenario: MakeScenario,
) -> None:
    outcome = run_scenario(make_scenario(), Variant.BROKEN)

    assert outcome.failure_observed


def test_run_scenario_rejects_an_outcome_for_the_wrong_variant() -> None:
    def wrong() -> Outcome:
        return Outcome(Variant.FIXED, False, Trace(ManualClock()))

    scenario = ScenarioDefinition(
        slug="mismatched",
        title="Mismatched",
        category="side-effects",
        summary="Returns the wrong variant",
        broken=wrong,
        fixed=wrong,
    )

    with pytest.raises(ScenarioContractError, match="mismatched"):
        run_scenario(scenario, Variant.BROKEN)


def test_the_contract_holds_when_broken_fails_and_fixed_does_not(
    make_scenario: MakeScenario,
) -> None:
    result = run_pair(make_scenario())

    assert result.contract_holds
    assert result.broken_reproduced
    assert not result.fixed_still_fails


@pytest.mark.parametrize(
    ("broken_fails", "fixed_fails"),
    [(False, False), (True, True), (False, True)],
)
def test_the_contract_is_broken_unless_only_the_broken_variant_fails(
    make_scenario: MakeScenario, broken_fails: bool, fixed_fails: bool
) -> None:
    result = run_pair(make_scenario(broken_fails=broken_fails, fixed_fails=fixed_fails))

    assert not result.contract_holds
    assert result.fixed_still_fails is fixed_fails


def test_run_all_returns_one_result_per_scenario_in_registration_order(
    make_scenario: MakeScenario,
) -> None:
    registry = ScenarioRegistry()
    registry.register(make_scenario("second-slug"))
    registry.register(make_scenario("first-slug"))

    results = run_all(registry)

    assert [result.scenario.slug for result in results] == ["second-slug", "first-slug"]
