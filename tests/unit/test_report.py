import json
from collections.abc import Callable

import pytest

from agent_failure_lab.report import (
    LIVE_NOTICE,
    all_data,
    all_markdown,
    contract_holds,
    format_value,
    outcome_data,
    outcome_markdown,
    pair_data,
    report_markdown,
    run_data,
    run_markdown,
    to_json,
)
from agent_failure_lab.runner import run_pair
from agent_failure_lab.scenario import Outcome, ScenarioDefinition, Variant
from agent_failure_lab.sim import EventKind, ManualClock, Trace

MakeScenario = Callable[..., ScenarioDefinition]


def _outcome(
    variant: Variant, *, failed: bool, metrics: dict[str, object] | None = None
) -> Outcome:
    trace = Trace(ManualClock())
    trace.record(1, EventKind.MODEL, "says hello")
    return Outcome(variant, failed, trace, metrics or {"charges": 2}, ("a finding",))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "text"),
    [(True, "yes"), (False, "no"), (3600.0, "3600"), (0.4396, "0.4396"), (7, "7"), ("x", "x")],
)
def test_values_are_formatted_for_people(value: object, text: str) -> None:
    assert format_value(value) == text  # type: ignore[arg-type]


def test_the_contract_needs_both_variants_to_say_anything() -> None:
    assert contract_holds([_outcome(Variant.BROKEN, failed=True)]) is None


@pytest.mark.parametrize(
    ("broken_fails", "fixed_fails", "expected"),
    [(True, False, True), (True, True, False), (False, False, False)],
)
def test_the_contract_holds_only_when_just_the_broken_variant_fails(
    broken_fails: bool, fixed_fails: bool, expected: bool
) -> None:
    outcomes = [
        _outcome(Variant.BROKEN, failed=broken_fails),
        _outcome(Variant.FIXED, failed=fixed_fails),
    ]

    assert contract_holds(outcomes) is expected


def test_outcome_data_includes_the_trace_only_when_asked() -> None:
    outcome = _outcome(Variant.BROKEN, failed=True)

    assert "trace" not in outcome_data(outcome, include_trace=False)
    assert outcome_data(outcome, include_trace=True)["trace"][0]["summary"] == "says hello"


def test_run_data_for_a_simulated_run_carries_the_contract(make_scenario: MakeScenario) -> None:
    outcomes = [_outcome(Variant.BROKEN, failed=True), _outcome(Variant.FIXED, failed=False)]

    data = run_data(make_scenario(), outcomes, include_trace=False)

    assert data["mode"] == "simulated"
    assert data["model"] is None
    assert data["contract_holds"] is True
    assert data["scenario"]["slug"] == "example-failure"


def test_run_data_for_a_live_run_names_the_model_and_makes_no_claim(
    make_scenario: MakeScenario,
) -> None:
    outcomes = [_outcome(Variant.BROKEN, failed=False), _outcome(Variant.FIXED, failed=False)]

    data = run_data(make_scenario(), outcomes, include_trace=False, model="gpt-test")

    assert data["mode"] == "live"
    assert data["model"] == "gpt-test"
    assert data["contract_holds"] is None


def test_all_data_lists_the_failures_whose_fix_did_not_work(make_scenario: MakeScenario) -> None:
    good = run_pair(make_scenario("good-one"))
    bad = run_pair(make_scenario("bad-one", fixed_fails=True))

    data = all_data([good, bad])

    assert data["fixed_still_failing"] == ["bad-one"]
    assert [r["slug"] for r in data["results"]] == ["good-one", "bad-one"]


def test_pair_data_is_plain_json(make_scenario: MakeScenario) -> None:
    data = pair_data(run_pair(make_scenario()), include_trace=True)

    assert json.loads(to_json(data))["contract_holds"] is True


def test_outcome_markdown_has_a_metrics_table_findings_and_an_optional_trace() -> None:
    outcome = _outcome(Variant.BROKEN, failed=True)

    plain = outcome_markdown(outcome, include_trace=False)
    traced = outcome_markdown(outcome, include_trace=True)

    assert "### Broken variant: failure observed" in plain
    assert "| charges | 2 |" in plain
    assert "- a finding" in plain
    assert "```text" not in plain
    assert "```text" in traced
    assert "says hello" in traced


def test_a_pipe_in_a_metric_does_not_break_the_table() -> None:
    outcome = _outcome(Variant.BROKEN, failed=True, metrics={"note": "a|b"})

    assert "a\\|b" in outcome_markdown(outcome, include_trace=False)


def test_run_markdown_states_whether_the_run_was_scripted_or_live(
    make_scenario: MakeScenario,
) -> None:
    outcomes = [_outcome(Variant.BROKEN, failed=True), _outcome(Variant.FIXED, failed=False)]

    simulated = run_markdown(make_scenario(), outcomes, include_trace=False)
    live = run_markdown(make_scenario(), outcomes, include_trace=False, model="gpt-test")

    assert "Scripted model" in simulated
    assert "The broken variant fails and the fixed variant does not." in simulated
    assert LIVE_NOTICE in live
    assert "gpt-test" in live
    assert "The broken variant fails" not in live


def test_all_markdown_has_one_row_per_failure(make_scenario: MakeScenario) -> None:
    pairs = [
        run_pair(make_scenario("good-one")),
        run_pair(make_scenario("bad-one", fixed_fails=True)),
    ]

    lines = all_markdown(pairs).splitlines()

    assert lines[2] == "| `good-one` | side-effects | reproduced | clean | ok |"
    assert lines[3] == "| `bad-one` | side-effects | reproduced | fails | check |"


def test_the_full_report_covers_every_failure(make_scenario: MakeScenario) -> None:
    pairs = [run_pair(make_scenario("good-one")), run_pair(make_scenario("other-one"))]

    document = report_markdown(pairs)

    assert document.startswith("# Results")
    assert "## good-one" in document
    assert "## other-one" in document
