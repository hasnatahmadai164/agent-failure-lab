from collections.abc import Mapping, Sequence
from typing import Any

from agent_failure_lab.guards import Pricing
from agent_failure_lab.scenario import Outcome, Variant
from agent_failure_lab.sim import (
    Agent,
    EventKind,
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

MAX_STEPS = 40
COST_CEILING = 0.5
COMPLETION_RESERVE = 64
# Illustrative rates in arbitrary cost units per million tokens, not any provider's prices.
PRICING = Pricing(prompt_per_million=100.0, completion_per_million=200.0)
SYSTEM_PROMPT = "You are a research assistant. Search the documents, then give a final answer."
TASK = "What is our refund policy for damaged items?"
SEARCH = "search_docs"
_EXCERPT = (
    "Section text about damaged items, returns, courier claims and refund timing. " * 8
).strip()


def search_tool() -> Tool:
    def search(arguments: Mapping[str, Any]) -> str:
        return f"results for '{arguments['query']}': {_EXCERPT}"

    spec = ToolSpec(
        SEARCH,
        "Search the policy documents.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    )
    return Tool(spec, search)


def restless_agent(messages: Sequence[Message]) -> Reply:
    """Never satisfied with the results, so it searches again with a slightly different query."""
    searches = sum(1 for m in messages for call in m.tool_calls if call.name == SEARCH)
    return Reply(
        tool_calls=(ToolCall(SEARCH, {"query": f"refund policy revision {searches + 1}"}),)
    )


def play(variant: Variant, *, guards: Sequence[Guard] = ()) -> Outcome:
    agent = Agent(
        ScriptedLLM([restless_agent], repeat_last=True),
        ToolRegistry([search_tool()]),
        clock=ManualClock(),
        guards=guards,
        max_steps=MAX_STEPS,
    )
    result = agent.run([system_message(SYSTEM_PROMPT), user_message(TASK)])

    cost = PRICING.cost(result.usage)
    over = cost > COST_CEILING
    findings: tuple[str, ...] = ()
    if over:
        findings = (
            f"The run cost {cost:.4f} units against a ceiling of {COST_CEILING:g}. "
            "Every search used different words, so nothing looked like a loop.",
        )
    elif result.stop_reason is StopReason.GUARD_STOP:
        findings = (f"A guard ended the run before the ceiling was reached: {result.stop_detail}.",)
    return Outcome(
        variant,
        failure_observed=over,
        trace=agent.trace,
        metrics={
            "steps": result.steps,
            "total_tokens": result.usage.total_tokens,
            "cost_units": round(cost, 4),
            "cost_ceiling": COST_CEILING,
            "stop_reason": result.stop_reason.value,
            "guard_interventions": len(agent.trace.of_kind(EventKind.GUARD)),
        },
        findings=findings,
    )
