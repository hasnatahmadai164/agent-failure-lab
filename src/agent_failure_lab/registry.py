import re

from agent_failure_lab.errors import (
    DuplicateScenarioError,
    InvalidSlugError,
    UnknownScenarioError,
)
from agent_failure_lab.failures import builtin_scenarios
from agent_failure_lab.scenario import Scenario

_SLUG_PATTERN = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")


def validate_slug(slug: str) -> None:
    if not _SLUG_PATTERN.fullmatch(slug):
        raise InvalidSlugError(slug)


def module_name(slug: str) -> str:
    """The Python package name for a slug, since a hyphen cannot appear in an import."""
    return slug.replace("-", "_")


class ScenarioRegistry:
    def __init__(self) -> None:
        self._by_slug: dict[str, Scenario] = {}

    def register(self, scenario: Scenario) -> None:
        validate_slug(scenario.slug)
        if scenario.slug in self._by_slug:
            raise DuplicateScenarioError(scenario.slug)
        self._by_slug[scenario.slug] = scenario

    def get(self, slug: str) -> Scenario:
        try:
            return self._by_slug[slug]
        except KeyError:
            raise UnknownScenarioError(slug) from None

    def scenarios(self) -> list[Scenario]:
        return list(self._by_slug.values())


def build_registry() -> ScenarioRegistry:
    registry = ScenarioRegistry()
    for scenario in builtin_scenarios():
        registry.register(scenario)
    return registry
