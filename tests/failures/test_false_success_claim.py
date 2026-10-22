from agent_failure_lab.failures.false_success_claim import SCENARIO
from agent_failure_lab.scenario import Variant


def test_broken_variant_claims_success_although_the_update_failed() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert outcome.failure_observed
    assert outcome.metrics["claimed_success"] is True
    assert outcome.metrics["stock_updated"] is False
    assert outcome.metrics["failed_tool_calls"] == 1
    assert "unknown sku 'SKU-9'" in outcome.findings[0]


def test_fixed_variant_no_longer_claims_success() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert not outcome.failure_observed
    assert outcome.metrics["claimed_success"] is False
    assert outcome.metrics["stock_updated"] is False


def test_fixed_variant_tells_the_user_what_could_not_be_confirmed() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    answer = str(outcome.metrics["final_answer"])
    assert answer.startswith("I could not confirm that this was completed")
    assert "unknown sku 'SKU-9'" in answer


def test_fixed_variant_records_that_it_replaced_the_answer() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert outcome.metrics["guard_interventions"] == 1
