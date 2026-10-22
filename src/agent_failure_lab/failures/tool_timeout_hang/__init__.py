from agent_failure_lab.failures.tool_timeout_hang import broken, fixed
from agent_failure_lab.scenario import ScenarioDefinition

SCENARIO = ScenarioDefinition(
    slug="tool-timeout-hang",
    title="Tool timeout hang",
    category="control-flow",
    summary="A tool never returns and the whole run stalls waiting for it",
    broken=broken.run,
    fixed=fixed.run,
)
