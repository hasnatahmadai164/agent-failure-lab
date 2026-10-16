from collections.abc import Mapping
from typing import Any

import pytest

from agent_failure_lab.errors import (
    DuplicateToolError,
    ToolExecutionError,
    ToolTimeoutError,
    UnknownToolError,
)
from agent_failure_lab.sim import Delay, Fail, ManualClock, Tool, ToolRegistry, ToolSpec


class Recorder:
    def __init__(self) -> None:
        self.calls: list[Mapping[str, Any]] = []

    def __call__(self, arguments: Mapping[str, Any]) -> str:
        self.calls.append(arguments)
        return "ok"


def _tool(recorder: Recorder, schedule: list[Fail | Delay | None] | None = None) -> Tool:
    return Tool(ToolSpec("work", "Do the work."), recorder, schedule or [])


def test_run_passes_arguments_to_the_function_and_counts_the_call() -> None:
    recorder = Recorder()
    tool = _tool(recorder)

    result = tool.run({"x": 1}, ManualClock())

    assert result == "ok"
    assert recorder.calls == [{"x": 1}]
    assert tool.call_count == 1


def test_scheduled_failure_raises_without_running_the_function() -> None:
    recorder = Recorder()
    tool = _tool(recorder, [Fail("service unavailable")])

    with pytest.raises(ToolExecutionError, match="service unavailable"):
        tool.run({}, ManualClock())

    assert recorder.calls == []


def test_failure_with_effects_applied_runs_the_function_before_raising() -> None:
    recorder = Recorder()
    tool = _tool(recorder, [Fail("response lost", effects_applied=True)])

    with pytest.raises(ToolExecutionError, match="response lost"):
        tool.run({"x": 1}, ManualClock())

    assert recorder.calls == [{"x": 1}]


def test_schedule_applies_by_call_number_then_calls_succeed() -> None:
    recorder = Recorder()
    tool = _tool(recorder, [None, Fail("second call fails")])
    clock = ManualClock()

    assert tool.run({}, clock) == "ok"
    with pytest.raises(ToolExecutionError):
        tool.run({}, clock)
    assert tool.run({}, clock) == "ok"
    assert tool.call_count == 3


def test_delay_advances_the_clock_then_returns_the_result() -> None:
    clock = ManualClock()
    tool = _tool(Recorder(), [Delay(30)])

    result = tool.run({}, clock)

    assert result == "ok"
    assert clock.now() == 30


def test_delay_longer_than_the_timeout_is_cut_off_at_the_timeout() -> None:
    clock = ManualClock()
    recorder = Recorder()
    tool = _tool(recorder, [Delay(3600)])

    with pytest.raises(ToolTimeoutError, match="timed out after 5s"):
        tool.run({}, clock, timeout=5)

    assert clock.now() == 5
    assert recorder.calls == []


def test_delay_equal_to_the_timeout_still_completes() -> None:
    clock = ManualClock()
    tool = _tool(Recorder(), [Delay(5)])

    assert tool.run({}, clock, timeout=5) == "ok"
    assert clock.now() == 5


def test_registry_returns_registered_tools_and_their_specs() -> None:
    tool = _tool(Recorder())
    registry = ToolRegistry([tool])

    assert registry.get("work") is tool
    assert registry.specs() == (tool.spec,)


def test_registry_raises_for_an_unknown_tool_name() -> None:
    with pytest.raises(UnknownToolError, match="missing"):
        ToolRegistry().get("missing")


def test_registry_rejects_a_duplicate_tool_name() -> None:
    registry = ToolRegistry([_tool(Recorder())])

    with pytest.raises(DuplicateToolError, match="work"):
        registry.add(_tool(Recorder()))
