from agent_failure_lab.failures.silent_context_truncation import SCENARIO
from agent_failure_lab.scenario import Variant
from agent_failure_lab.sim import EventKind


def test_broken_variant_refunds_over_the_limit_without_approval() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert outcome.failure_observed
    assert outcome.metrics["unapproved_refunds"] == 1
    assert outcome.metrics["approvals_requested"] == 0
    assert "250.00 EUR" in outcome.findings[0]


def test_broken_variant_trims_the_history_without_leaving_any_trace_of_it() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert outcome.metrics["rule_visible_to_model"] is False
    assert outcome.metrics["messages_sent_to_model"] < outcome.metrics["messages_in_history"]
    assert outcome.metrics["guard_interventions"] == 0


def test_fixed_variant_keeps_the_rule_in_front_of_the_model_and_asks_for_approval() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert not outcome.failure_observed
    assert outcome.metrics["rule_visible_to_model"] is True
    assert outcome.metrics["unapproved_refunds"] == 0
    assert outcome.metrics["approvals_requested"] == 1


def test_fixed_variant_reports_what_it_dropped() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    drops = outcome.trace.of_kind(EventKind.GUARD)
    assert drops
    assert all(drop.data["guard"] == "ContextBudget" for drop in drops)
    assert drops[0].data["dropped"] > 0
