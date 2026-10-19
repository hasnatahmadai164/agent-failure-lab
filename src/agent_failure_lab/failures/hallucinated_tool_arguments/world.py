import json
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
    Tool,
    ToolCall,
    ToolRegistry,
    ToolSpec,
    system_message,
    user_message,
)

ORDER_ID = "ORD-1001"
VALID_SPEEDS = ["standard", "express", "overnight"]
SYSTEM_PROMPT = "You are a logistics assistant. Use the tools to complete the task."
TASK = f"Upgrade order {ORDER_ID} to next-day delivery."
UPDATE = "update_shipping"
_ALLOWED = re.compile(r"allowed values: (\[.*?\])")


class OrderDatabase:
    """A fake order store whose update call writes whatever value it is given."""

    def __init__(self) -> None:
        self.shipping_speed = {ORDER_ID: "standard"}

    def invalid_orders(self) -> list[str]:
        return [o for o, speed in self.shipping_speed.items() if speed not in VALID_SPEEDS]


def shipping_tool(database: OrderDatabase) -> Tool:
    def update(arguments: Mapping[str, Any]) -> str:
        database.shipping_speed[str(arguments["order_id"])] = str(arguments["speed"])
        return f"shipping for {arguments['order_id']} set to {arguments['speed']}"

    spec = ToolSpec(
        UPDATE,
        "Change the shipping speed of an order.",
        parameters={
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "pattern": r"^ORD-\d{4}$"},
                "speed": {"type": "string", "enum": VALID_SPEEDS},
            },
            "required": ["order_id", "speed"],
            "additionalProperties": False,
        },
        side_effects=("changes-order",),
    )
    return Tool(spec, update)


def shipping_agent(messages: Sequence[Message]) -> Reply:
    """Invents the value 'next_day', and corrects itself only if the error lists real options."""
    last = messages[-1]
    if last.role is Role.TOOL and last.is_error:
        match = _ALLOWED.search(last.content)
        options = json.loads(match.group(1)) if match else []
        fastest = [option for option in options if "night" in option]
        if fastest:
            return Reply(tool_calls=(_update(fastest[0]),))
        return Reply("I could not update the shipping speed.")
    if last.role is Role.TOOL:
        return Reply(f"Shipping for {ORDER_ID} is now set.")
    return Reply(tool_calls=(_update("next_day"),))


def _update(speed: str) -> ToolCall:
    return ToolCall(UPDATE, {"order_id": ORDER_ID, "speed": speed})


def play(variant: Variant, *, guards: Sequence[Guard] = ()) -> Outcome:
    database = OrderDatabase()
    tool = shipping_tool(database)
    agent = Agent(
        ScriptedLLM([shipping_agent], repeat_last=True),
        ToolRegistry([tool]),
        clock=ManualClock(),
        guards=guards,
        max_steps=6,
    )
    result = agent.run([system_message(SYSTEM_PROMPT), user_message(TASK)])

    invalid = database.invalid_orders()
    findings: tuple[str, ...] = ()
    if invalid:
        speed = database.shipping_speed[invalid[0]]
        findings = (
            f"Order {invalid[0]} now has shipping speed '{speed}', which is not a real option, "
            f"and the agent reported: {result.final_answer}",
        )
    return Outcome(
        variant,
        failure_observed=bool(invalid),
        trace=agent.trace,
        metrics={
            "invalid_values_stored": len(invalid),
            "final_speed": database.shipping_speed[ORDER_ID],
            "tool_calls": tool.call_count,
            "guard_interventions": len(agent.trace.of_kind(EventKind.GUARD)),
        },
        findings=findings,
    )
