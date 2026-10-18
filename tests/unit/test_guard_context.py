from collections.abc import Callable, Sequence

import pytest

from agent_failure_lab.guards.context import ContextBudget
from agent_failure_lab.sim import (
    EventKind,
    Message,
    Role,
    RunState,
    Stop,
    ToolCall,
    estimate_message_tokens,
    system_message,
    tool_message,
    user_message,
)

MakeRun = Callable[..., RunState]

RULE = system_message("Never approve refunds above 100 EUR.")


def _chat(count: int) -> list[Message]:
    return [
        user_message(f"message number {index} with some padding text") for index in range(count)
    ]


def _tokens(messages: Sequence[Message]) -> int:
    return sum(estimate_message_tokens(m) for m in messages)


def _request(outcome: object) -> list[Message]:
    assert not isinstance(outcome, Stop)
    assert outcome is not None
    return list(outcome)  # type: ignore[call-overload]


def test_a_request_within_the_budget_is_left_alone(make_run: MakeRun) -> None:
    messages = [RULE, *_chat(3)]

    assert ContextBudget(_tokens(messages)).before_model(make_run(), messages) is None


def test_system_messages_survive_and_the_oldest_messages_are_dropped(make_run: MakeRun) -> None:
    messages = [RULE, *_chat(12)]
    budget = _tokens(messages) // 2

    request = _request(ContextBudget(budget).before_model(make_run(), messages))

    assert request[0] is RULE
    assert request[-1] is messages[-1]
    assert _tokens(request) <= budget
    assert len(request) < len(messages)


def test_the_model_is_told_that_messages_were_omitted(make_run: MakeRun) -> None:
    messages = [RULE, *_chat(12)]

    request = _request(ContextBudget(_tokens(messages) // 2).before_model(make_run(), messages))

    note = request[1]
    assert note.role is Role.SYSTEM
    assert "omitted" in note.content


def test_the_note_reports_how_many_messages_were_dropped(make_run: MakeRun) -> None:
    messages = [RULE, *_chat(12)]
    run = make_run()

    request = _request(ContextBudget(_tokens(messages) // 2).before_model(run, messages))

    dropped = len(messages) - (len(request) - 1)
    assert f"{dropped} earlier messages" in request[1].content
    (event,) = run.trace.of_kind(EventKind.GUARD)
    assert event.data["dropped"] == dropped


def test_a_tool_result_is_never_left_without_the_call_that_produced_it(
    make_run: MakeRun,
) -> None:
    call = ToolCall("lookup", {"id": 1}, id="call_1")
    assistant = Message(Role.ASSISTANT, "looking this up " * 10, tool_calls=(call,))
    result = tool_message(call, "r" * 40)
    newest = user_message("what now?")
    messages = [RULE, assistant, result, newest]
    note = system_message("Note: 3 earlier messages were omitted to fit the context window.")
    budget = _tokens([RULE, note, result, newest])

    request = _request(ContextBudget(budget).before_model(make_run(), messages))

    assert result not in request
    assert request[-1] is newest


def test_it_stops_when_the_pinned_messages_alone_do_not_fit(make_run: MakeRun) -> None:
    run = make_run()
    messages = [RULE, *_chat(5)]

    outcome = ContextBudget(5).before_model(run, messages)

    assert isinstance(outcome, Stop)
    assert "pinned" in outcome.reason
    assert len(run.trace.of_kind(EventKind.GUARD)) == 1


def test_it_stops_when_the_newest_message_does_not_fit(make_run: MakeRun) -> None:
    huge = user_message("x" * 4000)
    messages = [RULE, *_chat(3), huge]
    budget = _tokens([RULE]) + 40

    outcome = ContextBudget(budget).before_model(make_run(), messages)

    assert isinstance(outcome, Stop)
    assert "newest" in outcome.reason


def test_the_recorded_history_is_not_touched(make_run: MakeRun) -> None:
    messages = [RULE, *_chat(12)]
    before = list(messages)

    ContextBudget(_tokens(messages) // 2).before_model(make_run(), messages)

    assert messages == before


def test_the_budget_must_be_positive() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        ContextBudget(0)
