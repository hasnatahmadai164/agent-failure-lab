import pytest

from agent_failure_lab.errors import DuplicateScenarioError, UnknownScenarioError
from agent_failure_lab.registry import ScenarioInfo, ScenarioRegistry


def _info(slug: str) -> ScenarioInfo:
    return ScenarioInfo(slug=slug, title=slug.title(), category="side-effects", summary="summary")


def test_scenarios_keep_registration_order() -> None:
    registry = ScenarioRegistry()
    registry.register(_info("second-slug"))
    registry.register(_info("first-slug"))

    assert [info.slug for info in registry.scenarios()] == ["second-slug", "first-slug"]


def test_get_returns_the_registered_scenario() -> None:
    registry = ScenarioRegistry()
    info = _info("duplicate-side-effect")
    registry.register(info)

    assert registry.get("duplicate-side-effect") == info


def test_get_unknown_slug_raises_with_the_slug_in_the_message() -> None:
    registry = ScenarioRegistry()

    with pytest.raises(UnknownScenarioError, match="missing-slug"):
        registry.get("missing-slug")


def test_register_rejects_a_duplicate_slug() -> None:
    registry = ScenarioRegistry()
    registry.register(_info("same-slug"))

    with pytest.raises(DuplicateScenarioError, match="same-slug"):
        registry.register(_info("same-slug"))
