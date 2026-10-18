from agent_failure_lab.failures.duplicate_side_effect import SCENARIO
from agent_failure_lab.scenario import Variant
from agent_failure_lab.sim import EventKind


def test_broken_variant_charges_the_customer_twice() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert outcome.failure_observed
    assert outcome.metrics["charges"] == 2
    assert outcome.metrics["tool_calls"] == 2
    assert "charged 2 times" in outcome.findings[0]


def test_fixed_variant_charges_the_customer_once() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert not outcome.failure_observed
    assert outcome.metrics["charges"] == 1


def test_fixed_variant_still_retries_and_the_retry_is_answered_from_the_store() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert outcome.metrics["tool_calls"] == 2
    assert outcome.metrics["replayed_calls"] == 1


def test_fixed_variant_uses_the_same_key_for_both_attempts() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    keys = [event.data["key"] for event in outcome.trace.of_kind(EventKind.GUARD)]
    assert len(keys) == 2
    assert keys[0] == keys[1]
