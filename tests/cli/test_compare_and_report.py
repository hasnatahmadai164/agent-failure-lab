import json
from pathlib import Path

from typer.testing import CliRunner

from agent_failure_lab.cli import build_app
from agent_failure_lab.registry import build_registry

runner = CliRunner()
APP = build_app(build_registry())


def test_compare_puts_the_two_variants_side_by_side_in_a_metrics_table() -> None:
    result = runner.invoke(APP, ["compare", "duplicate-side-effect"])

    assert result.exit_code == 0
    header = next(line for line in result.output.splitlines() if "Metric" in line)
    assert "Broken" in header
    assert "Fixed" in header
    charges = next(
        line for line in result.output.splitlines() if line.lstrip("│ ").startswith("charges")
    )
    assert "2" in charges
    assert "1" in charges
    assert "failure observed" in result.output


def test_compare_shows_each_trace_one_after_the_other_on_a_narrow_terminal() -> None:
    result = runner.invoke(APP, ["compare", "duplicate-side-effect"], env={"COLUMNS": "80"})

    assert "Broken trace" in result.output
    assert "Fixed trace" in result.output
    assert "IdempotencyKeys: attached key" in result.output


def test_compare_puts_the_traces_next_to_each_other_on_a_wide_terminal() -> None:
    result = runner.invoke(APP, ["compare", "duplicate-side-effect"], env={"COLUMNS": "220"})

    header = next(line for line in result.output.splitlines() if "Broken trace" in line)
    assert "Fixed trace" in header


def test_compare_in_json_includes_both_traces() -> None:
    result = runner.invoke(APP, ["compare", "duplicate-side-effect", "--format", "json"])

    data = json.loads(result.stdout)
    assert data["broken"]["trace"]
    assert data["fixed"]["trace"]
    assert data["contract_holds"] is True


def test_compare_in_markdown_includes_the_traces() -> None:
    result = runner.invoke(APP, ["compare", "duplicate-side-effect", "--format", "md"])

    assert "```text" in result.output
    assert "### Fixed variant: no failure" in result.output


def test_compare_with_an_unknown_slug_is_a_clear_error() -> None:
    result = runner.invoke(APP, ["compare", "no-such-failure"])

    assert result.exit_code == 2
    assert "No failure is registered" in result.output


def test_report_prints_a_markdown_document_covering_every_failure() -> None:
    result = runner.invoke(APP, ["report"])

    assert result.exit_code == 0
    assert result.stdout.startswith("# Results")
    for scenario in build_registry().scenarios():
        assert f"## {scenario.slug}" in result.stdout


def test_report_can_be_written_as_json() -> None:
    result = runner.invoke(APP, ["report", "--format", "json"])

    data = json.loads(result.stdout)
    assert len(data["results"]) == 12
    assert data["fixed_still_failing"] == []


def test_report_can_be_written_to_a_file(tmp_path: Path) -> None:
    target = tmp_path / "results.md"

    result = runner.invoke(APP, ["report", "--output", str(target)])

    assert result.exit_code == 0
    assert f"Wrote {target}" in result.stdout
    assert target.read_text(encoding="utf-8").startswith("# Results")
    assert b"\r\n" not in target.read_bytes()


def test_report_has_no_plain_text_format() -> None:
    assert runner.invoke(APP, ["report", "--format", "text"]).exit_code == 2
