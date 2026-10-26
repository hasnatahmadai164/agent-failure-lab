import json
from collections.abc import Sequence
from typing import Any

from agent_failure_lab.runner import PairResult
from agent_failure_lab.scenario import MetricValue, Outcome, Scenario, Variant

LIVE_NOTICE = (
    "Live run against a real model. The result is not deterministic and "
    "the failure may not reproduce."
)
SIMULATED_NOTICE = "Scripted model, no network. The result is the same on every run."


def format_value(value: MetricValue) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def status_label(outcome: Outcome) -> str:
    if outcome.failure_observed:
        return "failure observed"
    return "no failure"


def contract_holds(outcomes: Sequence[Outcome]) -> bool | None:
    """Whether the broken variant failed and the fixed one did not, or None if both did not run."""
    by_variant = {outcome.variant: outcome for outcome in outcomes}
    if Variant.BROKEN not in by_variant or Variant.FIXED not in by_variant:
        return None
    return (
        by_variant[Variant.BROKEN].failure_observed
        and not by_variant[Variant.FIXED].failure_observed
    )


def scenario_data(scenario: Scenario) -> dict[str, Any]:
    return {
        "slug": scenario.slug,
        "title": scenario.title,
        "category": scenario.category,
        "summary": scenario.summary,
        "fix": scenario.fix,
        "guards": list(scenario.guards),
        "supports_live": scenario.supports_live,
    }


def outcome_data(outcome: Outcome, *, include_trace: bool) -> dict[str, Any]:
    data: dict[str, Any] = {
        "variant": outcome.variant.value,
        "failure_observed": outcome.failure_observed,
        "metrics": dict(outcome.metrics),
        "findings": list(outcome.findings),
    }
    if include_trace:
        data["trace"] = outcome.trace.to_dict()["events"]
    return data


def run_data(
    scenario: Scenario,
    outcomes: Sequence[Outcome],
    *,
    include_trace: bool,
    model: str | None = None,
) -> dict[str, Any]:
    return {
        "mode": "live" if model else "simulated",
        "model": model,
        "scenario": scenario_data(scenario),
        "outcomes": [outcome_data(o, include_trace=include_trace) for o in outcomes],
        "contract_holds": None if model else contract_holds(outcomes),
    }


def pair_data(pair: PairResult, *, include_trace: bool) -> dict[str, Any]:
    return {
        **scenario_data(pair.scenario),
        "broken": outcome_data(pair.broken, include_trace=include_trace),
        "fixed": outcome_data(pair.fixed, include_trace=include_trace),
        "contract_holds": pair.contract_holds,
    }


def all_data(pairs: Sequence[PairResult], *, include_findings: bool = True) -> dict[str, Any]:
    results = [pair_data(pair, include_trace=False) for pair in pairs]
    if not include_findings:
        for result in results:
            result["broken"].pop("findings")
            result["fixed"].pop("findings")
    return {
        "mode": "simulated",
        "results": results,
        "fixed_still_failing": [p.scenario.slug for p in pairs if p.fixed_still_fails],
    }


def to_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2)


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _metrics_table(outcome: Outcome) -> list[str]:
    if not outcome.metrics:
        return []
    lines = ["| Metric | Value |", "| --- | --- |"]
    lines += [f"| {_cell(k)} | {_cell(format_value(v))} |" for k, v in outcome.metrics.items()]
    return [*lines, ""]


def outcome_markdown(outcome: Outcome, *, include_trace: bool, level: int = 3) -> str:
    heading = "#" * level
    lines = [f"{heading} {outcome.variant.value.capitalize()} variant: {status_label(outcome)}", ""]
    lines += _metrics_table(outcome)
    lines += [f"- {finding}" for finding in outcome.findings]
    if outcome.findings:
        lines.append("")
    if include_trace:
        lines += ["Trace:", "", "```text", outcome.trace.render(), "```", ""]
    return "\n".join(lines)


def run_markdown(
    scenario: Scenario,
    outcomes: Sequence[Outcome],
    *,
    include_trace: bool,
    model: str | None = None,
    level: int = 2,
) -> str:
    lines = [f"{'#' * level} {scenario.slug}", "", scenario.summary, ""]
    lines += [f"> {LIVE_NOTICE} Model: {model}." if model else f"> {SIMULATED_NOTICE}", ""]
    parts = ["\n".join(lines)]
    parts += [outcome_markdown(o, include_trace=include_trace, level=level + 1) for o in outcomes]
    holds = None if model else contract_holds(outcomes)
    if holds is not None:
        parts.append(verdict_sentence(holds) + "\n")
    return "\n".join(parts)


def verdict_sentence(holds: bool) -> str:
    if holds:
        return "The broken variant fails and the fixed variant does not."
    return "The two variants do not behave as intended: check which one failed or did not."


def all_markdown(pairs: Sequence[PairResult]) -> str:
    lines = [
        "| Failure | Category | Broken | Fixed | Result |",
        "| --- | --- | --- | --- | --- |",
    ]
    for pair in pairs:
        fixed = "fails" if pair.fixed_still_fails else "clean"
        broken = "reproduced" if pair.broken_reproduced else "not seen"
        result = "ok" if pair.contract_holds else "check"
        lines.append(
            f"| `{pair.scenario.slug}` | {pair.scenario.category} | {broken} | {fixed} | {result} |"
        )
    return "\n".join(lines) + "\n"


def report_markdown(pairs: Sequence[PairResult]) -> str:
    parts = ["# Results", "", f"> {SIMULATED_NOTICE}", "", all_markdown(pairs)]
    for pair in pairs:
        outcomes = [pair.broken, pair.fixed]
        parts.append(run_markdown(pair.scenario, outcomes, include_trace=False, level=2))
    return "\n".join(parts)
