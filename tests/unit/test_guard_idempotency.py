from collections.abc import Callable

import pytest

from agent_failure_lab.guards.idempotency import KEY_ARGUMENT, IdempotencyKeys, IdempotencyStore
from agent_failure_lab.sim import EventKind, RunState, ToolCall, ToolSpec

MakeRun = Callable[..., RunState]

CHARGE = ToolSpec("charge", "Charge a card.", side_effects=("charges-card",))
LOOKUP = ToolSpec("lookup", "Look an order up.")


def test_store_runs_the_operation_once_and_replays_the_result() -> None:
    store = IdempotencyStore()
    runs: list[str] = []

    def operation() -> str:
        runs.append("run")
        return "charged"

    first = store.execute("key-1", operation)
    second = store.execute("key-1", operation)

    assert (first, second) == ("charged", "charged")
    assert len(runs) == 1
    assert store.replays == 1


def test_store_treats_different_keys_as_different_operations() -> None:
    store = IdempotencyStore()

    assert store.execute("a", lambda: "first") == "first"
    assert store.execute("b", lambda: "second") == "second"
    assert store.replays == 0


def test_store_does_not_remember_an_operation_that_failed() -> None:
    store = IdempotencyStore()

    def failing() -> str:
        raise RuntimeError("gateway down")

    with pytest.raises(RuntimeError, match="gateway down"):
        store.execute("key-1", failing)

    assert store.execute("key-1", lambda: "worked on retry") == "worked on retry"


def test_guard_attaches_a_key_to_a_side_effecting_call(make_run: MakeRun) -> None:
    run = make_run(specs=[CHARGE])
    call = ToolCall("charge", {"order_id": "A-1", "amount": 10})

    prepared = IdempotencyKeys().before_tool(run, call)

    assert prepared is not None
    assert KEY_ARGUMENT in prepared.arguments
    assert prepared.arguments["order_id"] == "A-1"


def test_guard_leaves_calls_without_side_effects_alone(make_run: MakeRun) -> None:
    run = make_run(specs=[LOOKUP])

    assert IdempotencyKeys().before_tool(run, ToolCall("lookup", {"order_id": "A-1"})) is None


def test_guard_leaves_unknown_tools_alone(make_run: MakeRun) -> None:
    assert IdempotencyKeys().before_tool(make_run(), ToolCall("mystery", {})) is None


def test_guard_does_not_replace_a_key_the_caller_already_set(make_run: MakeRun) -> None:
    run = make_run(specs=[CHARGE])
    call = ToolCall("charge", {"order_id": "A-1", KEY_ARGUMENT: "mine"})

    assert IdempotencyKeys().before_tool(run, call) is None


def test_the_same_call_always_gets_the_same_key(make_run: MakeRun) -> None:
    run = make_run(specs=[CHARGE])
    guard = IdempotencyKeys()

    first = guard.before_tool(run, ToolCall("charge", {"order_id": "A-1", "amount": 10}))
    second = guard.before_tool(run, ToolCall("charge", {"amount": 10, "order_id": "A-1"}))

    assert first is not None
    assert second is not None
    assert first.arguments[KEY_ARGUMENT] == second.arguments[KEY_ARGUMENT]


def test_a_different_order_gets_a_different_key(make_run: MakeRun) -> None:
    run = make_run(specs=[CHARGE])
    guard = IdempotencyKeys()

    first = guard.before_tool(run, ToolCall("charge", {"order_id": "A-1"}))
    second = guard.before_tool(run, ToolCall("charge", {"order_id": "A-2"}))

    assert first is not None
    assert second is not None
    assert first.arguments[KEY_ARGUMENT] != second.arguments[KEY_ARGUMENT]


def test_key_fields_limit_which_arguments_identify_the_operation(make_run: MakeRun) -> None:
    run = make_run(specs=[CHARGE])
    guard = IdempotencyKeys(key_fields=["order_id"])

    first = guard.before_tool(run, ToolCall("charge", {"order_id": "A-1", "amount": 10}))
    second = guard.before_tool(run, ToolCall("charge", {"order_id": "A-1", "amount": 11}))

    assert first is not None
    assert second is not None
    assert first.arguments[KEY_ARGUMENT] == second.arguments[KEY_ARGUMENT]


def test_attaching_a_key_is_recorded_in_the_trace(make_run: MakeRun) -> None:
    run = make_run(specs=[CHARGE])

    IdempotencyKeys().before_tool(run, ToolCall("charge", {"order_id": "A-1"}))

    (event,) = run.trace.of_kind(EventKind.GUARD)
    assert event.data["guard"] == "IdempotencyKeys"
    assert "charge" in event.summary
