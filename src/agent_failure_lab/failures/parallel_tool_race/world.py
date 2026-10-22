import re
from collections.abc import Mapping, Sequence
from typing import Any

from agent_failure_lab.scenario import Outcome, Variant
from agent_failure_lab.sim import (
    Agent,
    EventKind,
    Guard,
    ManualClock,
    Message,
    Reply,
    Role,
    ScriptedLLM,
    SharedStore,
    Tool,
    ToolCall,
    ToolRegistry,
    ToolSpec,
    system_message,
    user_message,
)

TICKET = "T-77"
WANTED_TAGS = ("urgent", "billing")
SYSTEM_PROMPT = "You are a triage assistant. Use the tools to complete the task."
TASK = f"Tag ticket {TICKET} as urgent and as billing."
_CONFIRMATION = re.compile(r"added tag (\S+) to \S+")


def tag_tool(store: SharedStore) -> Tool:
    """Adds a tag by reading the ticket's tags, appending, and writing the list back."""

    def add_tag(arguments: Mapping[str, Any]) -> str:
        ticket = str(arguments["ticket_id"])
        tags = store.get(ticket, [])
        store.set(ticket, [*tags, arguments["tag"]])
        return f"added tag {arguments['tag']} to {ticket}"

    spec = ToolSpec(
        "add_tag",
        "Add a tag to a support ticket.",
        parameters={
            "type": "object",
            "properties": {"ticket_id": {"type": "string"}, "tag": {"type": "string"}},
            "required": ["ticket_id", "tag"],
        },
        side_effects=("changes-ticket",),
    )
    return Tool(spec, add_tag)


def _add(tag: str) -> ToolCall:
    return ToolCall("add_tag", {"ticket_id": TICKET, "tag": tag})


def triage_agent(messages: Sequence[Message]) -> Reply:
    """Asks for both tags at once, then repeats any the tool says it did not apply."""
    results = [m for m in messages if m.role is Role.TOOL]
    if not results:
        return Reply(tool_calls=tuple(_add(tag) for tag in WANTED_TAGS))
    confirmed = set()
    for message in results:
        match = _CONFIRMATION.fullmatch(message.content)
        if match and not message.is_error:
            confirmed.add(match.group(1))
    remaining = [tag for tag in WANTED_TAGS if tag not in confirmed]
    if remaining:
        return Reply(tool_calls=(_add(remaining[0]),))
    return Reply(f"Both tags are on {TICKET}.")


def play(variant: Variant, *, guards: Sequence[Guard] = ()) -> Outcome:
    store = SharedStore({TICKET: []})
    agent = Agent(
        ScriptedLLM([triage_agent], repeat_last=True),
        ToolRegistry([tag_tool(store)]),
        clock=ManualClock(),
        guards=guards,
        max_steps=6,
        batch=store,
    )
    result = agent.run([system_message(SYSTEM_PROMPT), user_message(TASK)])

    saved = store.get(TICKET, [])
    missing = [tag for tag in WANTED_TAGS if tag not in saved]
    findings: tuple[str, ...] = ()
    if missing:
        findings = (
            f"The agent reported: {result.final_answer} The ticket has {saved}. "
            f"One update overwrote the other and '{missing[0]}' was lost.",
        )
    return Outcome(
        variant,
        failure_observed=bool(missing),
        trace=agent.trace,
        metrics={
            "tags_wanted": len(WANTED_TAGS),
            "tags_saved": len(saved),
            "lost_updates": store.lost_updates,
            "model_steps": result.steps,
            "guard_interventions": len(agent.trace.of_kind(EventKind.GUARD)),
        },
        findings=findings,
    )
