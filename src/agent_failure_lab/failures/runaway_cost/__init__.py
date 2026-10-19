from agent_failure_lab.failures.runaway_cost import broken, fixed
from agent_failure_lab.scenario import ScenarioDefinition

SCENARIO = ScenarioDefinition(
    slug="runaway-cost",
    title="Runaway cost",
    category="context-and-cost",
    summary="With no spending ceiling, a run keeps paying for more steps",
    broken=broken.run,
    fixed=fixed.run,
)
