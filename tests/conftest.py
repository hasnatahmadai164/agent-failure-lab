import os
from collections.abc import Callable

import pytest

from agent_failure_lab.scenario import Outcome, ScenarioDefinition, Variant
from agent_failure_lab.sim import ManualClock, Trace


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("RUN_LIVE") == "1":
        return
    skip_live = pytest.mark.skip(reason="set RUN_LIVE=1 to run live tests")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture
def make_scenario() -> Callable[..., ScenarioDefinition]:
    def factory(
        slug: str = "example-failure",
        *,
        category: str = "side-effects",
        summary: str = "Retry charges twice",
        broken_fails: bool = True,
        fixed_fails: bool = False,
    ) -> ScenarioDefinition:
        def outcome(variant: Variant, failure_observed: bool) -> Outcome:
            return Outcome(variant, failure_observed, Trace(ManualClock()))

        return ScenarioDefinition(
            slug=slug,
            title=slug.replace("-", " ").title(),
            category=category,
            summary=summary,
            broken=lambda: outcome(Variant.BROKEN, broken_fails),
            fixed=lambda: outcome(Variant.FIXED, fixed_fails),
        )

    return factory
