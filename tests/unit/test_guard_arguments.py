from collections.abc import Callable
from typing import Any

import pytest

from agent_failure_lab.guards.arguments import ArgumentValidator, validate_arguments
from agent_failure_lab.sim import Block, EventKind, RunState, Stop, ToolCall, ToolSpec

MakeRun = Callable[..., RunState]

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "order_id": {"type": "string", "pattern": r"^ORD-\d{4}$"},
        "speed": {"type": "string", "enum": ["standard", "express", "overnight"]},
        "parcels": {"type": "integer", "minimum": 1, "maximum": 5},
        "note": {"type": "string", "minLength": 2, "maxLength": 10},
    },
    "required": ["order_id", "speed"],
    "additionalProperties": False,
}
SHIP = ToolSpec("update_shipping", "Change the shipping speed.", SCHEMA)
GOOD = {"order_id": "ORD-1001", "speed": "express"}


def test_valid_arguments_produce_no_problems() -> None:
    assert validate_arguments(SCHEMA, GOOD) == []


def test_a_missing_required_argument_is_reported() -> None:
    assert validate_arguments(SCHEMA, {"speed": "express"}) == [
        "missing required argument 'order_id'"
    ]


def test_a_value_outside_the_enum_lists_the_allowed_values() -> None:
    (problem,) = validate_arguments(SCHEMA, {**GOOD, "speed": "next_day"})

    assert "'next_day'" in problem
    assert '["standard", "express", "overnight"]' in problem


def test_a_value_that_misses_the_pattern_is_reported() -> None:
    (problem,) = validate_arguments(SCHEMA, {**GOOD, "order_id": "1001"})

    assert "order_id" in problem


def test_the_wrong_type_is_reported_and_booleans_are_not_integers() -> None:
    assert validate_arguments(SCHEMA, {**GOOD, "parcels": "2"})
    assert validate_arguments(SCHEMA, {**GOOD, "parcels": True})


@pytest.mark.parametrize(("parcels", "valid"), [(0, False), (1, True), (5, True), (6, False)])
def test_numeric_bounds_are_inclusive(parcels: int, valid: bool) -> None:
    assert (validate_arguments(SCHEMA, {**GOOD, "parcels": parcels}) == []) is valid


@pytest.mark.parametrize(("note", "valid"), [("a", False), ("ab", True), ("x" * 11, False)])
def test_string_length_bounds(note: str, valid: bool) -> None:
    assert (validate_arguments(SCHEMA, {**GOOD, "note": note}) == []) is valid


def test_unknown_arguments_are_reported_only_when_the_schema_forbids_them() -> None:
    assert validate_arguments(SCHEMA, {**GOOD, "colour": "red"}) == ["unknown argument 'colour'"]
    assert validate_arguments({"properties": {}}, {"colour": "red"}) == []


def test_guard_passes_valid_calls_through(make_run: MakeRun) -> None:
    run = make_run(specs=[SHIP])

    assert ArgumentValidator().before_tool(run, ToolCall("update_shipping", GOOD)) is None


def test_guard_blocks_an_invalid_call_and_tells_the_model_what_to_fix(make_run: MakeRun) -> None:
    run = make_run(specs=[SHIP])
    call = ToolCall("update_shipping", {**GOOD, "speed": "next_day"})

    outcome = ArgumentValidator().before_tool(run, call)

    assert isinstance(outcome, Block)
    assert outcome.result.is_error
    assert "allowed values" in outcome.result.content
    assert len(run.trace.of_kind(EventKind.GUARD)) == 1


def test_guard_stops_the_run_when_repairs_run_out(make_run: MakeRun) -> None:
    guard = ArgumentValidator(max_repairs=2)
    run = make_run(specs=[SHIP])
    bad = ToolCall("update_shipping", {**GOOD, "speed": "next_day"})

    assert isinstance(guard.before_tool(run, bad), Block)
    assert isinstance(guard.before_tool(run, bad), Block)
    assert isinstance(guard.before_tool(run, bad), Stop)


def test_a_valid_call_resets_the_repair_count(make_run: MakeRun) -> None:
    guard = ArgumentValidator(max_repairs=1)
    run = make_run(specs=[SHIP])
    bad = ToolCall("update_shipping", {**GOOD, "speed": "next_day"})

    assert isinstance(guard.before_tool(run, bad), Block)
    assert guard.before_tool(run, ToolCall("update_shipping", GOOD)) is None
    assert isinstance(guard.before_tool(run, bad), Block)


def test_guard_ignores_tools_it_does_not_know(make_run: MakeRun) -> None:
    assert ArgumentValidator().before_tool(make_run(), ToolCall("mystery", {})) is None


def test_negative_repairs_are_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        ArgumentValidator(max_repairs=-1)
