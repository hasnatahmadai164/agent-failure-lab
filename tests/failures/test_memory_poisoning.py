from agent_failure_lab.failures.memory_poisoning import SCENARIO
from agent_failure_lab.failures.memory_poisoning.world import ATTACKER
from agent_failure_lab.scenario import Variant
from agent_failure_lab.sim import EventKind


def test_broken_variant_copies_the_invoice_to_an_address_nobody_asked_for() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert outcome.failure_observed
    assert outcome.metrics["memories_saved"] == 2
    assert outcome.metrics["unrequested_copies"] == 1
    assert ATTACKER in outcome.findings[0]


def test_broken_variant_stores_the_poisoned_note_with_no_record_of_where_it_came_from() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert outcome.metrics["memory_sources"] == "unlabelled, unlabelled"


def test_fixed_variant_sends_the_invoice_with_no_extra_copy() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert not outcome.failure_observed
    assert outcome.metrics["unrequested_copies"] == 0


def test_fixed_variant_keeps_the_harmless_fact_and_tags_where_it_came_from() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert outcome.metrics["memories_saved"] == 1
    assert outcome.metrics["memory_sources"] == "untrusted:read_email"


def test_fixed_variant_refuses_the_instruction_when_it_is_written_not_when_it_is_used() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    refusals = [e for e in outcome.trace.of_kind(EventKind.GUARD) if "refused" in e.summary]
    assert len(refusals) == 1
    assert refusals[0].step < 4
