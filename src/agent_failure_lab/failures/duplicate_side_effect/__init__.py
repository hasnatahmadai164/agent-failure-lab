from agent_failure_lab.failures.duplicate_side_effect import broken, fixed
from agent_failure_lab.scenario import ScenarioDefinition

SCENARIO = ScenarioDefinition(
    slug="duplicate-side-effect",
    title="Duplicate side effect on retry",
    category="side-effects",
    summary="A retried tool call charges the customer twice",
    fix="Idempotency keys",
    guards=("IdempotencyKeys", "IdempotencyStore"),
    broken=broken.run,
    fixed=fixed.run,
    broken_live=broken.run,
    fixed_live=fixed.run,
)
