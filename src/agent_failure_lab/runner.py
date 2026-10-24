from dataclasses import dataclass

from agent_failure_lab.errors import ScenarioContractError
from agent_failure_lab.registry import ScenarioRegistry
from agent_failure_lab.scenario import Outcome, Scenario, Variant
from agent_failure_lab.sim import LanguageModel


@dataclass(frozen=True, slots=True)
class PairResult:
    scenario: Scenario
    broken: Outcome
    fixed: Outcome

    @property
    def broken_reproduced(self) -> bool:
        return self.broken.failure_observed

    @property
    def fixed_still_fails(self) -> bool:
        return self.fixed.failure_observed

    @property
    def contract_holds(self) -> bool:
        """The broken variant shows the failure and the fixed variant does not."""
        return self.broken_reproduced and not self.fixed_still_fails


def _check_variant(scenario: Scenario, variant: Variant, outcome: Outcome) -> Outcome:
    if outcome.variant is not variant:
        raise ScenarioContractError(
            f"'{scenario.slug}' was asked for the {variant.value} variant "
            f"but returned a {outcome.variant.value} outcome"
        )
    return outcome


def run_scenario(scenario: Scenario, variant: Variant) -> Outcome:
    return _check_variant(scenario, variant, scenario.run(variant))


def run_scenario_live(scenario: Scenario, variant: Variant, model: LanguageModel) -> Outcome:
    return _check_variant(scenario, variant, scenario.run_live(variant, model))


def run_pair(scenario: Scenario) -> PairResult:
    return PairResult(
        scenario=scenario,
        broken=run_scenario(scenario, Variant.BROKEN),
        fixed=run_scenario(scenario, Variant.FIXED),
    )


def run_all(registry: ScenarioRegistry) -> list[PairResult]:
    return [run_pair(scenario) for scenario in registry.scenarios()]
