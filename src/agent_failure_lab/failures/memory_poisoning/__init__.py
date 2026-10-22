from agent_failure_lab.failures.memory_poisoning import broken, fixed
from agent_failure_lab.scenario import ScenarioDefinition

SCENARIO = ScenarioDefinition(
    slug="memory-poisoning",
    title="Memory poisoning",
    category="security",
    summary="Untrusted content saved to memory is later followed as an instruction",
    broken=broken.run,
    fixed=fixed.run,
)
