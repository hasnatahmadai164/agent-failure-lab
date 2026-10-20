import pytest

from agent_failure_lab.sim import (
    Agent,
    Guard,
    ManualClock,
    Reply,
    RunState,
    ScriptedLLM,
    Stop,
    Tool,
    ToolCall,
    ToolRegistry,
    ToolSpec,
    user_message,
)


class RecordingScope:
    def __init__(self) -> None:
        self.events: list[str] = []

    def begin(self) -> None:
        self.events.append("begin")

    def end(self) -> None:
        self.events.append("end")


def _agent(
    scope: RecordingScope, steps: list[Reply], *, guards: list[Guard] | None = None
) -> Agent:
    def work(arguments: object) -> str:
        scope.events.append("call")
        return "ok"

    tools = ToolRegistry([Tool(ToolSpec("work", "Do some work."), work)])
    return Agent(
        ScriptedLLM(steps),
        tools,
        clock=ManualClock(),
        guards=guards or [],
        batch=scope,
    )


def _calls(count: int) -> Reply:
    return Reply(tool_calls=tuple(ToolCall("work", {"n": n}) for n in range(count)))


def test_several_calls_in_one_turn_run_inside_a_single_batch() -> None:
    scope = RecordingScope()

    _agent(scope, [_calls(2), Reply("done")]).run([user_message("go")])

    assert scope.events == ["begin", "call", "call", "end"]


def test_a_turn_with_one_call_does_not_open_a_batch() -> None:
    scope = RecordingScope()

    _agent(scope, [_calls(1), Reply("done")]).run([user_message("go")])

    assert scope.events == ["call"]


def test_the_batch_is_closed_when_a_guard_stops_the_turn_part_way() -> None:
    class StopOnSecondCall(Guard):
        def before_tool(self, run: RunState, call: ToolCall) -> Stop | None:
            return Stop("enough") if call.arguments["n"] == 1 else None

    scope = RecordingScope()
    agent = _agent(scope, [_calls(2)], guards=[StopOnSecondCall()])

    agent.run([user_message("go")])

    assert scope.events == ["begin", "call", "end"]


def test_the_batch_is_closed_when_a_tool_raises_an_unexpected_error() -> None:
    scope = RecordingScope()

    def explode(arguments: object) -> str:
        raise RuntimeError("bug in the tool")

    tools = ToolRegistry([Tool(ToolSpec("work", "Do some work."), explode)])
    agent = Agent(ScriptedLLM([_calls(2)]), tools, clock=ManualClock(), batch=scope)

    with pytest.raises(RuntimeError, match="bug in the tool"):
        agent.run([user_message("go")])

    assert scope.events == ["begin", "end"]


def test_without_a_batch_scope_several_calls_simply_run_one_after_another() -> None:
    events: list[str] = []
    tools = ToolRegistry(
        [Tool(ToolSpec("work", "Do some work."), lambda arguments: events.append("call") or "ok")]
    )
    agent = Agent(ScriptedLLM([_calls(2), Reply("done")]), tools, clock=ManualClock())

    agent.run([user_message("go")])

    assert events == ["call", "call"]
