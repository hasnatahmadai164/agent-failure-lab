from collections.abc import Callable

from agent_failure_lab.guards.postconditions import PostconditionCheck, tool_succeeded
from agent_failure_lab.sim import (
    EventKind,
    Message,
    ModelTurn,
    Role,
    RunState,
    ToolCall,
    Usage,
    tool_message,
    user_message,
)

MakeRun = Callable[..., RunState]

CALL = ToolCall("update_inventory", {"sku": "SKU-9"}, id="call_1")
FAILED = tool_message(CALL, "error: unknown sku", is_error=True)
WORKED = tool_message(CALL, "stock set to 40")
ANSWER = ModelTurn(Message(Role.ASSISTANT, "Inventory has been updated."), Usage(10, 5))


def test_a_tool_that_was_never_called_fails_the_condition() -> None:
    problem = tool_succeeded("update_inventory")([user_message("go")])

    assert problem == "update_inventory was never called"


def test_a_last_result_that_is_an_error_fails_the_condition() -> None:
    problem = tool_succeeded("update_inventory")([FAILED])

    assert problem is not None
    assert "failed" in problem
    assert "unknown sku" in problem


def test_a_successful_last_result_passes_the_condition() -> None:
    assert tool_succeeded("update_inventory")([WORKED]) is None


def test_only_the_latest_result_counts_so_a_retry_that_worked_passes() -> None:
    assert tool_succeeded("update_inventory")([FAILED, WORKED]) is None


def test_a_turn_that_asks_for_more_tool_calls_is_not_checked(make_run: MakeRun) -> None:
    guard = PostconditionCheck([tool_succeeded("update_inventory")])
    turn = ModelTurn(Message(Role.ASSISTANT, tool_calls=(CALL,)), Usage())

    assert guard.after_model(make_run(history=[FAILED]), turn) is None


def test_a_supported_final_answer_goes_through(make_run: MakeRun) -> None:
    guard = PostconditionCheck([tool_succeeded("update_inventory")])

    assert guard.after_model(make_run(history=[WORKED]), ANSWER) is None


def test_an_unsupported_final_answer_is_replaced_with_what_could_not_be_confirmed(
    make_run: MakeRun,
) -> None:
    guard = PostconditionCheck([tool_succeeded("update_inventory")])
    run = make_run(history=[FAILED])

    replacement = guard.after_model(run, ANSWER)

    assert replacement is not None
    assert replacement.message.role is Role.ASSISTANT
    assert replacement.message.content.startswith("I could not confirm")
    assert "unknown sku" in replacement.message.content
    assert replacement.usage == ANSWER.usage
    assert len(run.trace.of_kind(EventKind.GUARD)) == 1


def test_every_failed_condition_is_reported(make_run: MakeRun) -> None:
    guard = PostconditionCheck([tool_succeeded("update_inventory"), tool_succeeded("notify")])

    replacement = guard.after_model(make_run(history=[FAILED]), ANSWER)

    assert replacement is not None
    assert "unknown sku" in replacement.message.content
    assert "notify was never called" in replacement.message.content
