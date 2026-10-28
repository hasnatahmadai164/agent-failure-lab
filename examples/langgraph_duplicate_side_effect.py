"""The duplicate-side-effect failure and its fix, written as a LangGraph graph.

A charge reaches the payment gateway but the reply is lost, so the tool reports a timeout and
the agent retries. Without protection the card is charged twice. With a stable idempotency
key attached to the call, and a store on the side that does the work, the retry returns the
stored result and the card is charged once.

The graph has two nodes, one that asks the model what to do and one that runs the tool. The
guard classes are the same ones the library's own loop uses: the tool node calls their hooks.

Install the extra first:  pip install "agent-failure-lab[langgraph]"
Run it with:              python examples/langgraph_duplicate_side_effect.py
"""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from agent_failure_lab.guards import KEY_ARGUMENT, IdempotencyKeys, IdempotencyStore
from agent_failure_lab.sim import (
    ManualClock,
    Message,
    Role,
    RunState,
    ToolCall,
    ToolSpec,
    Trace,
    tool_message,
    user_message,
)

CHARGE = ToolSpec("charge_card", "Charge the card for an order.", side_effects=("charges-card",))
CALL = ToolCall("charge_card", {"order_id": "A-1001", "amount": 49.0})


class Gateway:
    """A payment gateway that charges, then loses the reply the first time."""

    def __init__(self) -> None:
        self.charges: list[str] = []
        self.calls = 0

    def charge(self, order_id: str) -> str:
        self.charges.append(order_id)
        return f"charged order {order_id}"


class State(TypedDict):
    messages: list[Message]


def build_graph(gateway: Gateway, *, protected: bool) -> Any:
    store = IdempotencyStore()
    guard = IdempotencyKeys(key_fields=["order_id"])
    clock = ManualClock()
    run = RunState(clock=clock, trace=Trace(clock), tool_specs=[CHARGE], history=[])

    def model_node(state: State) -> State:
        """Charge the order, and try again if the last tool result was an error."""
        last = state["messages"][-1]
        if last.role is Role.TOOL and not last.is_error:
            return {"messages": [Message(Role.ASSISTANT, "The order has been charged.")]}
        return {"messages": [Message(Role.ASSISTANT, tool_calls=(CALL,))]}

    def tool_node(state: State) -> State:
        call = state["messages"][-1].tool_calls[0]
        if protected:
            call = guard.before_tool(run, call) or call
        gateway.calls += 1
        key = call.arguments.get(KEY_ARGUMENT)
        order_id = str(call.arguments["order_id"])
        if protected and key is not None:
            outcome = store.execute(str(key), lambda: gateway.charge(order_id))
        else:
            outcome = gateway.charge(order_id)
        if gateway.calls == 1:
            return {"messages": [tool_message(call, "timeout: no response", is_error=True)]}
        return {"messages": [tool_message(call, outcome)]}

    def route(state: State) -> str:
        return "tools" if state["messages"][-1].tool_calls else "done"

    graph = StateGraph(State)
    graph.add_node("model", model_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", route, {"tools": "tools", "done": END})
    graph.add_edge("tools", "model")
    return graph.compile()


def charges_for(*, protected: bool) -> int:
    gateway = Gateway()
    app = build_graph(gateway, protected=protected)
    app.invoke({"messages": [user_message("Charge order A-1001.")]}, {"recursion_limit": 12})
    return len(gateway.charges)


def main() -> None:
    print(f"Without the guard the card was charged {charges_for(protected=False)} times.")
    print(f"With the guard the card was charged {charges_for(protected=True)} time.")


if __name__ == "__main__":
    main()
