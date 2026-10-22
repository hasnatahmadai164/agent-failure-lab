from agent_failure_lab.failures.ambiguous_tool_selection import broken, fixed
from agent_failure_lab.scenario import ScenarioDefinition

SCENARIO = ScenarioDefinition(
    slug="ambiguous-tool-selection",
    title="Ambiguous tool selection",
    category="tool-use",
    summary="Two tools with overlapping descriptions get confused",
    broken=broken.run,
    fixed=fixed.run,
)
