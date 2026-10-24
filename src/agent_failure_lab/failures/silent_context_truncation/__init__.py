from agent_failure_lab.failures.silent_context_truncation import broken, fixed
from agent_failure_lab.scenario import ScenarioDefinition

SCENARIO = ScenarioDefinition(
    slug="silent-context-truncation",
    title="Silent context truncation",
    category="context-and-cost",
    summary="History is cut without any error and the model loses a constraint",
    fix="A context budget that pins instructions and fails loudly",
    guards=("ContextBudget",),
    broken=broken.run,
    fixed=fixed.run,
)
