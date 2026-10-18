from collections.abc import Callable

import pytest

from agent_failure_lab.guards.loops import LoopDetector, StepBudget
from agent_failure_lab.sim import Block, EventKind, RunState, Stop, ToolCall, ToolResult

MakeRun = Callable[..., RunState]

CALL = ToolCall("lookup", {"order_id": "A-1"})
SAME = ToolResult("pending")


def _execute(guard: LoopDetector, run: RunState, call: ToolCall, result: ToolResult) -> None:
    assert guard.before_tool(run, call) is None
    guard.after_tool(run, call, result)


def test_identical_calls_with_identical_results_are_allowed_up_to_the_limit(
    make_run: MakeRun,
) -> None:
    guard = LoopDetector(max_repeats=3)
    run = make_run()

    for _ in range(3):
        _execute(guard, run, CALL, SAME)


def test_the_next_identical_call_is_blocked_with_a_message_to_the_model(
    make_run: MakeRun,
) -> None:
    guard = LoopDetector(max_repeats=3)
    run = make_run()
    for _ in range(3):
        _execute(guard, run, CALL, SAME)

    outcome = guard.before_tool(run, CALL)

    assert isinstance(outcome, Block)
    assert outcome.result.is_error
    assert "Loop detected" in outcome.result.content


def test_repeating_the_call_again_after_the_warning_stops_the_run(make_run: MakeRun) -> None:
    guard = LoopDetector(max_repeats=3, max_warnings=1)
    run = make_run()
    for _ in range(3):
        _execute(guard, run, CALL, SAME)
    guard.before_tool(run, CALL)
    guard.after_tool(run, CALL, ToolResult("Loop detected", is_error=True))

    outcome = guard.before_tool(run, CALL)

    assert isinstance(outcome, Stop)
    assert "loop detected" in outcome.reason


def test_a_call_whose_result_keeps_changing_is_not_a_loop(make_run: MakeRun) -> None:
    guard = LoopDetector(max_repeats=3)
    run = make_run()

    for index in range(6):
        _execute(guard, run, CALL, ToolResult(f"progress {index}"))


def test_different_arguments_are_counted_separately(make_run: MakeRun) -> None:
    guard = LoopDetector(max_repeats=2)
    run = make_run()
    other = ToolCall("lookup", {"order_id": "A-2"})
    for _ in range(2):
        _execute(guard, run, CALL, SAME)

    assert guard.before_tool(run, other) is None


def test_the_blocked_message_is_not_counted_as_a_tool_result(make_run: MakeRun) -> None:
    guard = LoopDetector(max_repeats=2, max_warnings=2)
    run = make_run()
    for _ in range(2):
        _execute(guard, run, CALL, SAME)
    guard.before_tool(run, CALL)
    guard.after_tool(run, CALL, ToolResult("Loop detected", is_error=True))

    assert isinstance(guard.before_tool(run, CALL), Block)


def test_blocking_is_recorded_in_the_trace(make_run: MakeRun) -> None:
    guard = LoopDetector(max_repeats=2)
    run = make_run()
    for _ in range(2):
        _execute(guard, run, CALL, SAME)

    guard.before_tool(run, CALL)

    (event,) = run.trace.of_kind(EventKind.GUARD)
    assert "blocked" in event.summary


@pytest.mark.parametrize(("repeats", "warnings"), [(1, 1), (3, -1)])
def test_loop_detector_rejects_nonsense_limits(repeats: int, warnings: int) -> None:
    with pytest.raises(ValueError, match="max_"):
        LoopDetector(max_repeats=repeats, max_warnings=warnings)


def test_step_budget_lets_earlier_steps_continue(make_run: MakeRun) -> None:
    assert StepBudget(3).on_step_end(make_run(step=2)) is None


def test_step_budget_stops_the_run_when_the_last_step_is_used(make_run: MakeRun) -> None:
    run = make_run(step=3)

    outcome = StepBudget(3).on_step_end(run)

    assert isinstance(outcome, Stop)
    assert "3" in outcome.reason
    assert len(run.trace.of_kind(EventKind.GUARD)) == 1


def test_step_budget_must_allow_at_least_one_step() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        StepBudget(0)
