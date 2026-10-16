from collections.abc import Callable

import pytest

from agent_failure_lab.errors import (
    DuplicateScenarioError,
    InvalidSlugError,
    UnknownScenarioError,
)
from agent_failure_lab.registry import ScenarioRegistry, build_registry
from agent_failure_lab.scenario import ScenarioDefinition

MakeScenario = Callable[..., ScenarioDefinition]


def test_scenarios_keep_registration_order(make_scenario: MakeScenario) -> None:
    registry = ScenarioRegistry()
    registry.register(make_scenario("second-slug"))
    registry.register(make_scenario("first-slug"))

    assert [scenario.slug for scenario in registry.scenarios()] == ["second-slug", "first-slug"]


def test_get_returns_the_registered_scenario(make_scenario: MakeScenario) -> None:
    registry = ScenarioRegistry()
    scenario = make_scenario("duplicate-side-effect")
    registry.register(scenario)

    assert registry.get("duplicate-side-effect") is scenario


def test_get_unknown_slug_raises_with_the_slug_in_the_message() -> None:
    registry = ScenarioRegistry()

    with pytest.raises(UnknownScenarioError, match="missing-slug"):
        registry.get("missing-slug")


def test_register_rejects_a_duplicate_slug(make_scenario: MakeScenario) -> None:
    registry = ScenarioRegistry()
    registry.register(make_scenario("same-slug"))

    with pytest.raises(DuplicateScenarioError, match="same-slug"):
        registry.register(make_scenario("same-slug"))


@pytest.mark.parametrize(
    "slug",
    [
        "",
        "Upper-Case",
        "has_underscore",
        "-leading",
        "trailing-",
        "double--hyphen",
        "1-digit-first",
    ],
)
def test_register_rejects_a_malformed_slug(make_scenario: MakeScenario, slug: str) -> None:
    registry = ScenarioRegistry()

    with pytest.raises(InvalidSlugError):
        registry.register(make_scenario(slug))


def test_register_accepts_slugs_with_digits_after_the_first_letter(
    make_scenario: MakeScenario,
) -> None:
    registry = ScenarioRegistry()

    registry.register(make_scenario("step-2-retry"))

    assert registry.get("step-2-retry").slug == "step-2-retry"


def test_build_registry_registers_every_builtin_scenario_with_a_unique_valid_slug() -> None:
    registry = build_registry()

    slugs = [scenario.slug for scenario in registry.scenarios()]
    assert len(slugs) == len(set(slugs))
