from agent_failure_lab.failures.ambiguous_tool_selection import SCENARIO
from agent_failure_lab.failures.ambiguous_tool_selection.world import (
    AMBIGUOUS_SPECS,
    CLEAR_SPECS,
    choose_tool,
)
from agent_failure_lab.guards import lint_descriptions
from agent_failure_lab.scenario import Variant


def test_broken_variant_sends_the_internal_remark_to_the_customer() -> None:
    outcome = SCENARIO.run(Variant.BROKEN)

    assert outcome.failure_observed
    assert outcome.metrics["tool_chosen"] == "send_reply"
    assert outcome.metrics["customer_messages_sent"] == 1
    assert outcome.metrics["internal_notes_added"] == 0


def test_fixed_variant_adds_the_note_for_staff_only() -> None:
    outcome = SCENARIO.run(Variant.FIXED)

    assert not outcome.failure_observed
    assert outcome.metrics["tool_chosen"] == "add_note"
    assert outcome.metrics["customer_messages_sent"] == 0
    assert outcome.metrics["internal_notes_added"] == 1


def test_the_linter_flags_the_original_descriptions_and_passes_the_rewritten_ones() -> None:
    assert len(lint_descriptions(AMBIGUOUS_SPECS)) == 1
    assert lint_descriptions(CLEAR_SPECS) == []


def test_the_scenario_reports_how_many_description_problems_each_variant_has() -> None:
    assert SCENARIO.run(Variant.BROKEN).metrics["description_problems"] == 1
    assert SCENARIO.run(Variant.FIXED).metrics["description_problems"] == 0


def test_the_stand_in_model_breaks_ties_in_favour_of_the_tool_listed_first() -> None:
    assert choose_tool("do something unrelated", AMBIGUOUS_SPECS) == "send_reply"
    assert choose_tool("do something unrelated", tuple(reversed(AMBIGUOUS_SPECS))) == "add_note"
