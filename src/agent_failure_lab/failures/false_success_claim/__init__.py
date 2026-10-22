from agent_failure_lab.failures.false_success_claim import broken, fixed
from agent_failure_lab.scenario import ScenarioDefinition

SCENARIO = ScenarioDefinition(
    slug="false-success-claim",
    title="False success claim",
    category="tool-use",
    summary="The agent reports success after a tool returned an error",
    broken=broken.run,
    fixed=fixed.run,
)
