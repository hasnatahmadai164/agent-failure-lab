from collections.abc import Callable

import pytest

from agent_failure_lab.guards.serialize import ConflictSerializer
from agent_failure_lab.sim import (
    Block,
    EventKind,
    Message,
    Role,
    RunState,
    ToolCall,
    ToolSpec,
    user_message,
)

MakeRun = Callable[..., RunState]

ADD_TAG = ToolSpec("add_tag", "Add a tag.", side_effects=("changes-ticket",))
GET_TICKET = ToolSpec("get_ticket", "Read a ticket.")
URGENT = ToolCall("add_tag", {"ticket_id": "T-1", "tag": "urgent"}, id="c1")
BILLING = ToolCall("add_tag", {"ticket_id": "T-1", "tag": "billing"}, id="c2")
OTHER_TICKET = ToolCall("add_tag", {"ticket_id": "T-2", "tag": "urgent"}, id="c3")
READ = ToolCall("get_ticket", {"ticket_id": "T-1"}, id="c4")


def _run(make_run: MakeRun, *calls: ToolCall) -> RunState:
    turn = Message(Role.ASSISTANT, tool_calls=calls)
    return make_run(specs=[ADD_TAG, GET_TICKET], history=[user_message("go"), turn])


def test_the_first_change_to_a_resource_in_a_turn_runs(make_run: MakeRun) -> None:
    run = _run(make_run, URGENT, BILLING)

    assert ConflictSerializer(["ticket_id"]).before_tool(run, URGENT) is None


def test_a_later_change_to_the_same_resource_in_the_same_turn_is_held_back(
    make_run: MakeRun,
) -> None:
    run = _run(make_run, URGENT, BILLING)

    outcome = ConflictSerializer(["ticket_id"]).before_tool(run, BILLING)

    assert isinstance(outcome, Block)
    assert outcome.result.is_error
    assert "next step" in outcome.result.content


def test_a_change_to_a_different_resource_runs(make_run: MakeRun) -> None:
    run = _run(make_run, URGENT, OTHER_TICKET)

    assert ConflictSerializer(["ticket_id"]).before_tool(run, OTHER_TICKET) is None


def test_a_call_that_only_reads_is_never_held_back(make_run: MakeRun) -> None:
    run = _run(make_run, URGENT, READ)

    assert ConflictSerializer(["ticket_id"]).before_tool(run, READ) is None


def test_a_read_earlier_in_the_turn_does_not_hold_back_a_change(make_run: MakeRun) -> None:
    run = _run(make_run, READ, URGENT)

    assert ConflictSerializer(["ticket_id"]).before_tool(run, URGENT) is None


def test_only_the_first_of_several_changes_to_one_resource_runs(make_run: MakeRun) -> None:
    third = ToolCall("add_tag", {"ticket_id": "T-1", "tag": "vip"}, id="c5")
    run = _run(make_run, URGENT, BILLING, third)
    guard = ConflictSerializer(["ticket_id"])

    assert guard.before_tool(run, URGENT) is None
    assert isinstance(guard.before_tool(run, BILLING), Block)
    assert isinstance(guard.before_tool(run, third), Block)


def test_a_call_without_the_key_arguments_is_left_alone(make_run: MakeRun) -> None:
    anonymous = ToolCall("add_tag", {"tag": "urgent"}, id="c6")
    run = _run(make_run, URGENT, anonymous)

    assert ConflictSerializer(["ticket_id"]).before_tool(run, anonymous) is None


def test_holding_a_call_back_is_recorded_in_the_trace(make_run: MakeRun) -> None:
    run = _run(make_run, URGENT, BILLING)

    ConflictSerializer(["ticket_id"]).before_tool(run, BILLING)

    (event,) = run.trace.of_kind(EventKind.GUARD)
    assert "held back add_tag" in event.summary


def test_key_fields_cannot_be_empty() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        ConflictSerializer([])
