from agent_failure_lab.failures.hallucinated_tool_arguments import broken, fixed
from agent_failure_lab.scenario import ScenarioDefinition

SCENARIO = ScenarioDefinition(
    slug="hallucinated-tool-arguments",
    title="Hallucinated tool arguments",
    category="tool-use",
    summary="The model invents an enum value and the tool stores it",
    broken=broken.run,
    fixed=fixed.run,
)
