from collections.abc import Callable

from agent_failure_lab.guards.journal import Journal, StepJournal
from agent_failure_lab.sim import Block, EventKind, RunState, ToolCall, ToolResult, ToolSpec

MakeRun = Callable[..., RunState]

CHARGE = ToolSpec("charge", "Charge a card.", side_effects=("charges-card",))
LOOKUP = ToolSpec("lookup", "Look an order up.")
CALL = ToolCall("charge", {"order_id": "A-1"})
DONE = ToolResult("charged")


def _complete(guard: StepJournal, run: RunState, call: ToolCall, result: ToolResult) -> None:
    assert guard.before_tool(run, call) is None
    guard.after_tool(run, call, result)


def test_a_completed_call_is_recorded_and_replayed_by_the_next_run(make_run: MakeRun) -> None:
    journal = Journal()
    _complete(StepJournal(journal), make_run(specs=[CHARGE]), CALL, DONE)

    restarted = StepJournal(journal)
    outcome = restarted.before_tool(make_run(specs=[CHARGE]), CALL)

    assert isinstance(outcome, Block)
    assert outcome.result == DONE
    assert restarted.replays == 1


def test_a_replayed_call_is_not_recorded_a_second_time(make_run: MakeRun) -> None:
    journal = Journal()
    _complete(StepJournal(journal), make_run(specs=[CHARGE]), CALL, DONE)
    restarted = StepJournal(journal)
    run = make_run(specs=[CHARGE])

    restarted.before_tool(run, CALL)
    restarted.after_tool(run, CALL, DONE)

    assert len(journal) == 1


def test_a_failed_call_is_not_recorded_so_it_runs_again(make_run: MakeRun) -> None:
    journal = Journal()
    _complete(StepJournal(journal), make_run(specs=[CHARGE]), CALL, ToolResult("down", True))

    assert len(journal) == 0
    assert StepJournal(journal).before_tool(make_run(specs=[CHARGE]), CALL) is None


def test_calls_that_only_read_are_never_journaled(make_run: MakeRun) -> None:
    journal = Journal()
    lookup = ToolCall("lookup", {"order_id": "A-1"})
    _complete(StepJournal(journal), make_run(specs=[LOOKUP]), lookup, DONE)

    assert len(journal) == 0
    assert StepJournal(journal).before_tool(make_run(specs=[LOOKUP]), lookup) is None


def test_a_deliberate_repeat_in_one_run_is_not_mistaken_for_a_replay(make_run: MakeRun) -> None:
    journal = Journal()
    guard = StepJournal(journal)
    run = make_run(specs=[CHARGE])

    _complete(guard, run, CALL, DONE)
    _complete(guard, run, CALL, DONE)

    assert len(journal) == 2


def test_after_a_restart_only_the_steps_that_finished_are_skipped(make_run: MakeRun) -> None:
    journal = Journal()
    _complete(StepJournal(journal), make_run(specs=[CHARGE]), CALL, DONE)
    restarted = StepJournal(journal)
    run = make_run(specs=[CHARGE])

    assert isinstance(restarted.before_tool(run, CALL), Block)
    restarted.after_tool(run, CALL, DONE)
    assert restarted.before_tool(run, CALL) is None


def test_skipping_a_step_is_recorded_in_the_trace(make_run: MakeRun) -> None:
    journal = Journal()
    _complete(StepJournal(journal), make_run(specs=[CHARGE]), CALL, DONE)
    run = make_run(specs=[CHARGE])

    StepJournal(journal).before_tool(run, CALL)

    (event,) = run.trace.of_kind(EventKind.GUARD)
    assert "skipped charge" in event.summary
