from collections.abc import Mapping, Sequence
from typing import Any

from agent_failure_lab.scenario import Outcome, Variant
from agent_failure_lab.sim import (
    Agent,
    Guard,
    ManualClock,
    Message,
    Reply,
    ScriptedLLM,
    StopReason,
    Tool,
    ToolCall,
    ToolRegistry,
    ToolSpec,
    system_message,
    user_message,
)

ORDER_ID = "A-1001"
MAX_STEPS = 20
SYSTEM_PROMPT = "You are a support assistant. Use the tools to answer the question."
TASK = f"What is the current status of order {ORDER_ID}?"
LOOKUP = "lookup_order_status"


def lookup_tool() -> Tool:
    """The status system answers every time with the same non-answer."""

    def lookup(arguments: Mapping[str, Any]) -> str:
        return f"order {arguments['order_id']}: status pending, no update available"

    spec = ToolSpec(
        LOOKUP,
        "Look up the current status of an order.",
        parameters={
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    )
    return Tool(spec, lookup)


def persistent_agent(messages: Sequence[Message]) -> Reply:
    """Hopes the next lookup will say something new, and never settles for what it has."""
    return Reply(tool_calls=(ToolCall(LOOKUP, {"order_id": ORDER_ID}),))


def play(variant: Variant, *, guards: Sequence[Guard] = ()) -> Outcome:
    tool = lookup_tool()
    agent = Agent(
        ScriptedLLM([persistent_agent], repeat_last=True),
        ToolRegistry([tool]),
        clock=ManualClock(),
        guards=guards,
        max_steps=MAX_STEPS,
    )
    result = agent.run([system_message(SYSTEM_PROMPT), user_message(TASK)])

    ran_to_the_limit = result.stop_reason is StopReason.STEP_LIMIT
    findings: tuple[str, ...] = ()
    if ran_to_the_limit:
        findings = (
            f"{LOOKUP} was called {tool.call_count} times with identical arguments and the "
            "agent never answered. Only the step limit ended the run.",
        )
    elif result.stop_reason is StopReason.GUARD_STOP:
        findings = (f"A guard ended the run: {result.stop_detail}.",)
    return Outcome(
        variant,
        failure_observed=ran_to_the_limit,
        trace=agent.trace,
        metrics={
            "steps": result.steps,
            "tool_calls": tool.call_count,
            "total_tokens": result.usage.total_tokens,
            "stop_reason": result.stop_reason.value,
        },
        findings=findings,
    )
