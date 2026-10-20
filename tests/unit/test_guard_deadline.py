from collections.abc import Callable

import pytest

from agent_failure_lab.guards.deadline import Deadline
from agent_failure_lab.sim import EventKind, RunState, Stop, ToolCall, ToolResult

MakeRun = Callable[..., RunState]

CALL = ToolCall("fetch", {})
TIMED_OUT = ToolResult("error: tool 'fetch' timed out after 5s", is_error=True)


def test_a_deadline_needs_at_least_one_limit() -> None:
    with pytest.raises(ValueError, match="per_call, total or both"):
        Deadline()


@pytest.mark.parametrize("kwargs", [{"per_call": 0}, {"total": -1}])
def test_limits_must_be_positive(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError, match="positive"):
        Deadline(**kwargs)


def test_the_per_call_limit_becomes_the_runs_tool_timeout(make_run: MakeRun) -> None:
    run = make_run()

    assert Deadline(per_call=5).before_tool(run, CALL) is None

    assert run.tool_timeout == 5


def test_the_limit_shrinks_as_the_total_deadline_gets_closer(make_run: MakeRun) -> None:
    run = make_run()
    run.clock.advance(17)

    Deadline(per_call=5, total=20).before_tool(run, CALL)

    assert run.tool_timeout == 3


def test_with_only_a_total_the_limit_is_whatever_time_remains(make_run: MakeRun) -> None:
    run = make_run()
    run.clock.advance(4)

    Deadline(total=10).before_tool(run, CALL)

    assert run.tool_timeout == 6


def test_no_tool_call_starts_once_the_total_deadline_has_passed(make_run: MakeRun) -> None:
    run = make_run()
    run.clock.advance(20)

    outcome = Deadline(per_call=5, total=20).before_tool(run, CALL)

    assert isinstance(outcome, Stop)
    assert "20s" in outcome.reason


def test_no_model_call_starts_once_the_total_deadline_has_passed(make_run: MakeRun) -> None:
    run = make_run()
    guard = Deadline(total=20)

    assert guard.before_model(run, []) is None
    run.clock.advance(20)

    assert isinstance(guard.before_model(run, []), Stop)
    assert len(run.trace.of_kind(EventKind.GUARD)) == 1


def test_a_call_cut_off_at_the_limit_gets_a_message_to_carry_on_with_what_it_has(
    make_run: MakeRun,
) -> None:
    run = make_run()
    guard = Deadline(per_call=5)
    guard.before_tool(run, CALL)
    run.clock.advance(5)

    result = guard.after_tool(run, CALL, TIMED_OUT)

    assert result is not None
    assert result.is_error
    assert "cancelled after 5s" in result.content
    assert "what is missing" in result.content


def test_an_error_that_came_back_quickly_is_left_alone(make_run: MakeRun) -> None:
    run = make_run()
    guard = Deadline(per_call=5)
    guard.before_tool(run, CALL)
    run.clock.advance(1)

    assert guard.after_tool(run, CALL, ToolResult("error: bad input", is_error=True)) is None


def test_a_successful_result_is_left_alone(make_run: MakeRun) -> None:
    run = make_run()
    guard = Deadline(per_call=5)
    guard.before_tool(run, CALL)
    run.clock.advance(5)

    assert guard.after_tool(run, CALL, ToolResult("fine")) is None


def test_a_result_from_a_call_the_guard_never_saw_start_is_left_alone(make_run: MakeRun) -> None:
    guard = Deadline(per_call=5)

    assert guard.after_tool(make_run(), CALL, TIMED_OUT) is None
