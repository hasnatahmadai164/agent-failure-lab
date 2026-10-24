from agent_failure_lab.failures.infinite_tool_loop import broken, fixed
from agent_failure_lab.scenario import ScenarioDefinition

SCENARIO = ScenarioDefinition(
    slug="infinite-tool-loop",
    title="Infinite tool loop",
    category="control-flow",
    summary="The model repeats the same call without progress and burns tokens",
    fix="Loop detection and a step budget",
    guards=("LoopDetector", "StepBudget"),
    broken=broken.run,
    fixed=fixed.run,
)
