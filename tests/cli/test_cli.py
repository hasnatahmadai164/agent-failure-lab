from collections.abc import Callable

from typer.testing import CliRunner

from agent_failure_lab import __version__
from agent_failure_lab.cli import build_app
from agent_failure_lab.registry import ScenarioRegistry
from agent_failure_lab.scenario import ScenarioDefinition

runner = CliRunner()


def test_version_flag_prints_package_version() -> None:
    result = runner.invoke(build_app(ScenarioRegistry()), ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"aflab {__version__}"


def test_help_mentions_the_list_command() -> None:
    result = runner.invoke(build_app(ScenarioRegistry()), ["--help"])

    assert result.exit_code == 0
    assert "list" in result.output


def test_list_reports_an_empty_catalogue() -> None:
    result = runner.invoke(build_app(ScenarioRegistry()), ["list"])

    assert result.exit_code == 0
    assert "No failures are registered yet." in result.output


def test_list_shows_slug_category_and_summary(
    make_scenario: Callable[..., ScenarioDefinition],
) -> None:
    registry = ScenarioRegistry()
    registry.register(make_scenario("duplicate-side-effect"))

    result = runner.invoke(build_app(registry), ["list"])

    assert result.exit_code == 0
    assert "duplicate-side-effect" in result.output
    assert "side-effects" in result.output
    assert "Retry charges twice" in result.output
