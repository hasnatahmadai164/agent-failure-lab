import importlib
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

import agent_failure_lab.failures as failures_package
from agent_failure_lab.errors import InvalidSlugError, ScaffoldError
from agent_failure_lab.runner import run_pair
from agent_failure_lab.scaffold import register_in_catalogue, scaffold_failure

INIT = """\
from agent_failure_lab.failures import (
    alpha_thing,
    zulu_thing,
)
from agent_failure_lab.scenario import Scenario


def builtin_scenarios() -> tuple[Scenario, ...]:
    return (
        alpha_thing.SCENARIO,
        zulu_thing.SCENARIO,
    )
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    failures = tmp_path / "src" / "agent_failure_lab" / "failures"
    failures.mkdir(parents=True)
    (failures / "__init__.py").write_text(INIT, encoding="utf-8")
    return tmp_path


@pytest.fixture
def importable_failures(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Let the scaffolded package be imported from the temporary repository."""
    where = str(repo / "src" / "agent_failure_lab" / "failures")
    monkeypatch.setattr(failures_package, "__path__", [*failures_package.__path__, where])
    importlib.invalidate_caches()
    yield
    for name in [n for n in sys.modules if n.startswith("agent_failure_lab.failures.fresh_")]:
        del sys.modules[name]


def test_every_file_a_contributor_needs_is_created(repo: Path) -> None:
    result = scaffold_failure(repo, "brand-new-failure", category="tool-use")

    names = sorted(path.name for path in result.created)
    assert names == [
        "README.md",
        "__init__.py",
        "broken.py",
        "fixed.py",
        "test_brand_new_failure.py",
        "world.py",
    ]
    assert all(path.exists() for path in result.created)


def test_the_package_name_uses_underscores_where_the_slug_has_hyphens(repo: Path) -> None:
    scaffold_failure(repo, "brand-new-failure", category="tool-use")

    package = repo / "src" / "agent_failure_lab" / "failures" / "brand_new_failure"
    assert (package / "__init__.py").exists()
    assert 'slug="brand-new-failure"' in (package / "__init__.py").read_text(encoding="utf-8")


def test_files_are_written_with_unix_line_endings_and_no_byte_order_mark(repo: Path) -> None:
    result = scaffold_failure(repo, "brand-new-failure", category="tool-use")

    for path in result.created:
        raw = path.read_bytes()
        assert b"\r\n" not in raw
        assert not raw.startswith(b"\xef\xbb\xbf")


def test_the_new_package_is_added_to_the_catalogue_in_sorted_import_order(repo: Path) -> None:
    result = scaffold_failure(repo, "middle-thing", category="security")

    text = (repo / "src" / "agent_failure_lab" / "failures" / "__init__.py").read_text("utf-8")
    assert result.registered
    assert (
        text.index("    alpha_thing,")
        < text.index("    middle_thing,")
        < text.index("    zulu_thing,")
    )
    assert text.rstrip().endswith("        middle_thing.SCENARIO,\n    )")


def test_registering_twice_does_not_add_a_second_entry(repo: Path) -> None:
    init = repo / "src" / "agent_failure_lab" / "failures" / "__init__.py"

    assert register_in_catalogue(init, "middle_thing")
    once = init.read_text(encoding="utf-8")

    assert register_in_catalogue(init, "middle_thing")
    assert init.read_text(encoding="utf-8") == once


def test_a_catalogue_file_of_an_unexpected_shape_is_left_alone(repo: Path) -> None:
    init = repo / "src" / "agent_failure_lab" / "failures" / "__init__.py"
    init.write_text("SCENARIOS = []\n", encoding="utf-8")

    assert not register_in_catalogue(init, "middle_thing")
    assert init.read_text(encoding="utf-8") == "SCENARIOS = []\n"


def test_a_malformed_slug_is_refused(repo: Path) -> None:
    with pytest.raises(InvalidSlugError):
        scaffold_failure(repo, "Not_Valid", category="tool-use")


def test_an_unknown_category_is_refused_with_the_list_of_choices(repo: Path) -> None:
    with pytest.raises(ScaffoldError, match="side-effects"):
        scaffold_failure(repo, "brand-new-failure", category="made-up")


def test_an_existing_failure_is_never_overwritten(repo: Path) -> None:
    scaffold_failure(repo, "brand-new-failure", category="tool-use")

    with pytest.raises(ScaffoldError, match="already exists"):
        scaffold_failure(repo, "brand-new-failure", category="tool-use")


def test_running_outside_the_repository_gives_a_helpful_error(tmp_path: Path) -> None:
    with pytest.raises(ScaffoldError, match="repository root"):
        scaffold_failure(tmp_path, "brand-new-failure", category="tool-use")


def test_everything_that_is_generated_is_valid_python(repo: Path) -> None:
    result = scaffold_failure(repo, "brand-new-failure", category="tool-use")

    for path in result.created:
        if path.suffix == ".py":
            compile(path.read_text(encoding="utf-8"), str(path), "exec")


@pytest.mark.usefixtures("importable_failures")
def test_the_generated_failure_runs_and_holds_the_contract(repo: Path) -> None:
    scaffold_failure(repo, "fresh-failure", category="control-flow")

    module = importlib.import_module("agent_failure_lab.failures.fresh_failure")
    result = run_pair(module.SCENARIO)

    assert result.contract_holds
    assert result.broken.metrics["jobs_run"] == 4
    assert result.fixed.metrics["jobs_run"] == 1
