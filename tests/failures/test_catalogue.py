from importlib.resources import files

import pytest

from agent_failure_lab.registry import build_registry
from agent_failure_lab.runner import run_pair
from agent_failure_lab.scenario import Scenario

SCENARIOS = build_registry().scenarios()
CATEGORIES = {"side-effects", "control-flow", "security", "tool-use", "context-and-cost"}
README_SECTIONS = [
    "What happens",
    "Why it happens",
    "Impact",
    "How to detect it in your own system",
    "The fix",
    "Trade-offs",
    "Related guards",
]


def _readme(scenario: Scenario) -> str:
    package = f"agent_failure_lab.failures.{scenario.slug.replace('-', '_')}"
    return files(package).joinpath("README.md").read_text(encoding="utf-8")


def test_the_catalogue_lists_the_failures_in_the_order_of_the_brief() -> None:
    assert [scenario.slug for scenario in SCENARIOS] == [
        "duplicate-side-effect",
        "infinite-tool-loop",
        "tool-output-injection",
        "hallucinated-tool-arguments",
        "silent-context-truncation",
        "runaway-cost",
        "resume-replays-completed-steps",
        "tool-timeout-hang",
        "parallel-tool-race",
        "ambiguous-tool-selection",
        "false-success-claim",
        "memory-poisoning",
    ]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.slug)
def test_the_broken_variant_shows_the_failure_and_the_fixed_variant_does_not(
    scenario: Scenario,
) -> None:
    result = run_pair(scenario)

    assert result.broken_reproduced
    assert not result.fixed_still_fails


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.slug)
def test_two_runs_produce_the_same_metrics_and_the_same_trace(scenario: Scenario) -> None:
    first = run_pair(scenario)
    second = run_pair(scenario)

    assert dict(first.broken.metrics) == dict(second.broken.metrics)
    assert dict(first.fixed.metrics) == dict(second.fixed.metrics)
    assert first.broken.trace.to_json() == second.broken.trace.to_json()
    assert first.fixed.trace.to_json() == second.fixed.trace.to_json()


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.slug)
def test_the_metadata_is_filled_in_and_the_category_is_a_known_one(scenario: Scenario) -> None:
    assert scenario.title
    assert scenario.summary
    assert not scenario.summary.endswith(".")
    assert scenario.category in CATEGORIES


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.slug)
def test_the_readme_has_every_required_section_and_names_the_failure(
    scenario: Scenario,
) -> None:
    text = _readme(scenario)

    assert text.startswith(f"# {scenario.slug}\n")
    for section in README_SECTIONS:
        assert f"\n## {section}\n" in text


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.slug)
def test_the_readme_uses_no_dashes_as_punctuation(scenario: Scenario) -> None:
    text = _readme(scenario)

    assert chr(0x2014) not in text
    assert chr(0x2013) not in text
