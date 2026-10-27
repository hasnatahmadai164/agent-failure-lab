from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_failure_lab.cli import build_app
from agent_failure_lab.registry import ScenarioRegistry

runner = CliRunner()
APP = build_app(ScenarioRegistry())

INIT = """\
from agent_failure_lab.failures import (
    alpha_thing,
)
from agent_failure_lab.scenario import Scenario


def builtin_scenarios() -> tuple[Scenario, ...]:
    return (
        alpha_thing.SCENARIO,
    )
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    failures = tmp_path / "src" / "agent_failure_lab" / "failures"
    failures.mkdir(parents=True)
    (failures / "__init__.py").write_text(INIT, encoding="utf-8")
    return tmp_path


def test_new_creates_the_files_and_registers_the_failure(repo: Path) -> None:
    result = runner.invoke(APP, ["new", "brand-new-failure", "--root", str(repo)])

    assert result.exit_code == 0
    assert "Created brand-new-failure" in result.output
    assert (repo / "tests" / "failures" / "test_brand_new_failure.py").exists()
    init = (repo / "src" / "agent_failure_lab" / "failures" / "__init__.py").read_text("utf-8")
    assert "brand_new_failure.SCENARIO" in init
    assert "Could not register" not in result.output


def test_new_takes_a_category(repo: Path) -> None:
    runner.invoke(APP, ["new", "brand-new-failure", "--category", "security", "--root", str(repo)])

    package = repo / "src" / "agent_failure_lab" / "failures" / "brand_new_failure"
    assert 'category="security"' in (package / "__init__.py").read_text("utf-8")


def test_new_says_what_to_do_by_hand_when_it_cannot_register_the_failure(repo: Path) -> None:
    init = repo / "src" / "agent_failure_lab" / "failures" / "__init__.py"
    init.write_text("SCENARIOS = []\n", encoding="utf-8")

    result = runner.invoke(APP, ["new", "brand-new-failure", "--root", str(repo)])

    assert result.exit_code == 0
    assert "Could not register it automatically" in result.output


def test_new_points_to_the_next_steps(repo: Path) -> None:
    result = runner.invoke(APP, ["new", "brand-new-failure", "--root", str(repo)])

    assert "generate_catalog.py" in result.output


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["new", "Not_Valid"], "not a valid slug"),
        (["new", "fine-slug", "--category", "nonsense"], "Unknown category"),
    ],
)
def test_new_explains_bad_input_and_exits_with_status_two(
    repo: Path, arguments: list[str], message: str
) -> None:
    result = runner.invoke(APP, [*arguments, "--root", str(repo)])

    assert result.exit_code == 2
    assert message in result.output


def test_new_will_not_overwrite_a_failure_that_exists(repo: Path) -> None:
    runner.invoke(APP, ["new", "brand-new-failure", "--root", str(repo)])

    result = runner.invoke(APP, ["new", "brand-new-failure", "--root", str(repo)])

    assert result.exit_code == 2
    assert "already exists" in result.output


def test_new_outside_a_repository_says_where_to_run_it(tmp_path: Path) -> None:
    result = runner.invoke(APP, ["new", "brand-new-failure", "--root", str(tmp_path)])

    assert result.exit_code == 2
    assert "repository root" in result.output
