from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from agent_failure_lab import __version__
from agent_failure_lab.registry import ScenarioRegistry, build_registry


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"aflab {__version__}")
        raise typer.Exit()


def build_app(registry: ScenarioRegistry) -> typer.Typer:
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
    def list_failures() -> None:
        console = Console()
        scenarios = registry.scenarios()
        if not scenarios:
            console.print("No failures are registered yet.")
            return
        table = Table(show_header=True, header_style="bold")
        table.add_column("Slug", no_wrap=True)
        table.add_column("Category", no_wrap=True)
        table.add_column("Summary")
        for info in scenarios:
            table.add_row(info.slug, info.category, info.summary)
        console.print(table)

    return app


def main() -> None:
    build_app(build_registry())()
