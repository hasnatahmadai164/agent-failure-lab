from collections.abc import Sequence

from rich.console import Console
from rich.table import Table
from rich.text import Text

from agent_failure_lab.report import (
    LIVE_NOTICE,
    SIMULATED_NOTICE,
    contract_holds,
    format_value,
    status_label,
    verdict_sentence,
)
from agent_failure_lab.runner import PairResult
from agent_failure_lab.scenario import Outcome, Scenario

WIDE_TERMINAL = 120


def make_console(*, stderr: bool = False) -> Console:
    """A console that prints text as given: brackets in a trace must not be read as styling."""
    return Console(markup=False, highlight=False, stderr=stderr)


def _status(outcome: Outcome) -> Text:
    style = "bold red" if outcome.failure_observed else "bold green"
    label = status_label(outcome).upper() if outcome.failure_observed else status_label(outcome)
    return Text(f"{outcome.variant.value.capitalize()} variant: {label}", style=style)


def show_header(console: Console, scenario: Scenario, *, model: str | None) -> None:
    console.print(Text(f"{scenario.slug}  ({scenario.category})", style="bold"))
    console.print(scenario.summary)
    if model:
        console.print(Text(f"{LIVE_NOTICE} Model: {model}.", style="bold yellow"), soft_wrap=True)
    else:
        console.print(Text(SIMULATED_NOTICE, style="dim"), soft_wrap=True)
    console.print()


def show_outcome(console: Console, outcome: Outcome, *, include_trace: bool) -> None:
    console.print(_status(outcome))
    if outcome.metrics:
        grid = Table.grid(padding=(0, 2))
        for key, value in outcome.metrics.items():
            grid.add_row(Text(f"  {key}", style="dim"), Text(format_value(value)))
        console.print(grid)
    for finding in outcome.findings:
        console.print(Text(f"  {finding}"), soft_wrap=True)
    if include_trace:
        console.print(Text("  Trace:", style="dim"))
        for line in outcome.trace.render().splitlines():
            console.print(Text(f"    {line}"), soft_wrap=True)
    console.print()


def show_verdict(console: Console, outcomes: Sequence[Outcome]) -> None:
    holds = contract_holds(outcomes)
    if holds is None:
        return
    style = "green" if holds else "yellow"
    console.print(Text(verdict_sentence(holds), style=style), soft_wrap=True)


def show_run(
    console: Console,
    scenario: Scenario,
    outcomes: Sequence[Outcome],
    *,
    include_trace: bool,
    model: str | None = None,
) -> None:
    show_header(console, scenario, model=model)
    for outcome in outcomes:
        show_outcome(console, outcome, include_trace=include_trace)
    if model is None:
        show_verdict(console, outcomes)


def show_all(console: Console, pairs: Sequence[PairResult]) -> None:
    table = Table(show_header=True, header_style="bold")
    table.add_column("Failure", no_wrap=True)
    table.add_column("Broken", no_wrap=True)
    table.add_column("Fixed", no_wrap=True)
    table.add_column("Result", no_wrap=True)
    for pair in pairs:
        holds = pair.contract_holds
        table.add_row(
            Text(pair.scenario.slug),
            Text("reproduced" if pair.broken_reproduced else "not seen"),
            Text("fails" if pair.fixed_still_fails else "clean"),
            Text("ok" if holds else "check", style="green" if holds else "red"),
        )
    console.print(table)
    unfixed = [p.scenario.slug for p in pairs if p.fixed_still_fails]
    if unfixed:
        console.print(Text(f"Fixed variant still fails: {', '.join(unfixed)}", style="bold red"))
    else:
        console.print(Text(f"All {len(pairs)} fixed variants avoid the failure.", style="green"))


def show_compare(console: Console, pair: PairResult) -> None:
    show_header(console, pair.scenario, model=None)
    keys = list(dict.fromkeys([*pair.broken.metrics, *pair.fixed.metrics]))
    table = Table(show_header=True, header_style="bold")
    table.add_column("Metric")
    table.add_column("Broken")
    table.add_column("Fixed")
    for key in keys:
        table.add_row(
            Text(key),
            Text(format_value(pair.broken.metrics[key]) if key in pair.broken.metrics else "-"),
            Text(format_value(pair.fixed.metrics[key]) if key in pair.fixed.metrics else "-"),
        )
    table.add_row(
        Text("failure observed", style="bold"),
        Text("yes" if pair.broken.failure_observed else "no"),
        Text("yes" if pair.fixed.failure_observed else "no"),
    )
    console.print(table)
    console.print()
    if console.width >= WIDE_TERMINAL:
        side = Table(show_header=True, header_style="bold", show_lines=False)
        side.add_column("Broken trace", overflow="fold")
        side.add_column("Fixed trace", overflow="fold")
        side.add_row(Text(pair.broken.trace.render()), Text(pair.fixed.trace.render()))
        console.print(side)
    else:
        for name, outcome in (("Broken", pair.broken), ("Fixed", pair.fixed)):
            console.print(Text(f"{name} trace", style="bold"))
            for line in outcome.trace.render().splitlines():
                console.print(Text(f"  {line}"), soft_wrap=True)
            console.print()
    show_verdict(console, [pair.broken, pair.fixed])
