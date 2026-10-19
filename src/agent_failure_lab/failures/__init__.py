from agent_failure_lab.failures import (
    duplicate_side_effect,
    hallucinated_tool_arguments,
    infinite_tool_loop,
    runaway_cost,
    silent_context_truncation,
    tool_output_injection,
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
    )
