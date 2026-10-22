from agent_failure_lab.failures import (
    ambiguous_tool_selection,
    duplicate_side_effect,
    false_success_claim,
    hallucinated_tool_arguments,
    infinite_tool_loop,
    memory_poisoning,
    parallel_tool_race,
    resume_replays_completed_steps,
    runaway_cost,
    silent_context_truncation,
    tool_output_injection,
    tool_timeout_hang,
)
from agent_failure_lab.scenario import Scenario


def builtin_scenarios() -> tuple[Scenario, ...]:
    return (
        duplicate_side_effect.SCENARIO,
        infinite_tool_loop.SCENARIO,
        tool_output_injection.SCENARIO,
        hallucinated_tool_arguments.SCENARIO,
        silent_context_truncation.SCENARIO,
        runaway_cost.SCENARIO,
        resume_replays_completed_steps.SCENARIO,
        tool_timeout_hang.SCENARIO,
        parallel_tool_race.SCENARIO,
        ambiguous_tool_selection.SCENARIO,
        false_success_claim.SCENARIO,
        memory_poisoning.SCENARIO,
    )
