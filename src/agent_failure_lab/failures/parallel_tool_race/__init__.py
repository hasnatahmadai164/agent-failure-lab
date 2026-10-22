from agent_failure_lab.failures.parallel_tool_race import broken, fixed
from agent_failure_lab.scenario import ScenarioDefinition

SCENARIO = ScenarioDefinition(
    slug="parallel-tool-race",
    title="Parallel tool race",
    category="side-effects",
    summary="Two parallel tool calls overwrite each other's update",
    broken=broken.run,
    fixed=fixed.run,
)
