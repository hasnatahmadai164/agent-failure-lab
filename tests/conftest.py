import os
from collections.abc import Callable, Sequence

import pytest

from agent_failure_lab.scenario import Outcome, ScenarioDefinition, Variant
from agent_failure_lab.sim import (
    LanguageModel,
    ManualClock,
    Message,
    RunState,
    ToolSpec,
    Trace,
    Usage,
)


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
        fix: str = "Idempotency keys",
        guards: tuple[str, ...] = ("IdempotencyKeys",),
        broken_fails: bool = True,
        fixed_fails: bool = False,
        live: bool = False,
    ) -> ScenarioDefinition:
        def outcome(variant: Variant, failure_observed: bool) -> Outcome:
            metrics = {"charges": 2 if failure_observed else 1}
            return Outcome(variant, failure_observed, Trace(ManualClock()), metrics)

        def live_outcome(variant: Variant) -> Callable[[LanguageModel], Outcome]:
            return lambda model: outcome(variant, variant is Variant.BROKEN)

        return ScenarioDefinition(
            slug=slug,
            title=slug.replace("-", " ").title(),
            category=category,
            summary=summary,
            fix=fix,
            guards=guards,
            broken=lambda: outcome(Variant.BROKEN, broken_fails),
            fixed=lambda: outcome(Variant.FIXED, fixed_fails),
            broken_live=live_outcome(Variant.BROKEN) if live else None,
            fixed_live=live_outcome(Variant.FIXED) if live else None,
        )

    return factory


@pytest.fixture
def make_run() -> Callable[..., RunState]:
    """Build a RunState so a guard's hooks can be called without running an agent."""

    def factory(
        *,
        specs: Sequence[ToolSpec] = (),
        history: Sequence[Message] = (),
        usage: Usage | None = None,
        step: int = 1,
    ) -> RunState:
        clock = ManualClock()
        state = RunState(clock=clock, trace=Trace(clock), tool_specs=specs, history=history)
        state.step = step
        if usage is not None:
            state.usage = usage
        return state

    return factory
