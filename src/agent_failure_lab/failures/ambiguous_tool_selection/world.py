import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from agent_failure_lab.guards import lint_descriptions
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
    Tool,
    ToolCall,
    ToolRegistry,
    ToolSpec,
    system_message,
    user_message,
)

TICKET = "T-9"
NOTE_TEXT = "Refund approved pending a manager check."
SYSTEM_PROMPT = "You are a support assistant. Use the tools to complete the task."
TASK = f"Leave an internal note on ticket {TICKET} saying: {NOTE_TEXT}"

_PARAMETERS = {
    "type": "object",
    "properties": {"ticket_id": {"type": "string"}, "text": {"type": "string"}},
    "required": ["ticket_id", "text"],
}
_WORD = re.compile(r"[a-z0-9]+")
_COMMON = frozenset(
    {"a", "an", "the", "to", "of", "on", "for", "in", "that", "will", "only", "can"}
)

# Two tools whose descriptions say almost the same thing.
AMBIGUOUS_SPECS = (
    ToolSpec("send_reply", "Add a message to a support ticket.", _PARAMETERS, ("writes-ticket",)),
    ToolSpec("add_note", "Add a comment to a support ticket.", _PARAMETERS, ("writes-ticket",)),
)

# The same two tools, with descriptions that say who sees the result.
CLEAR_SPECS = (
    ToolSpec(
        "send_reply",
        "Send a reply that the customer will see. Not for internal remarks.",
        _PARAMETERS,
        ("writes-ticket",),
    ),
    ToolSpec(
        "add_note",
        "Add an internal note to the ticket that only staff can see.",
        _PARAMETERS,
        ("writes-ticket",),
    ),
)


class Helpdesk:
    """A fake ticket system that records what the customer can see and what only staff can."""

    def __init__(self) -> None:
        self.customer_messages: list[str] = []
        self.internal_notes: list[str] = []


def helpdesk_tools(specs: Sequence[ToolSpec], helpdesk: Helpdesk) -> list[Tool]:
    def send_reply(arguments: Mapping[str, Any]) -> str:
        helpdesk.customer_messages.append(str(arguments["text"]))
        return f"reply sent to the customer on {arguments['ticket_id']}"

    def add_note(arguments: Mapping[str, Any]) -> str:
        helpdesk.internal_notes.append(str(arguments["text"]))
        return f"internal note added to {arguments['ticket_id']}"

    functions = {"send_reply": send_reply, "add_note": add_note}
    return [Tool(spec, functions[spec.name]) for spec in specs]


def _words(text: str) -> frozenset[str]:
    return frozenset(_WORD.findall(text.lower())) - _COMMON


def choose_tool(request: str, specs: Sequence[ToolSpec]) -> str:
    """Pick the tool whose description shares the most words with the request.

    Ties go to the tool listed first, which is what an unsure model drifts towards.
    """
    asked = _words(request)
    return max(specs, key=lambda spec: len(asked & _words(spec.description))).name


def helpdesk_agent(specs: Sequence[ToolSpec]) -> Callable[[Sequence[Message]], Reply]:
    def agent(messages: Sequence[Message]) -> Reply:
        used = [m.name for m in messages if m.role is Role.TOOL]
        if used:
            return Reply(f"Done. I used {used[0]}.")
        tool = choose_tool(TASK, specs)
        return Reply(tool_calls=(ToolCall(tool, {"ticket_id": TICKET, "text": NOTE_TEXT}),))

    return agent


def play(variant: Variant, *, specs: Sequence[ToolSpec], guards: Sequence[Guard] = ()) -> Outcome:
    helpdesk = Helpdesk()
    agent = Agent(
        ScriptedLLM([helpdesk_agent(specs)], repeat_last=True),
        ToolRegistry(helpdesk_tools(specs, helpdesk)),
        clock=ManualClock(),
        guards=guards,
        max_steps=4,
    )
    agent.run([system_message(SYSTEM_PROMPT), user_message(TASK)])

    findings: tuple[str, ...] = ()
    if helpdesk.customer_messages:
        findings = (
            "An internal remark was sent to the customer: "
            f"'{helpdesk.customer_messages[0]}' The user asked for a note only staff can see.",
        )
    return Outcome(
        variant,
        failure_observed=bool(helpdesk.customer_messages),
        trace=agent.trace,
        metrics={
            "customer_messages_sent": len(helpdesk.customer_messages),
            "internal_notes_added": len(helpdesk.internal_notes),
            "tool_chosen": choose_tool(TASK, specs),
            "description_problems": len(lint_descriptions(specs)),
            "guard_interventions": len(agent.trace.of_kind(EventKind.GUARD)),
        },
        findings=findings,
    )
