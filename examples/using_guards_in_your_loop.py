"""Use the guards in a loop that does not use this library's Agent.

A guard is a plain object with five hooks. Your own loop calls them at the same points the
library's loop does and acts on what they return:

    None          leave things as they are
    a value       use it in place of the original (a tool call, a tool result)
    Block(result) skip the tool and use this result instead
    Stop(reason)  end the run

This loop calls three of the hooks. before_model and after_model work the same way.

Run it with:  python examples/using_guards_in_your_loop.py
"""

from collections.abc import Sequence

from agent_failure_lab.guards import LoopDetector, StepBudget
from agent_failure_lab.sim import (
    Block,
    Guard,
    ManualClock,
    Message,
    Role,
    RunState,
    Stop,
    ToolCall,
    ToolResult,
    ToolSpec,
    Trace,
    system_message,
    tool_message,
    user_message,
)

LOOKUP = ToolSpec("lookup_order", "Look up the status of an order.")


def lookup_order() -> str:
    return "order A-1: pending, no update available"


def ask_model(history: Sequence[Message]) -> ToolCall:
    """Stands in for your model call. This one keeps asking for the same lookup."""
    return ToolCall("lookup_order", {"order_id": "A-1"}, id=f"call_{len(history)}")


def before_tool(guards: Sequence[Guard], run: RunState, call: ToolCall) -> ToolCall | Block | Stop:
    for guard in guards:
        outcome = guard.before_tool(run, call)
        if isinstance(outcome, Block | Stop):
            return outcome
        if outcome is not None:
            call = outcome
    return call


def after_tool(
    guards: Sequence[Guard], run: RunState, call: ToolCall, result: ToolResult
) -> ToolResult | Stop:
    for guard in guards:
        outcome = guard.after_tool(run, call, result)
        if isinstance(outcome, Stop):
            return outcome
        if outcome is not None:
            result = outcome
    return result


def run_loop(guards: Sequence[Guard], *, limit: int = 12) -> tuple[str, RunState]:
    clock = ManualClock()
    run = RunState(
        clock=clock,
        trace=Trace(clock),
        tool_specs=[LOOKUP],
        history=[system_message("Answer questions about orders."), user_message("Where is A-1?")],
    )
    tool_calls = 0
    for step in range(1, limit + 1):
        run.step = step
        call = ask_model(run.history)
        run.append(Message(Role.ASSISTANT, tool_calls=(call,)))

        prepared = before_tool(guards, run, call)
        if isinstance(prepared, Stop):
            return f"stopped: {prepared.reason}", run
        if isinstance(prepared, Block):
            result = prepared.result
        else:
            result = ToolResult(lookup_order())
            tool_calls += 1
        checked = after_tool(guards, run, call, result)
        if isinstance(checked, Stop):
            return f"stopped: {checked.reason}", run
        run.append(tool_message(call, checked.content, is_error=checked.is_error))

        for guard in guards:
            stop = guard.on_step_end(run)
            if stop is not None:
                return f"stopped: {stop.reason}", run
    return f"ran all {limit} steps and made {tool_calls} real tool calls", run


def main() -> None:
    plain, _ = run_loop([])
    print(f"Without guards: {plain}")

    guarded, run = run_loop([LoopDetector(max_repeats=3), StepBudget(10)])
    print(f"With guards:    {guarded}")
    print()
    print("What the guards did:")
    for event in run.trace.events:
        print(f"  step {event.step}: {event.summary}")


if __name__ == "__main__":
    main()
