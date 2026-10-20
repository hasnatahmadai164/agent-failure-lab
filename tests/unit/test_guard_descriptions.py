from collections.abc import Callable

from agent_failure_lab.guards.descriptions import (
    ToolDescriptionLinter,
    description_words,
    lint_descriptions,
)
from agent_failure_lab.sim import EventKind, RunState, Stop, ToolSpec

MakeRun = Callable[..., RunState]

REPLY = ToolSpec("send_reply", "Add a message to a support ticket.")
NOTE = ToolSpec("add_note", "Add a comment to a support ticket.")
CLEAR_REPLY = ToolSpec("send_reply", "Send a reply that the customer will see.")
CLEAR_NOTE = ToolSpec("add_note", "Add an internal note that only staff can read.")


def test_words_are_lower_case_and_stop_words_are_dropped() -> None:
    assert description_words("Add a Message to the Ticket") == {"add", "message", "ticket"}


def test_descriptions_that_share_most_of_their_words_are_flagged() -> None:
    (finding,) = lint_descriptions([REPLY, NOTE])

    assert finding.tools == ("send_reply", "add_note")
    assert "overlap by 60%" in finding.message


def test_descriptions_that_say_different_things_are_not_flagged() -> None:
    assert lint_descriptions([CLEAR_REPLY, CLEAR_NOTE]) == []


def test_the_overlap_limit_can_be_changed() -> None:
    assert lint_descriptions([REPLY, NOTE], max_overlap=0.7) == []


def test_a_description_with_too_few_meaningful_words_is_flagged() -> None:
    (finding,) = lint_descriptions([ToolSpec("do_it", "Does it.")])

    assert finding.tools == ("do_it",)
    assert "fewer than 3" in finding.message


def test_the_guard_stops_the_run_when_descriptions_are_unclear(make_run: MakeRun) -> None:
    run = make_run(specs=[REPLY, NOTE])

    outcome = ToolDescriptionLinter().before_model(run, [])

    assert isinstance(outcome, Stop)
    assert "overlap" in outcome.reason
    assert len(run.trace.of_kind(EventKind.GUARD)) == 1


def test_the_guard_checks_only_once_per_run(make_run: MakeRun) -> None:
    guard = ToolDescriptionLinter()
    run = make_run(specs=[REPLY, NOTE])
    guard.before_model(run, [])

    assert guard.before_model(run, []) is None


def test_the_guard_lets_clear_descriptions_through_without_a_trace(make_run: MakeRun) -> None:
    run = make_run(specs=[CLEAR_REPLY, CLEAR_NOTE])

    assert ToolDescriptionLinter().before_model(run, []) is None
    assert run.trace.of_kind(EventKind.GUARD) == []


def test_in_non_strict_mode_the_findings_are_recorded_but_the_run_goes_on(
    make_run: MakeRun,
) -> None:
    run = make_run(specs=[REPLY, NOTE])

    assert ToolDescriptionLinter(strict=False).before_model(run, []) is None
    assert len(run.trace.of_kind(EventKind.GUARD)) == 1
