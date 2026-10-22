from collections.abc import Mapping, Sequence
from typing import Any

from agent_failure_lab.scenario import Outcome, Variant
from agent_failure_lab.sim import (
    Agent,
    Delay,
    EventKind,
    Guard,
    ManualClock,
    Message,
    Reply,
    Role,
    ScriptedLLM,
    StopReason,
    Tool,
    ToolCall,
    ToolRegistry,
    ToolSpec,
    system_message,
    user_message,
)

RUN_SLA_SECONDS = 30
HANG_SECONDS = 3600
SYSTEM_PROMPT = "You are a reporting assistant. Use the tools to complete the task."
TASK = "Prepare the daily summary from the sales and inventory systems."


def report_tools() -> list[Tool]:
    """The inventory system accepts the request and then never answers in a useful time."""

    def fetch_sales(arguments: Mapping[str, Any]) -> str:
        return "sales data for yesterday"

    def fetch_inventory(arguments: Mapping[str, Any]) -> str:
        return "stock levels for all warehouses"

    return [
        Tool(ToolSpec("fetch_sales", "Fetch yesterday's sales data."), fetch_sales),
        Tool(
            ToolSpec("fetch_inventory", "Fetch current stock levels."),
            fetch_inventory,
            schedule=[Delay(HANG_SECONDS)],
        ),
    ]


def reporting_agent(messages: Sequence[Message]) -> Reply:
    """Asks for each source in turn, and reports honestly on whatever it ends up with."""
    results = {m.name: m for m in messages if m.role is Role.TOOL}
    if "fetch_sales" not in results:
        return Reply(tool_calls=(ToolCall("fetch_sales", {}),))
    if "fetch_inventory" not in results:
        return Reply(tool_calls=(ToolCall("fetch_inventory", {}),))
    if results["fetch_inventory"].is_error:
        return Reply(
            "Daily summary: sales are ready. Inventory data is missing because the "
            "inventory system did not respond in time."
        )
    return Reply("Daily summary: sales and inventory are ready.")


def play(variant: Variant, *, guards: Sequence[Guard] = ()) -> Outcome:
    agent = Agent(
        ScriptedLLM([reporting_agent], repeat_last=True),
        ToolRegistry(report_tools()),
        clock=ManualClock(),
        guards=guards,
        max_steps=6,
    )
    result = agent.run([system_message(SYSTEM_PROMPT), user_message(TASK)])

    over = result.elapsed_seconds > RUN_SLA_SECONDS
    findings: tuple[str, ...] = ()
    if over:
        findings = (
            f"The run took {result.elapsed_seconds:g}s against a limit of {RUN_SLA_SECONDS}s, "
            "waiting on a tool that did not answer.",
        )
    elif result.final_answer and "missing" in result.final_answer:
        findings = ("The run finished in time with a partial summary that says what is missing.",)
    return Outcome(
        variant,
        failure_observed=over,
        trace=agent.trace,
        metrics={
            "elapsed_seconds": result.elapsed_seconds,
            "time_limit_seconds": RUN_SLA_SECONDS,
            "answered": result.stop_reason is StopReason.FINAL_ANSWER,
            "final_answer": result.final_answer or "",
            "guard_interventions": len(agent.trace.of_kind(EventKind.GUARD)),
        },
        findings=findings,
    )
