from collections.abc import Callable, Iterator
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table
from rich.text import Text

from agent_failure_lab import __version__, render, report
from agent_failure_lab.errors import AflabError, LiveNotSupportedError
from agent_failure_lab.live import DEFAULT_MODEL, create_openai_model
from agent_failure_lab.registry import ScenarioRegistry, build_registry
from agent_failure_lab.runner import run_all, run_pair, run_scenario, run_scenario_live
from agent_failure_lab.scaffold import scaffold_failure
from agent_failure_lab.scenario import CATEGORIES, Outcome, Scenario, Variant
from agent_failure_lab.sim import LanguageModel

ModelFactory = Callable[[str], LanguageModel]


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    MD = "md"


class VariantChoice(str, Enum):
    BROKEN = "broken"
    FIXED = "fixed"
    BOTH = "both"


def _variants(choice: VariantChoice | None) -> list[Variant]:
    if choice is VariantChoice.BROKEN:
        return [Variant.BROKEN]
    if choice is VariantChoice.FIXED:
        return [Variant.FIXED]
    return [Variant.BROKEN, Variant.FIXED]


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"aflab {__version__}")
        raise typer.Exit()


@contextmanager
def _reporting_errors() -> Iterator[None]:
    """Turn the library's own errors into a one-line message and exit status 2."""
    try:
        yield
    except AflabError as error:
        render.make_console(stderr=True).print(Text(f"error: {error}", style="red"), soft_wrap=True)
        raise typer.Exit(2) from error


def _check_run_options(
    slug: str | None,
    variant: VariantChoice | None,
    *,
    everything: bool,
    trace: bool,
    fail_on_unfixed: bool,
    live: bool,
) -> None:
    if slug is None and not everything:
        raise typer.BadParameter("give the slug of a failure, or use --all", param_hint="SLUG")
    if slug is not None and everything:
        raise typer.BadParameter("use either a slug or --all, not both", param_hint="--all")
    if everything and variant not in (None, VariantChoice.BOTH):
        raise typer.BadParameter("--all always runs both variants", param_hint="--variant")
    if everything and live:
        raise typer.BadParameter("live mode runs one failure at a time", param_hint="--live")
    if everything and trace:
        raise typer.BadParameter("traces are shown for one failure at a time", param_hint="--trace")
    if fail_on_unfixed and not everything:
        raise typer.BadParameter(
            "this only applies together with --all", param_hint="--fail-on-unfixed"
        )


def _emit_run(
    scenario: Scenario,
    outcomes: list[Outcome],
    output_format: OutputFormat,
    *,
    trace: bool,
    model: str | None,
) -> None:
    if output_format is OutputFormat.JSON:
        data = report.run_data(scenario, outcomes, include_trace=trace, model=model)
        typer.echo(report.to_json(data))
    elif output_format is OutputFormat.MD:
        typer.echo(report.run_markdown(scenario, outcomes, include_trace=trace, model=model))
    else:
        render.show_run(render.make_console(), scenario, outcomes, include_trace=trace, model=model)


def build_app(
    registry: ScenarioRegistry, *, model_factory: ModelFactory = create_openai_model
) -> typer.Typer:
    app = typer.Typer(
        name="aflab",
        help="Catalogue of LLM agent failures with deterministic reproductions and tested guards.",
        no_args_is_help=True,
        add_completion=False,
    )

    @app.callback()
    def root(
        version: Annotated[
            bool,
            typer.Option(
                "--version",
                callback=_print_version,
                is_eager=True,
                help="Show the version and exit.",
            ),
        ] = False,
    ) -> None:
        pass

    @app.command("list", help="List every failure in the catalogue.")
    def list_failures(
        live_only: Annotated[
            bool,
            typer.Option("--live", help="Only list failures that can run against a real model."),
        ] = False,
    ) -> None:
        console = render.make_console()
        scenarios = [s for s in registry.scenarios() if s.supports_live or not live_only]
        if not scenarios:
            console.print("No failures are registered yet.")
            return
        table = Table(show_header=True, header_style="bold")
        table.add_column("Slug", no_wrap=True)
        table.add_column("Category", no_wrap=True)
        table.add_column("Summary")
        for scenario in scenarios:
            table.add_row(Text(scenario.slug), Text(scenario.category), Text(scenario.summary))
        console.print(table)

    @app.command("run", help="Run one failure, or all of them, and show what happens.")
    def run(
        slug: Annotated[
            str | None, typer.Argument(help="The failure to run. See 'aflab list'.")
        ] = None,
        variant: Annotated[
            VariantChoice | None,
            typer.Option(help="Which variant to run. The default is both."),
        ] = None,
        trace: Annotated[
            bool, typer.Option("--trace", help="Show the step by step trace.")
        ] = False,
        output_format: Annotated[
            OutputFormat, typer.Option("--format", help="How to print the result.")
        ] = OutputFormat.TEXT,
        everything: Annotated[bool, typer.Option("--all", help="Run every failure.")] = False,
        fail_on_unfixed: Annotated[
            bool,
            typer.Option(
                "--fail-on-unfixed",
                help="With --all, exit with status 1 if a fixed variant still fails.",
            ),
        ] = False,
        live: Annotated[
            bool,
            typer.Option(
                "--live",
                help="Use a real OpenAI model. Not deterministic, and needs the live extra.",
            ),
        ] = False,
        model_name: Annotated[
            str, typer.Option("--model", help="The OpenAI model to use with --live.")
        ] = DEFAULT_MODEL,
    ) -> None:
        _check_run_options(
            slug,
            variant,
            everything=everything,
            trace=trace,
            fail_on_unfixed=fail_on_unfixed,
            live=live,
        )
        with _reporting_errors():
            if everything:
                pairs = run_all(registry)
                if output_format is OutputFormat.JSON:
                    typer.echo(report.to_json(report.all_data(pairs)))
                elif output_format is OutputFormat.MD:
                    typer.echo(report.all_markdown(pairs))
                else:
                    render.show_all(render.make_console(), pairs)
                if fail_on_unfixed and any(pair.fixed_still_fails for pair in pairs):
                    raise typer.Exit(1)
                return
            scenario = registry.get(str(slug))
            variants = _variants(variant)
            if live:
                if not scenario.supports_live:
                    raise LiveNotSupportedError(scenario.slug)
                chosen = model_factory(model_name)
                outcomes = [run_scenario_live(scenario, v, chosen) for v in variants]
            else:
                outcomes = [run_scenario(scenario, v) for v in variants]
            _emit_run(
                scenario, outcomes, output_format, trace=trace, model=model_name if live else None
            )

    @app.command("compare", help="Show both variants of one failure side by side.")
    def compare(
        slug: Annotated[str, typer.Argument(help="The failure to compare. See 'aflab list'.")],
        output_format: Annotated[
            OutputFormat, typer.Option("--format", help="How to print the result.")
        ] = OutputFormat.TEXT,
    ) -> None:
        with _reporting_errors():
            pair = run_pair(registry.get(slug))
            if output_format is OutputFormat.JSON:
                typer.echo(report.to_json(report.pair_data(pair, include_trace=True)))
            elif output_format is OutputFormat.MD:
                outcomes = [pair.broken, pair.fixed]
                typer.echo(report.run_markdown(pair.scenario, outcomes, include_trace=True))
            else:
                render.show_compare(render.make_console(), pair)

    @app.command("new", help="Create the files for a new failure and register it.")
    def new(
        slug: Annotated[str, typer.Argument(help="Lowercase words joined by hyphens.")],
        category: Annotated[
            str, typer.Option(help=f"One of: {', '.join(CATEGORIES)}.")
        ] = "tool-use",
        root_dir: Annotated[
            Path,
            typer.Option("--root", help="The repository root.", file_okay=False),
        ] = Path("."),
    ) -> None:
        console = render.make_console()
        with _reporting_errors():
            result = scaffold_failure(root_dir, slug, category=category)
        console.print(Text(f"Created {slug}:", style="bold"))
        for path in result.created:
            console.print(Text(f"  {path}"), soft_wrap=True)
        if not result.registered:
            console.print(
                Text(
                    "Could not register it automatically. Add it to builtin_scenarios() in "
                    "src/agent_failure_lab/failures/__init__.py.",
                    style="yellow",
                ),
                soft_wrap=True,
            )
        console.print(
            "Next: edit world.py, broken.py, fixed.py and the README, then run "
            "'python scripts/generate_catalog.py' and the tests.",
            soft_wrap=True,
        )

    @app.command("report", help="Run every failure and write a results report.")
    def results(
        output_format: Annotated[
            OutputFormat,
            typer.Option("--format", help="Markdown or JSON."),
        ] = OutputFormat.MD,
        output: Annotated[
            Path | None, typer.Option("--output", help="Write to this file instead of printing.")
        ] = None,
    ) -> None:
        if output_format is OutputFormat.TEXT:
            raise typer.BadParameter("choose md or json", param_hint="--format")
        with _reporting_errors():
            pairs = run_all(registry)
            if output_format is OutputFormat.JSON:
                document = report.to_json(report.all_data(pairs))
            else:
                document = report.report_markdown(pairs)
            if output is None:
                typer.echo(document)
            else:
                output.write_text(document + "\n", encoding="utf-8", newline="\n")
                typer.echo(f"Wrote {output}")

    return app


def main() -> None:
    build_app(build_registry())()
