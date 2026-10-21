from agent_failure_lab.failures.resume_replays_completed_steps import SCENARIO
from agent_failure_lab.scenario import Variant
from agent_failure_lab.sim import EventKind


def test_broken_variant_repeats_the_steps_that_had_already_finished() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert outcome.failure_observed
    assert outcome.metrics["runs"] == 2
    assert outcome.metrics["accounts_created"] == 2
    assert outcome.metrics["welcome_emails_sent"] == 2
    assert outcome.metrics["setup_fees_charged"] == 1
    assert "2 accounts created" in outcome.findings[0]


def test_fixed_variant_does_each_step_exactly_once() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert not outcome.failure_observed
    assert outcome.metrics["accounts_created"] == 1
    assert outcome.metrics["welcome_emails_sent"] == 1
    assert outcome.metrics["setup_fees_charged"] == 1


def test_fixed_variant_answers_the_two_finished_steps_from_the_journal() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert outcome.metrics["steps_replayed_from_journal"] == 2
    skipped = [e.summary for e in outcome.trace.of_kind(EventKind.GUARD) if "skipped" in e.summary]
    assert len(skipped) == 2


def test_the_crash_is_visible_in_the_trace() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    stops = [e.summary for e in outcome.trace.of_kind(EventKind.STOP)]
    assert stops[0].startswith("process crashed")
    assert stops[-1] == "final_answer"
