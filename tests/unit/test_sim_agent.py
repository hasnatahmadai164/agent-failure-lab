from collections.abc import Sequence
from dataclasses import dataclass, replace

import pytest

from agent_failure_lab.sim import (
    Agent,
    Block,
    Delay,
    EventKind,
    Fail,
    Guard,
    ManualClock,
    Message,
    ModelTurn,
    Reply,
    Role,
    RunResult,
    RunState,
    ScriptedLLM,
    Stop,
    StopReason,
    Tool,
    ToolCall,
    ToolRegistry,
    ToolResult,
    ToolSpec,
    estimate_message_tokens,
    user_message,
)
from agent_failure_lab.sim.llm import ScriptStep

TASK = [user_message("do the task")]


def echo_tool(schedule: Sequence[Fail | Delay | None] = ()) -> Tool:
    spec = ToolSpec("echo", "Echo the text back.")
    return Tool(spec, lambda arguments: f"echo:{arguments['text']}", schedule)


def call_echo(text: str = "hi") -> ToolCall:
    return ToolCall("echo", {"text": text})


@dataclass
class Rig:
    agent: Agent
    llm: ScriptedLLM
    clock: ManualClock


def build_rig(
    steps: Sequence[ScriptStep],
    tools: Sequence[Tool] = (),
    *,
    guards: Sequence[Guard] = (),
    max_steps: int = 10,
    tool_timeout: float | None = None,
    repeat_last: bool = False,
) -> Rig:
    clock = ManualClock()
    llm = ScriptedLLM(steps, repeat_last=repeat_last)
    agent = Agent(
        llm,
        ToolRegistry(tools),
        clock=clock,
        guards=guards,
        max_steps=max_steps,
        tool_timeout=tool_timeout,
    )
    return Rig(agent, llm, clock)


def tool_messages(result: RunResult) -> list[Message]:
    return [message for message in result.messages if message.role is Role.TOOL]


def test_a_reply_without_tool_calls_is_the_final_answer() -> None:
    rig = build_rig([Reply("all done")])

    result = rig.agent.run(TASK)

    assert result.stop_reason is StopReason.FINAL_ANSWER
    assert result.final_answer == "all done"
    assert result.steps == 1


def test_tool_results_are_fed_back_to_the_model_before_the_final_answer() -> None:
    rig = build_rig([Reply(tool_calls=(call_echo("a"),)), Reply("finished")], [echo_tool()])

    result = rig.agent.run(TASK)

    assert [message.role for message in result.messages] == [
        Role.USER,
        Role.ASSISTANT,
        Role.TOOL,
        Role.ASSISTANT,
    ]
    tool_result = tool_messages(result)[0]
    assert tool_result.content == "echo:a"
    assert tool_result.tool_call_id == "call_1"
    assert result.final_answer == "finished"


def test_a_call_to_an_unknown_tool_becomes_an_error_result_and_the_run_continues() -> None:
    rig = build_rig([Reply(tool_calls=(ToolCall("missing", {}),)), Reply("recovered")])

    result = rig.agent.run(TASK)

    error = tool_messages(result)[0]
    assert error.is_error
    assert "unknown tool 'missing'" in error.content
    assert result.final_answer == "recovered"


def test_a_failing_tool_becomes_an_error_result() -> None:
    rig = build_rig(
        [Reply(tool_calls=(call_echo(),)), Reply("noted")],
        [echo_tool([Fail("backend down")])],
    )

    result = rig.agent.run(TASK)

    error = tool_messages(result)[0]
    assert error.is_error
    assert error.content == "error: backend down"


def test_the_run_stops_at_the_step_limit_when_the_model_never_answers() -> None:
    tool = echo_tool()
    rig = build_rig([Reply(tool_calls=(call_echo(),))], [tool], max_steps=3, repeat_last=True)

    result = rig.agent.run(TASK)

    assert result.stop_reason is StopReason.STEP_LIMIT
    assert result.final_answer is None
    assert result.steps == 3
    assert tool.call_count == 3


def test_usage_is_summed_over_every_model_call() -> None:
    rig = build_rig([Reply(tool_calls=(call_echo(),)), Reply("done")], [echo_tool()])

    result = rig.agent.run(TASK)

    model_events = rig.agent.trace.of_kind(EventKind.MODEL)
    assert result.usage.prompt_tokens == sum(e.data["prompt_tokens"] for e in model_events)
    assistant_tokens = sum(
        estimate_message_tokens(m) for m in result.messages if m.role is Role.ASSISTANT
    )
    assert result.usage.completion_tokens == assistant_tokens
    assert model_events[1].data["prompt_tokens"] > model_events[0].data["prompt_tokens"]


def test_elapsed_seconds_reflects_time_spent_waiting_on_tools() -> None:
    rig = build_rig([Reply(tool_calls=(call_echo(),)), Reply("done")], [echo_tool([Delay(30)])])

    result = rig.agent.run(TASK)

    assert result.elapsed_seconds == 30


def test_the_trace_records_model_tool_and_stop_events_in_order() -> None:
    rig = build_rig([Reply(tool_calls=(call_echo(),)), Reply("done")], [echo_tool()])

    rig.agent.run(TASK)

    kinds = [event.kind for event in rig.agent.trace.events]
    assert kinds == [
        EventKind.MODEL,
        EventKind.TOOL_CALL,
        EventKind.TOOL_RESULT,
        EventKind.MODEL,
        EventKind.STOP,
    ]


def test_max_steps_below_one_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        build_rig([Reply("x")], max_steps=0)


class BlockEverything(Guard):
    def before_tool(self, run: RunState, call: ToolCall) -> Block:
        run.intervene(self.name, f"blocked {call.name}")
        return Block(ToolResult("blocked by policy"))


def test_a_blocked_tool_call_is_not_executed_and_the_model_sees_the_replacement() -> None:
    tool = echo_tool()
    rig = build_rig(
        [Reply(tool_calls=(call_echo(),)), Reply("ok")], [tool], guards=[BlockEverything()]
    )

    result = rig.agent.run(TASK)

    assert tool.call_count == 0
    assert tool_messages(result)[0].content == "blocked by policy"


class RewriteArguments(Guard):
    def before_tool(self, run: RunState, call: ToolCall) -> ToolCall:
        return replace(call, arguments={"text": "repaired"})


def test_a_guard_can_replace_tool_arguments_before_execution() -> None:
    rig = build_rig(
        [Reply(tool_calls=(call_echo("original"),)), Reply("ok")],
        [echo_tool()],
        guards=[RewriteArguments()],
    )

    result = rig.agent.run(TASK)

    assert tool_messages(result)[0].content == "echo:repaired"


class Redact(Guard):
    def after_tool(self, run: RunState, call: ToolCall, result: ToolResult) -> ToolResult:
        return ToolResult("[redacted]")


def test_a_guard_can_replace_a_tool_result_before_the_model_sees_it() -> None:
    rig = build_rig(
        [Reply(tool_calls=(call_echo(),)), Reply("ok")], [echo_tool()], guards=[Redact()]
    )

    result = rig.agent.run(TASK)

    assert tool_messages(result)[0].content == "[redacted]"


class LastMessageOnly(Guard):
    def before_model(self, run: RunState, messages: Sequence[Message]) -> Sequence[Message]:
        return messages[-1:]


def test_a_guard_changes_only_what_the_model_sees_not_the_recorded_history() -> None:
    seen: list[int] = []

    def reply(messages: Sequence[Message]) -> Reply:
        seen.append(len(messages))
        return Reply("ok")

    rig = build_rig([reply], guards=[LastMessageOnly()])

    result = rig.agent.run([user_message("one"), user_message("two"), user_message("three")])

    assert seen == [1]
    assert len(result.messages) == 4


class StopAtStepEnd(Guard):
    def on_step_end(self, run: RunState) -> Stop:
        return Stop("budget spent")


def test_a_stop_at_step_end_ends_the_run_with_the_guards_reason() -> None:
    rig = build_rig(
        [Reply(tool_calls=(call_echo(),))],
        [echo_tool()],
        guards=[StopAtStepEnd()],
        repeat_last=True,
    )

    result = rig.agent.run(TASK)

    assert result.stop_reason is StopReason.GUARD_STOP
    assert result.stop_detail == "budget spent"
    assert result.steps == 1


class StopBeforeModel(Guard):
    def before_model(self, run: RunState, messages: Sequence[Message]) -> Stop:
        return Stop("not allowed to start")


def test_a_stop_before_the_model_call_prevents_the_call() -> None:
    rig = build_rig([Reply("never reached")], guards=[StopBeforeModel()])

    result = rig.agent.run(TASK)

    assert result.stop_reason is StopReason.GUARD_STOP
    assert rig.llm.turns_taken == 0


class StopAfterModel(Guard):
    def after_model(self, run: RunState, turn: ModelTurn) -> Stop:
        return Stop("answer rejected")


def test_a_stop_after_the_model_call_discards_the_turn_from_the_history() -> None:
    rig = build_rig([Reply("a bad answer")], guards=[StopAfterModel()])

    result = rig.agent.run(TASK)

    assert result.stop_reason is StopReason.GUARD_STOP
    assert result.final_answer is None
    assert [message.role for message in result.messages] == [Role.USER]


class Append(Guard):
    def __init__(self, suffix: str) -> None:
        self._suffix = suffix

    def before_tool(self, run: RunState, call: ToolCall) -> ToolCall:
        text = str(call.arguments["text"]) + self._suffix
        return replace(call, arguments={"text": text})


def test_guards_run_in_order_and_each_sees_the_previous_guards_change() -> None:
    rig = build_rig(
        [Reply(tool_calls=(call_echo("x"),)), Reply("ok")],
        [echo_tool()],
        guards=[Append("1"), Append("2")],
    )

    result = rig.agent.run(TASK)

    assert tool_messages(result)[0].content == "echo:x12"


def test_a_block_skips_the_guards_after_it() -> None:
    tool = echo_tool()
    rig = build_rig(
        [Reply(tool_calls=(call_echo(),)), Reply("ok")],
        [tool],
        guards=[BlockEverything(), RewriteArguments()],
    )

    result = rig.agent.run(TASK)

    assert tool_messages(result)[0].content == "blocked by policy"
    assert tool.call_count == 0


def test_interventions_are_recorded_in_the_trace_with_the_step_number() -> None:
    rig = build_rig(
        [Reply(tool_calls=(call_echo(),)), Reply("ok")], [echo_tool()], guards=[BlockEverything()]
    )

    rig.agent.run(TASK)

    (event,) = rig.agent.trace.of_kind(EventKind.GUARD)
    assert event.summary == "BlockEverything: blocked echo"
    assert event.step == 1
    assert event.data["guard"] == "BlockEverything"


class CapToolTime(Guard):
    def before_tool(self, run: RunState, call: ToolCall) -> None:
        run.tool_timeout = 5
        return None


def test_a_guard_can_cap_how_long_the_following_tool_calls_may_take() -> None:
    rig = build_rig(
        [Reply(tool_calls=(call_echo(),)), Reply("gave up")],
        [echo_tool([Delay(3600)])],
        guards=[CapToolTime()],
    )

    result = rig.agent.run(TASK)

    assert "timed out after 5s" in tool_messages(result)[0].content
    assert result.elapsed_seconds == 5


def test_the_agent_level_tool_timeout_applies_without_any_guard() -> None:
    rig = build_rig(
        [Reply(tool_calls=(call_echo(),)), Reply("gave up")],
        [echo_tool([Delay(3600)])],
        tool_timeout=10,
    )

    result = rig.agent.run(TASK)

    assert tool_messages(result)[0].is_error
    assert result.elapsed_seconds == 10


def test_a_tool_with_no_timeout_stalls_for_its_full_delay() -> None:
    rig = build_rig([Reply(tool_calls=(call_echo(),)), Reply("done")], [echo_tool([Delay(3600)])])

    result = rig.agent.run(TASK)

    assert result.elapsed_seconds == 3600
