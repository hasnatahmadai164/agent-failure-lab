from collections.abc import Mapping, Sequence
from typing import Any

from agent_failure_lab.guards import IdempotencyStore
from agent_failure_lab.scenario import Outcome, Variant
from agent_failure_lab.sim import (
    Agent,
    Fail,
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

ORDER_ID = "A-1001"
AMOUNT = 49.0
SYSTEM_PROMPT = "You are a billing assistant. Use the tools to complete the task."
TASK = f"Charge order {ORDER_ID} for {AMOUNT:.2f} EUR."


class PaymentProvider:
    """A fake payment gateway that records every charge it actually performs."""

    def __init__(self) -> None:
        self.charges: list[tuple[str, float]] = []

    def charge(self, order_id: str, amount: float) -> str:
        self.charges.append((order_id, amount))
        return f"charged {amount:.2f} EUR for order {order_id}"


def billing_agent(messages: Sequence[Message]) -> Reply:
    """Charges the order, and simply tries again if the charge reports an error."""
    last = messages[-1]
    if last.role is Role.TOOL and not last.is_error:
        return Reply(f"Order {ORDER_ID} has been charged.")
    call = ToolCall("charge_card", {"order_id": ORDER_ID, "amount": AMOUNT})
    return Reply(tool_calls=(call,))


def charge_tool(provider: PaymentProvider, store: IdempotencyStore | None) -> Tool:
    """The first attempt reaches the gateway and charges, but the reply never makes it back."""

    def charge(arguments: Mapping[str, Any]) -> str:
        def perform() -> str:
            return provider.charge(str(arguments["order_id"]), float(arguments["amount"]))

        key = arguments.get("idempotency_key")
        if store is None or key is None:
            return perform()
        return store.execute(str(key), perform)

    spec = ToolSpec(
        "charge_card",
        "Charge the customer's card for an order.",
        parameters={
            "type": "object",
            "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}},
            "required": ["order_id", "amount"],
        },
        side_effects=("charges-card",),
    )
    lost_reply = Fail("gateway timeout: no response received", effects_applied=True)
    return Tool(spec, charge, schedule=[lost_reply])


def play(
    variant: Variant,
    *,
    guards: Sequence[Guard] = (),
    store: IdempotencyStore | None = None,
) -> Outcome:
    provider = PaymentProvider()
    tool = charge_tool(provider, store)
    agent = Agent(
        ScriptedLLM([billing_agent], repeat_last=True),
        ToolRegistry([tool]),
        clock=ManualClock(),
        guards=guards,
        max_steps=6,
    )
    agent.run([system_message(SYSTEM_PROMPT), user_message(TASK)])

    charges = len(provider.charges)
    total = sum(amount for _, amount in provider.charges)
    replays = store.replays if store is not None else 0
    findings: tuple[str, ...] = ()
    if charges > 1:
        findings = (f"Order {ORDER_ID} was charged {charges} times ({total:.2f} EUR in total).",)
    elif replays:
        findings = ("The retry reused the stored result, so the card was charged once.",)
    return Outcome(
        variant,
        failure_observed=charges > 1,
        trace=agent.trace,
        metrics={"charges": charges, "tool_calls": tool.call_count, "replayed_calls": replays},
        findings=findings,
    )
