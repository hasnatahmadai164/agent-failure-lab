import json

from agent_failure_lab.sim import EventKind, ManualClock, Trace


def _trace() -> tuple[Trace, ManualClock]:
    clock = ManualClock()
    return Trace(clock), clock


def test_events_keep_the_order_they_were_recorded_in() -> None:
    trace, _ = _trace()
    trace.record(1, EventKind.MODEL, "first")
    trace.record(1, EventKind.TOOL_CALL, "second")

    assert [event.summary for event in trace.events] == ["first", "second"]


def test_events_are_stamped_with_the_clock_time() -> None:
    trace, clock = _trace()
    trace.record(1, EventKind.MODEL, "early")
    clock.advance(12.5)
    trace.record(2, EventKind.MODEL, "late")

    assert [event.at for event in trace.events] == [0.0, 12.5]


def test_of_kind_returns_only_matching_events() -> None:
    trace, _ = _trace()
    trace.record(1, EventKind.MODEL, "model")
    trace.record(1, EventKind.GUARD, "guard")

    assert [event.summary for event in trace.of_kind(EventKind.GUARD)] == ["guard"]


def test_render_has_one_line_per_event_with_step_time_and_kind() -> None:
    trace, clock = _trace()
    trace.record(1, EventKind.MODEL, "says hello")
    clock.advance(3)
    trace.record(2, EventKind.STOP, "final_answer")

    lines = trace.render().splitlines()

    assert len(lines) == 2
    assert "model" in lines[0]
    assert "says hello" in lines[0]
    assert "3.0s" in lines[1]
    assert "stop" in lines[1]


def test_to_json_round_trips_to_the_same_structure_as_to_dict() -> None:
    trace, _ = _trace()
    trace.record(1, EventKind.TOOL_RESULT, "ok", {"tool": "charge", "is_error": False})

    assert json.loads(trace.to_json()) == trace.to_dict()
    assert trace.to_dict()["events"][0]["data"] == {"tool": "charge", "is_error": False}


def test_record_copies_the_data_it_is_given() -> None:
    trace, _ = _trace()
    data = {"n": 1}
    trace.record(1, EventKind.GUARD, "x", data)
    data["n"] = 2

    assert trace.events[0].data == {"n": 1}
