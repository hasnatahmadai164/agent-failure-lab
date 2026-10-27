import json
from collections.abc import Callable

import pytest
from typer.testing import CliRunner

from agent_failure_lab.cli import build_app
from agent_failure_lab.errors import LiveModeUnavailableError
from agent_failure_lab.registry import ScenarioRegistry, build_registry
from agent_failure_lab.scenario import ScenarioDefinition
from agent_failure_lab.sim import LanguageModel, Reply, ScriptedLLM

runner = CliRunner()
MakeScenario = Callable[..., ScenarioDefinition]


def _real(*args: str) -> tuple[int, str]:
    result = runner.invoke(build_app(build_registry()), list(args))
    return result.exit_code, result.stdout


def test_running_one_failure_shows_both_variants_and_the_verdict() -> None:
    code, output = _real("run", "duplicate-side-effect")

    assert code == 0
    assert "Broken variant: FAILURE OBSERVED" in output
    assert "Fixed variant: no failure" in output
    assert "charges" in output
    assert "The broken variant fails and the fixed variant does not." in output
    assert "Scripted model, no network" in output


def test_one_variant_can_be_chosen_and_then_no_verdict_is_given() -> None:
    code, output = _real("run", "duplicate-side-effect", "--variant", "fixed")

    assert code == 0
    assert "Fixed variant" in output
    assert "Broken variant" not in output
    assert "The broken variant fails" not in output


def test_the_trace_is_only_shown_when_asked_for() -> None:
    _, plain = _real("run", "duplicate-side-effect")
    _, traced = _real("run", "duplicate-side-effect", "--trace")

    assert "tool_result" not in plain
    assert "tool_result" in traced
    assert "IdempotencyKeys: attached key" in traced


def test_text_in_square_brackets_is_printed_as_it_is() -> None:
    _, output = _real("run", "tool-output-injection", "--variant", "fixed", "--trace")

    assert "[untrusted content returned by fetch_page" in output


def test_json_output_is_a_single_valid_document() -> None:
    code, output = _real("run", "duplicate-side-effect", "--format", "json")

    data = json.loads(output)
    assert code == 0
    assert data["scenario"]["slug"] == "duplicate-side-effect"
    assert data["contract_holds"] is True
    broken, fixed = data["outcomes"]
    assert broken["metrics"]["charges"] == 2
    assert fixed["metrics"]["charges"] == 1
    assert "trace" not in broken


def test_json_output_includes_the_trace_when_asked() -> None:
    _, output = _real("run", "duplicate-side-effect", "--format", "json", "--trace")

    assert json.loads(output)["outcomes"][0]["trace"][0]["kind"] == "model"


def test_markdown_output_has_a_heading_and_a_metrics_table() -> None:
    _, output = _real("run", "duplicate-side-effect", "--format", "md")

    assert output.startswith("## duplicate-side-effect")
    assert "| charges | 2 |" in output


def test_running_everything_lists_every_failure_and_succeeds() -> None:
    code, output = _real("run", "--all")

    assert code == 0
    assert "memory-poisoning" in output
    assert "All 12 fixed variants avoid the failure." in output


def test_all_in_json_names_any_fix_that_did_not_work(make_scenario: MakeScenario) -> None:
    registry = ScenarioRegistry()
    registry.register(make_scenario("good-one"))
    registry.register(make_scenario("bad-one", fixed_fails=True))

    result = runner.invoke(build_app(registry), ["run", "--all", "--format", "json"])

    assert json.loads(result.stdout)["fixed_still_failing"] == ["bad-one"]


def test_fail_on_unfixed_exits_with_status_one_when_a_fix_does_not_work(
    make_scenario: MakeScenario,
) -> None:
    registry = ScenarioRegistry()
    registry.register(make_scenario("bad-one", fixed_fails=True))

    result = runner.invoke(build_app(registry), ["run", "--all", "--fail-on-unfixed"])

    assert result.exit_code == 1
    assert "Fixed variant still fails: bad-one" in result.output


def test_fail_on_unfixed_is_quiet_when_every_fix_works(make_scenario: MakeScenario) -> None:
    registry = ScenarioRegistry()
    registry.register(make_scenario("good-one"))

    assert runner.invoke(build_app(registry), ["run", "--all", "--fail-on-unfixed"]).exit_code == 0


def test_without_the_flag_a_failing_fix_does_not_change_the_exit_status(
    make_scenario: MakeScenario,
) -> None:
    registry = ScenarioRegistry()
    registry.register(make_scenario("bad-one", fixed_fails=True))

    assert runner.invoke(build_app(registry), ["run", "--all"]).exit_code == 0


@pytest.mark.parametrize(
    "arguments",
    [
        ["run"],
        ["run", "duplicate-side-effect", "--all"],
        ["run", "--all", "--variant", "broken"],
        ["run", "--all", "--live"],
        ["run", "--all", "--trace"],
        ["run", "duplicate-side-effect", "--fail-on-unfixed"],
    ],
)
def test_options_that_do_not_make_sense_together_are_refused(arguments: list[str]) -> None:
    code, _ = _real(*arguments)

    assert code == 2


def test_an_unknown_slug_gets_a_one_line_message_and_status_two() -> None:
    result = runner.invoke(build_app(build_registry()), ["run", "no-such-failure"])

    assert result.exit_code == 2
    assert "No failure is registered under the slug 'no-such-failure'" in result.output
    assert "Traceback" not in result.output


def _live_registry(make_scenario: MakeScenario) -> ScenarioRegistry:
    registry = ScenarioRegistry()
    registry.register(make_scenario("live-one", live=True))
    registry.register(make_scenario("scripted-only"))
    return registry


def test_a_live_run_is_labelled_and_makes_no_claim_about_the_result(
    make_scenario: MakeScenario,
) -> None:
    asked: list[str] = []

    def factory(name: str) -> LanguageModel:
        asked.append(name)
        return ScriptedLLM([Reply("unused")])

    app = build_app(_live_registry(make_scenario), model_factory=factory)
    result = runner.invoke(app, ["run", "live-one", "--live", "--model", "gpt-test"])

    assert result.exit_code == 0
    assert asked == ["gpt-test"]
    assert "Live run against a real model" in result.output
    assert "gpt-test" in result.output
    assert "not deterministic" in result.output
    assert "The broken variant fails" not in result.output


def test_live_json_output_says_it_was_live_and_names_the_model(
    make_scenario: MakeScenario,
) -> None:
    app = build_app(_live_registry(make_scenario), model_factory=lambda name: ScriptedLLM([]))

    result = runner.invoke(
        app, ["run", "live-one", "--live", "--model", "gpt-test", "--format", "json"]
    )

    data = json.loads(result.stdout)
    assert (data["mode"], data["model"], data["contract_holds"]) == ("live", "gpt-test", None)


def test_a_failure_with_no_live_variant_is_refused_before_a_model_is_created(
    make_scenario: MakeScenario,
) -> None:
    def factory(name: str) -> LanguageModel:
        raise AssertionError("no model should be created")

    app = build_app(_live_registry(make_scenario), model_factory=factory)
    result = runner.invoke(app, ["run", "scripted-only", "--live"])

    assert result.exit_code == 2
    assert "has no live variant" in result.output


def test_a_missing_package_or_key_is_explained_and_not_a_traceback(
    make_scenario: MakeScenario,
) -> None:
    def factory(name: str) -> LanguageModel:
        raise LiveModeUnavailableError("OPENAI_API_KEY is not set. Set it in your environment.")

    app = build_app(_live_registry(make_scenario), model_factory=factory)
    result = runner.invoke(app, ["run", "live-one", "--live"])

    assert result.exit_code == 2
    assert "OPENAI_API_KEY is not set" in result.output
    assert "Traceback" not in result.output
