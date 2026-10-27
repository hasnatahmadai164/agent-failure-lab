from pathlib import Path

import pytest

from agent_failure_lab.catalog import END_MARKER, START_MARKER
from loader import load_module

SCRIPT = load_module("scripts/generate_catalog.py", "generate_catalog_script")
INTRO = "# Title\n\nSome words before the table.\n"
OUTRO = "\n## After\n\nSome words after the table.\n"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "README.md").write_text(
        f"{INTRO}\n{START_MARKER}\nold table\n{END_MARKER}\n{OUTRO}", encoding="utf-8", newline="\n"
    )
    return tmp_path


def test_check_reports_every_file_that_is_out_of_date(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = SCRIPT.main(["--check"], root=repo)

    output = capsys.readouterr().out
    assert status == 1
    assert "out of date: README.md" in output
    assert "out of date: docs" in output
    assert "python scripts/generate_catalog.py" in output
    assert "old table" in (repo / "README.md").read_text(encoding="utf-8")


def test_running_it_writes_the_page_and_the_table_and_leaves_the_rest_alone(repo: Path) -> None:
    assert SCRIPT.main([], root=repo) == 0

    readme = (repo / "README.md").read_text(encoding="utf-8")
    assert readme.startswith(INTRO)
    assert readme.endswith(OUTRO)
    assert "old table" not in readme
    assert "duplicate-side-effect" in readme
    assert (repo / "docs" / "catalog.md").read_text(encoding="utf-8").startswith("# Catalog")


def test_after_a_run_the_check_passes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    SCRIPT.main([], root=repo)
    capsys.readouterr()

    assert SCRIPT.main(["--check"], root=repo) == 0
    assert capsys.readouterr().out == ""


def test_running_it_twice_changes_nothing(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    SCRIPT.main([], root=repo)
    capsys.readouterr()

    assert SCRIPT.main([], root=repo) == 0
    assert "already up to date" in capsys.readouterr().out


def test_the_readme_links_work_on_pypi_where_relative_links_do_not(repo: Path) -> None:
    SCRIPT.main([], root=repo)

    readme = (repo / "README.md").read_text(encoding="utf-8")
    assert "](https://github.com/hasnatahmadai164/agent-failure-lab/blob/main/src/" in readme
    assert "](src/" not in readme
    assert b"\r\n" not in (repo / "README.md").read_bytes()
